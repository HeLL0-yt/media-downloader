"""Manual core verification: python -m mediagrab.core.cli URL --audio."""

import argparse
import logging
from collections.abc import Sequence
from pathlib import Path
from threading import Event

from mediagrab.core.downloader import download
from mediagrab.core.errors import DownloadCancelledError, MediaGrabError
from mediagrab.core.models import (
    AUDIO_BITRATES,
    VIDEO_HEIGHTS,
    DownloadMode,
    DownloadRequest,
    DownloadStatus,
    FormatChoice,
    ProgressEvent,
)

_LOGGER = logging.getLogger(__name__)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download media to MP4 or MP3 using MediaGrab.")
    parser.add_argument("url", help="HTTP/HTTPS media URL")
    parser.add_argument("--audio", action="store_true", help="Save MP3 instead of MP4")
    parser.add_argument("--height", choices=["best", *map(str, VIDEO_HEIGHTS)], default="best")
    parser.add_argument("--bitrate", choices=["best", *map(str, AUDIO_BITRATES)], default="best")
    parser.add_argument("--output-dir", type=Path, default=Path("downloads"))
    parser.add_argument("--playlists", action="store_true", help="Enable full playlist downloads")
    parser.add_argument("--cookies-from-browser", choices=["chrome", "firefox", "edge"])
    parser.add_argument("--no-compatibility", action="store_true")
    parser.add_argument("--no-thumbnail", action="store_true")
    return parser


def _progress(event: ProgressEvent) -> None:
    if event.status is DownloadStatus.DOWNLOADING:
        if event.percent is not None:
            _LOGGER.info("Downloading: %.1f%%", event.percent)
    elif event.status is DownloadStatus.FINISHED:
        _LOGGER.info("Saved: %s", event.file_path)
    elif event.status in {DownloadStatus.ERROR, DownloadStatus.CANCELLED}:
        _LOGGER.error("%s", event.message)
    else:
        _LOGGER.info("Merging/converting media")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the manual verification CLI using logging for status and errors.

    Args:
        argv: Arguments without the executable name, or None for sys.argv.

    Returns:
        Zero on success, one on failure, or 130 on cancellation.
    """
    arguments = _parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    cancel_event = Event()
    try:
        request = DownloadRequest(
            arguments.url,
            arguments.output_dir,
            format=FormatChoice(
                mode=DownloadMode.AUDIO if arguments.audio else DownloadMode.VIDEO,
                max_height=None if arguments.height == "best" else int(arguments.height),
                audio_bitrate=None if arguments.bitrate == "best" else int(arguments.bitrate),
            ),
            playlists=arguments.playlists,
            prefer_compatibility=not arguments.no_compatibility,
            embed_thumbnail=not arguments.no_thumbnail,
            cookies_browser=arguments.cookies_from_browser,
        )
        download(request, _progress, cancel_event)
    except KeyboardInterrupt, DownloadCancelledError:
        cancel_event.set()
        _LOGGER.info("Download cancelled.")
        return 130
    except MediaGrabError as error:
        _LOGGER.error("%s", error)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
