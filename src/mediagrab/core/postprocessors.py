"""Output boundaries, compatible MP4 conversion, and optional artwork."""

import json
import logging
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path
from threading import Event
from typing import Any

from yt_dlp.networking import Request
from yt_dlp.postprocessor import EmbedThumbnailPP
from yt_dlp.postprocessor.common import PostProcessor
from yt_dlp.utils import DownloadCancelled, determine_ext

from mediagrab.core.errors import DownloadCancelledError, OutputDirectoryError, PostProcessingError
from mediagrab.core.ffmpeg import FfmpegPaths
from mediagrab.core.logging_utils import log_exception
from mediagrab.core.process import run_process
from mediagrab.core.validators import validate_url

_LOGGER = logging.getLogger(__name__)


def check_cancelled(cancel_event: Event) -> None:
    """Abort the engine when the caller requests cancellation."""
    if cancel_event.is_set():
        raise DownloadCancelled()


def bounded_path(value: str | Path, output_dir: Path) -> Path:
    """Resolve a media path and reject destinations outside the output folder.

    Args:
        value: Engine-provided local file path.
        output_dir: Resolved destination directory.

    Returns:
        Absolute path within the destination.

    Raises:
        OutputDirectoryError: The path escapes the destination or cannot resolve.
    """
    try:
        path = Path(value).resolve()
        if path == output_dir or not path.is_relative_to(output_dir):
            raise OutputDirectoryError("The engine selected a path outside the output folder.")
    except (OSError, RuntimeError, ValueError) as error:
        raise OutputDirectoryError() from error
    return path


def probe_media(path: Path, tools: FfmpegPaths, cancel_event: Event) -> list[dict[str, Any]]:
    """Read local media streams with ffprobe using a timeout and no shell.

    Args:
        path: Absolute local media file.
        tools: Resolved FFmpeg executable pair.
        cancel_event: Cancellation shared with the download worker.

    Returns:
        Stream dictionaries returned by ffprobe.

    Raises:
        PostProcessingError: Probing fails or returns invalid stream data.
        DownloadCancelledError: The user cancels during probing.
    """
    try:
        result = run_process(
            [str(tools.ffprobe), "-v", "error", "-show_streams", "-of", "json", str(path)],
            timeout=20.0,
            cancel_event=cancel_event,
        )
        streams = json.loads(result.stdout)["streams"]
        if not isinstance(streams, list) or not all(isinstance(item, dict) for item in streams):
            raise ValueError("Invalid stream data")
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError) as error:
        raise PostProcessingError("FFmpeg could not inspect the downloaded media.") from error
    return streams


