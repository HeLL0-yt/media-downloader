"""Pure construction of verified yt-dlp library options."""

from collections.abc import Callable, Sequence
from typing import Any

from mediagrab.core.ffmpeg import FfmpegPaths
from mediagrab.core.models import DownloadMode, DownloadRequest

# yt-dlp hook payloads and options are heterogeneous third-party dictionaries.
type YtDlpHook = Callable[[dict[str, Any]], None]


def build_options(
    request: DownloadRequest,
    ffmpeg: FfmpegPaths,
    *,
    progress_hooks: Sequence[YtDlpHook] = (),
    postprocessor_hooks: Sequence[YtDlpHook] = (),
) -> dict[str, Any]:
    """Build fresh engine options without I/O or changing caller data.

    Directory creation, executable discovery, cancellation hooks, safe logging,
    and best-effort thumbnail failure handling belong to the download runner.

    Args:
        request: Validated download settings.
        ffmpeg: Executable pair resolved separately by the worker.
        progress_hooks: Raw engine transfer callbacks, copied into a new list.
        postprocessor_hooks: Raw engine processing callbacks, copied likewise.

    Returns:
        yt-dlp options containing verified library names and postprocessor keys.
    """
    # Escape literal percent signs in the destination, not the engine template.
    # Titles and IDs are sanitized by yt-dlp; directory structure is fixed.
    directory = request.output_dir.as_posix().replace("%", "%%")
    template = f"{directory.rstrip('/')}/%(title).150B [%(id)s].%(ext)s"
    options: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "outtmpl": template,
        "windowsfilenames": True,
        "restrictfilenames": False,
        "ffmpeg_location": str(ffmpeg.location),
        "retries": 5,
        "fragment_retries": 5,
        "socket_timeout": 20,
        "concurrent_fragment_downloads": 4,
        "noprogress": True,
        "progress_hooks": list(progress_hooks),
        "postprocessor_hooks": list(postprocessor_hooks),
        "noplaylist": not request.playlists,
        "ignoreerrors": False,
        "cachedir": False,
    }
    if not request.playlists:
        # noplaylist alone does not limit a URL that identifies only a playlist.
        options["playlist_items"] = "1"
    if request.cookies_browser is not None:
        options["cookiesfrombrowser"] = (request.cookies_browser,)
    if request.format.mode is DownloadMode.VIDEO:
        height = request.format.max_height
        ceiling = f"[height<={height}]" if height is not None else ""
        options.update(
            format=f"bestvideo*{ceiling}+bestaudio/best{ceiling}",
            merge_output_format="mp4",
            final_ext="mp4",
            postprocessors=[
                # Merging does not cover a source with a single combined stream.
                {"key": "FFmpegVideoRemuxer", "preferedformat": "mp4"},
                {"key": "FFmpegMetadata"},
            ],
        )
        if request.prefer_compatibility:
            # Preserve resolution first, then prefer H.264/AAC at that resolution.
            # 4K is often VP9/AV1: sorting and an MP4 container do not change codecs.
            # Incompatible streams require re-encoding in the download runner,
            # with extra CPU time and generation loss, for broad player support.
            options["format_sort"] = ["res", "vcodec:h264", "acodec:aac"]
    else:
        bitrate = request.format.audio_bitrate
        processors: list[dict[str, Any]] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "0" if bitrate is None else str(bitrate),
            },
            {"key": "FFmpegMetadata"},
        ]
        if request.embed_thumbnail:
            processors.append({"key": "EmbedThumbnail", "already_have_thumbnail": False})
        options.update(
            format="bestaudio/best",
            final_ext="mp3",
            postprocessors=processors,
            writethumbnail=request.embed_thumbnail,
        )
    return options
