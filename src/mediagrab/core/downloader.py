"""GUI-independent metadata extraction and cancellable yt-dlp downloads."""

import logging
import math
from dataclasses import replace
from pathlib import Path
from threading import Event
from typing import Any

import yt_dlp
from yt_dlp.postprocessor import get_postprocessor

from mediagrab.core.environment import runtime_options
from mediagrab.core.errors import DownloadCancelledError, ExtractionError
from mediagrab.core.errors_map import map_error
from mediagrab.core.ffmpeg import ensure_ffmpeg
from mediagrab.core.logging_utils import EngineLogger, log_exception
from mediagrab.core.models import (
    Browser,
    DownloadMode,
    DownloadRequest,
    DownloadStatus,
    ProgressCallback,
    ProgressEvent,
    VideoInfo,
)
from mediagrab.core.options import build_options
from mediagrab.core.postprocessors import (
    FinalPathPP,
    OptionalThumbnailPP,
    OutputGuardPP,
    VideoOutputPP,
    check_cancelled,
)
from mediagrab.core.validators import ensure_output_directory, validate_url

_LOGGER = logging.getLogger(__name__)


def _number(value: object) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        result = float(value)
        if math.isfinite(result) and result >= 0:
            return result
    return None


def _integer(value: object) -> int | None:
    number = _number(value)
    return int(number) if number is not None and number.is_integer() else None


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _metadata(info: dict[str, Any], url: str) -> VideoInfo:
    playlist = info.get("_type") in {"playlist", "multi_video"}
    entries = info.get("entries")
    count = _integer(info.get("playlist_count"))
    if count is None:
        count = len(entries) if isinstance(entries, (list, tuple)) else None
    heights: set[int] = set()
    for item in info.get("formats") or []:
        if isinstance(item, dict) and item.get("vcodec") != "none":
            height = _integer(item.get("height"))
            if height is not None and height > 0:
                heights.add(height)
    return VideoInfo(
        title=_text(info.get("title")) or "Untitled media",
        uploader=_text(info.get("uploader")) or _text(info.get("channel")),
        duration=_number(info.get("duration")),
        thumbnail_url=_text(info.get("thumbnail")),
        webpage_url=_text(info.get("webpage_url")) or url,
        extractor=_text(info.get("extractor_key")) or _text(info.get("extractor")) or "Unknown",
        is_playlist=playlist,
        entries_count=count if playlist else 1,
        available_heights=tuple(heights),
    )


def _extract_metadata(engine: yt_dlp.YoutubeDL, url: str) -> dict[str, Any]:
    # process=False preserves lazy playlist entries. lazy_playlist alone still
    # enumerates the playlist in YoutubeDL.__process_playlist.
    info = engine.extract_info(url, download=False, process=False)
    overlays: list[dict[str, Any]] = []
    for _ in range(10):
        if not isinstance(info, dict):
            raise ExtractionError("The engine returned no media information.")
        if info.get("_type") not in {"url", "url_transparent"}:
            break
        target = _text(info.get("url"))
        if target is None:
            raise ExtractionError("The engine returned an invalid media redirect.")
        if info.get("_type") == "url_transparent":
            overlays.append(info)
        info = engine.extract_info(target, ie_key=info.get("ie_key"), download=False, process=False)
    else:
        raise ExtractionError("The media redirects could not be resolved.")
    for overlay in reversed(overlays):
        for key in ("title", "uploader", "channel", "duration", "thumbnail", "webpage_url"):
            if overlay.get(key) is not None:
                info[key] = overlay[key]
    return info


def get_info(
    url: str, *, cookies_browser: Browser | None = None, cancel_event: Event | None = None
) -> VideoInfo:
    """Analyze one URL without downloading media or traversing a playlist.

    Args:
        url: HTTP/HTTPS media URL.
        cookies_browser: Explicit opt-in browser session for authenticated sites.
        cancel_event: Optional cancellation checked before and after extraction.

    Returns:
        Immutable metadata; unavailable playlist counts remain unknown.

    Raises:
        MediaGrabError: Validation, extraction, network, or cancellation failure.
    """
    cancellation = cancel_event if cancel_event is not None else Event()
    try:
        # Reuse request validation for the browser setting without performing I/O.
        request = DownloadRequest(url, Path("."), cookies_browser=cookies_browser)
        check_cancelled(cancellation)
        options: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "js_runtimes": runtime_options(),
            "remote_components": set(),
            "noplaylist": True,
            "socket_timeout": 20,
            "cachedir": False,
            "logger": EngineLogger(_LOGGER),
        }
        if cookies_browser is not None:
            options["cookiesfrombrowser"] = (cookies_browser,)
        with yt_dlp.YoutubeDL(options) as engine:
            info = _extract_metadata(engine, request.url)
        check_cancelled(cancellation)
        return _metadata(info, request.url)
    except Exception as error:
        mapped = map_error(error)
        log_exception(_LOGGER, "Media analysis failed.", error)
        if mapped is error:
            raise
        raise mapped from error