class OutputGuardPP(PostProcessor):
    """Check filenames before yt-dlp creates output files."""

    def __init__(
        self,
        output_dir: Path,
        extension: str,
        cancel_event: Event,
        *,
        compatibility: bool = False,
    ) -> None:
        """Store the resolved destination and final extension."""
        super().__init__()
        self._output_dir = output_dir
        self._extension = extension
        self._cancel_event = cancel_event
        self._compatibility = compatibility

    def run(self, info: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
        """Reject escaped filenames before the download starts."""
        check_cancelled(self._cancel_event)
        if self._extension == "mp4" and self._compatibility and info.get("requested_formats"):
            # yt-dlp's automatic merger runs before registered processors. MKV
            # accepts codecs (such as VP8) that cannot first be merged into MP4.
            # This intermediate is converted to the requested MP4 before metadata.
            info["ext"] = "mkv"
        filename = self._downloader.prepare_filename(info)
        if not isinstance(filename, str):
            raise OutputDirectoryError()
        path = bounded_path(filename, self._output_dir)
        bounded_path(path.with_suffix(f".{self._extension}"), self._output_dir)
        return [], info


class FinalPathPP(PostProcessor):
    """Capture authoritative paths after conversion and final file moves."""

    def __init__(self, output_dir: Path, extension: str, cancel_event: Event) -> None:
        """Create a collector for one engine operation, including playlists."""
        super().__init__()
        self._output_dir = output_dir
        self._extension = extension
        self._cancel_event = cancel_event
        self.paths: list[Path] = []

    def run(self, info: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
        """Record only existing, nonempty, post-processed media files."""
        check_cancelled(self._cancel_event)
        value = info.get("filepath")
        if not isinstance(value, str):
            raise PostProcessingError("The engine did not report a final media file.")
        path = bounded_path(value, self._output_dir)
        if path.suffix.lower() != f".{self._extension}" or not path.is_file():
            raise PostProcessingError("The expected final media file was not created.")
        if path.stat().st_size == 0:
            raise PostProcessingError("The downloaded media file is empty.")
        self.paths.append(path)
        return [], info


class VideoOutputPP(PostProcessor):
    """Produce MP4, encoding incompatible streams only when requested."""

    def __init__(
        self, tools: FfmpegPaths, output_dir: Path, cancel_event: Event, compatibility: bool
    ) -> None:
        """Store conversion settings without launching a process."""
        super().__init__()
        self._tools = tools
        self._output_dir = output_dir
        self._cancel_event = cancel_event
        self._compatibility = compatibility

    def run(self, info: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
        """Verify codecs and atomically install a converted MP4 when necessary."""
        check_cancelled(self._cancel_event)
        source = bounded_path(info["filepath"], self._output_dir)
        streams = probe_media(source, self._tools, self._cancel_event)
        video = next((item for item in streams if item.get("codec_type") == "video"), None)
        audio = next((item for item in streams if item.get("codec_type") == "audio"), None)
        if video is None:
            raise PostProcessingError("The selected media does not contain a video stream.")
        video_ok = video.get("codec_name") == "h264" and video.get("pix_fmt") in {
            "yuv420p",
            "yuvj420p",
        }
        audio_ok = audio is None or audio.get("codec_name") == "aac"
        encode_video = self._compatibility and not video_ok
        encode_audio = self._compatibility and not audio_ok
        if source.suffix.lower() == ".mp4" and not (encode_video or encode_audio):
            return [], info
        destination = bounded_path(source.with_suffix(".mp4"), self._output_dir)
        with tempfile.NamedTemporaryFile(
            prefix=".mediagrab-", suffix=".mp4", dir=self._output_dir, delete=False
        ) as temporary:
            temp_path = Path(temporary.name)
        try:
            arguments = [
                str(self._tools.ffmpeg),
                "-nostdin",
                "-y",
                "-v",
                "error",
                "-i",
                str(source),
                "-map",
                "0:v:0",
                "-map",
                "0:a:0?",
            ]
            if encode_video:
                arguments += [
                    "-c:v",
                    "libx264",
                    "-preset",
                    "medium",
                    "-crf",
                    "20",
                    "-pix_fmt",
                    "yuv420p",
                    "-vf",
                    "pad=ceil(iw/2)*2:ceil(ih/2)*2",
                ]
            else:
                arguments += ["-c:v", "copy"]
            arguments += ["-c:a", "aac", "-b:a", "256k"] if encode_audio else ["-c:a", "copy"]
            arguments += ["-movflags", "+faststart", str(temp_path)]
            run_process(arguments, timeout=86400.0, cancel_event=self._cancel_event)
            check_cancelled(self._cancel_event)
            if not temp_path.stat().st_size:
                raise PostProcessingError("FFmpeg produced an empty MP4 file.")
            temp_path.replace(destination)
        except (OSError, subprocess.SubprocessError) as error:
            raise PostProcessingError() from error
        finally:
            temp_path.unlink(missing_ok=True)
        info.update(filepath=str(destination), ext="mp4")
        return [str(source)] if source != destination else [], info


class OptionalThumbnailPP(PostProcessor):
    """Embed artwork in a private copy, preserving converted audio on failure."""

    def __init__(
        self,
        cancel_event: Event,
        output_dir: Path,
        on_warning: Callable[[str], None] | None = None,
    ) -> None:
        """Store cancellation, the destination, and an optional warning callback."""
        super().__init__()
        self._cancel_event = cancel_event
        self._output_dir = output_dir
        self._on_warning = on_warning

    def run(self, info: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
        """Install the decorated copy only after embedding succeeds."""
        check_cancelled(self._cancel_event)
        if not info.get("thumbnails"):
            return [], info
        source = bounded_path(info["filepath"], self._output_dir)
        working: Path | None = None
        artwork: Path | None = None
        try:
            thumbnail = info["thumbnails"][-1]
            url = validate_url(thumbnail["url"])
            extension = determine_ext(url, default_ext="jpg")
            if extension not in {"jpg", "jpeg", "png", "webp"}:
                extension = "jpg"
            with tempfile.NamedTemporaryFile(
                prefix=".mediagrab-artwork-",
                suffix=f".{extension}",
                dir=self._output_dir,
                delete=False,
            ) as temporary:
                artwork = Path(temporary.name)
                with self._downloader.urlopen(
                    Request(url, headers=info.get("http_headers"))
                ) as response:
                    size = 0
                    while chunk := response.read(65536):
                        check_cancelled(self._cancel_event)
                        size += len(chunk)
                        if size > 10 * 1024 * 1024:
                            raise PostProcessingError(
                                "The thumbnail exceeds the artwork size limit."
                            )
                        temporary.write(chunk)
            with tempfile.NamedTemporaryFile(
                prefix=".mediagrab-artwork-", suffix=".mp3", dir=self._output_dir, delete=False
            ) as temporary:
                working = Path(temporary.name)
            # Embedding modifies only a private copy. A partial copy or failed
            # embedding can never replace the successfully converted MP3.
            shutil.copyfile(source, working)
            artwork_info = dict(info)
            artwork_info["filepath"] = str(working)
            artwork_info["thumbnails"] = [{**thumbnail, "filepath": str(artwork), "ext": extension}]
            processor = EmbedThumbnailPP(self._downloader, already_have_thumbnail=False)
            processor.run(artwork_info)
            check_cancelled(self._cancel_event)
            working.replace(source)
            return [], info
        except DownloadCancelled, DownloadCancelledError:
            raise
        except Exception as error:
            log_exception(_LOGGER, "Optional thumbnail embedding failed; keeping the MP3.", error)
            message = "Artwork could not be embedded. The MP3 was saved without it."
            self.report_warning(message)
            if self._on_warning is not None:
                self._on_warning(message)
            return [], info
        finally:
            self._cleanup(working, artwork)

    def _cleanup(self, working: Path | None, artwork: Path | None) -> None:
        paths: set[Path] = set()
        if working is not None:
            paths.update({working, working.with_suffix(".temp.mp3")})
        if artwork is not None:
            paths.add(artwork)
            paths.update(artwork.with_suffix(f".{suffix}") for suffix in ("webp", "png"))
        for path in paths:
            try:
                path.unlink(missing_ok=True)
            except OSError as error:
                log_exception(
                    _LOGGER, "An optional artwork temporary file could not be removed.", error
                )
