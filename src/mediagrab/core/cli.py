"""Manual core verification: python -m mediagrab.core.cli URL --audio."""

import argparse
import logging
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from copy import copy
from pathlib import Path
from threading import Event

from mediagrab.core.downloader import download
from mediagrab.core.env_check import check_environment
from mediagrab.core.errors import DownloadCancelledError, MediaGrabError
from mediagrab.core.logging_utils import format_exception
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
    parser.add_argument(
        "--verbose", action="store_true", help="Show redacted diagnostic tracebacks"
    )
    return parser


class _ConsoleFilter(logging.Filter):
    def __init__(self, verbose: bool) -> None:
        """Store whether diagnostic traceback records may reach the console."""
        super().__init__()
        self._verbose = verbose

    def filter(self, record: logging.LogRecord) -> bool:
        """Keep normal messages and show traceback diagnostics only on request."""
        return self._verbose or not getattr(record, "mediagrab_traceback", False)


class _ConsoleFormatter(logging.Formatter):
    def __init__(self, verbose: bool) -> None:
        """Configure readable status messages and optional Python traceback fields."""
        super().__init__("%(levelname)s: %(message)s")
        self._verbose = verbose

    def format(self, record: logging.LogRecord) -> str:
        """Hide exception/stack fields on a copy, preserving other log handlers."""
        record = copy(record)
        # Raw stack strings can include source lines. Exception frames below use
        # the same redaction helper as core logging instead of Python's formatter.
        record.stack_info = None
        record.exc_text = None
        if self._verbose and record.exc_info and record.exc_info[1] is not None:
            record.exc_text = format_exception(record.exc_info[1])
        record.exc_info = None
        return super().format(record)


@contextmanager
def _console_logging(verbose: bool) -> Iterator[None]:
    logger = logging.getLogger("mediagrab")
    previous_level, previous_propagation = logger.level, logger.propagate
    handler = logging.StreamHandler()
    handler.addFilter(_ConsoleFilter(verbose))
    handler.setFormatter(_ConsoleFormatter(verbose))
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.propagate = False
    logger.addHandler(handler)
    try:
        yield
    finally:
        logger.removeHandler(handler)
        handler.close()
        logger.setLevel(previous_level)
        logger.propagate = previous_propagation


def _progress(event: ProgressEvent) -> None:
    if event.status is DownloadStatus.DOWNLOADING:
        if event.percent is not None:
            _LOGGER.info("Downloading: %.1f%%", event.percent)
    elif event.status is DownloadStatus.FINISHED:
        _LOGGER.info("Saved: %s", event.file_path)
    elif event.status not in {DownloadStatus.ERROR, DownloadStatus.CANCELLED}:
        _LOGGER.info("Merging/converting media")
    # The exception handler reports terminal failures once. Core emits both an
    # event and an exception, so printing both would duplicate the same error.


def main(argv: Sequence[str] | None = None) -> int:
    """Run the manual verification CLI using logging for status and errors.

    Args:
        argv: Arguments without the executable name, or None for sys.argv.

    Returns:
        Zero on success, one on failure, or 130 on cancellation.
    """
    arguments = _parser().parse_args(argv)
    with _console_logging(arguments.verbose):
        return _run(arguments)


def _run(arguments: argparse.Namespace) -> int:
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
        environment = check_environment()
        for warning in environment.warnings:
            _LOGGER.warning("%s", warning)
        _LOGGER.debug(
            "yt-dlp %s; impersonation targets: %s",
            environment.yt_dlp_version,
            ", ".join(environment.impersonation_targets) or "none",
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