def download(request: DownloadRequest, on_progress: ProgressCallback, cancel_event: Event) -> Path:
    """Download and post-process media, returning the final local file.

    Args:
        request: Validated mode, quality, destination, and privacy settings.
        on_progress: Plain synchronous callback invoked on this worker thread.
        cancel_event: Thread-safe cancellation checked at engine hooks.

    Returns:
        Final MP4 or MP3 path; for a playlist, the last completed entry's path.

    Raises:
        MediaGrabError: Download, conversion, validation, or cancellation failure.
    """
    callback_failed = False

    def emit(event: ProgressEvent) -> None:
        nonlocal callback_failed
        try:
            on_progress(event)
        except Exception:
            callback_failed = True
            raise

    def progress(data: dict[str, Any]) -> None:
        check_cancelled(cancel_event)
        status = data.get("status")
        if status == "downloading":
            total = _integer(data.get("total_bytes"))
            if total is None:
                total = _integer(data.get("total_bytes_estimate"))
            emit(
                ProgressEvent(
                    DownloadStatus.DOWNLOADING,
                    downloaded_bytes=_integer(data.get("downloaded_bytes")) or 0,
                    total_bytes=total,
                    speed_bytes_per_second=_number(data.get("speed")),
                    eta_seconds=_number(data.get("eta")),
                )
            )
        elif status == "finished":
            emit(ProgressEvent(DownloadStatus.PROCESSING))

    def postprocess(data: dict[str, Any]) -> None:
        check_cancelled(cancel_event)
        if data.get("postprocessor") not in {"OutputGuard", "FinalPath"}:
            emit(ProgressEvent(DownloadStatus.PROCESSING))

    def artwork_warning(message: str) -> None:
        emit(ProgressEvent(DownloadStatus.PROCESSING, message=message))

    try:
        check_cancelled(cancel_event)
        validate_url(request.url)
        output_dir = ensure_output_directory(request.output_dir)
        tools = ensure_ffmpeg()
        check_cancelled(cancel_event)
        normalized = replace(request, output_dir=output_dir)
        options = build_options(
            normalized, tools, progress_hooks=[progress], postprocessor_hooks=[postprocess]
        )
        specs = options.pop("postprocessors")
        options["logger"] = EngineLogger(_LOGGER)
        options["js_runtimes"] = runtime_options()
        options["remote_components"] = set()
        # Optional artwork is fetched after audio conversion, so its I/O failures
        # cannot abort a successful media transfer. The wrapper embeds it below.
        if request.format.mode is DownloadMode.AUDIO:
            options["writethumbnail"] = False
        extension = "mp3" if request.format.mode is DownloadMode.AUDIO else "mp4"
        final = FinalPathPP(output_dir, extension, cancel_event)
        with yt_dlp.YoutubeDL(options) as engine:
            engine.add_post_processor(
                OutputGuardPP(
                    output_dir,
                    extension,
                    cancel_event,
                    compatibility=request.prefer_compatibility,
                ),
                when="video",
            )
            for spec in specs:
                arguments = dict(spec)
                key = arguments.pop("key")
                if key == "FFmpegVideoRemuxer":
                    processor = VideoOutputPP(
                        tools, output_dir, cancel_event, request.prefer_compatibility
                    )
                elif key == "EmbedThumbnail":
                    processor = OptionalThumbnailPP(cancel_event, output_dir, artwork_warning)
                else:
                    processor = get_postprocessor(key)(engine, **arguments)
                engine.add_post_processor(processor)
            engine.add_post_processor(final, when="after_move")
            exit_code = engine.download([request.url])
        check_cancelled(cancel_event)
        if exit_code or not final.paths:
            raise ExtractionError("The engine did not complete a media download.")
        path = final.paths[-1]
        emit(ProgressEvent(DownloadStatus.FINISHED, file_path=path))
        return path
    except Exception as error:
        mapped = map_error(error)
        cancelled = isinstance(mapped, DownloadCancelledError)
        if not cancelled:
            log_exception(_LOGGER, "Media download failed.", error)
        if not callback_failed:
            emit(
                ProgressEvent(
                    DownloadStatus.CANCELLED if cancelled else DownloadStatus.ERROR,
                    message=str(mapped),
                )
            )
        if mapped is error:
            raise
        raise mapped from error
