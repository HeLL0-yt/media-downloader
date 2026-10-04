"""Signal-only background adapters for real core analysis and downloads."""

import logging
from threading import Event
from urllib.request import urlopen

from PySide6.QtCore import QThread, Signal

from mediagrab.core import downloader
from mediagrab.core.env_check import YT_DLP_VERSION
from mediagrab.core.errors import DownloadCancelledError, MediaGrabError
from mediagrab.core.errors_map import map_error
from mediagrab.core.ffmpeg import get_ffmpeg_versions, locate_ffmpeg
from mediagrab.core.logging_utils import log_exception
from mediagrab.core.models import Browser, DownloadRequest, DownloadStatus, ProgressEvent, VideoInfo
from mediagrab.core.validators import validate_url

_LOGGER = logging.getLogger(__name__)


def friendly_error(error: Exception) -> str:
    """Map typed failures to application-owned text without raw exception details."""
    return type(map_error(error)).default_message


class DownloadWorker(QThread):
    """Bridge the real core callback to the existing queue signal contract."""

    progress = Signal(str, object)

    def __init__(self, job_id: str, request: DownloadRequest) -> None:
        """Own immutable input and the core cancellation Event."""
        super().__init__()
        self.job_id = job_id
        self.request = request
        self.cancel_event = Event()

    def run(self) -> None:
        """Run core on this thread and deliver exactly one terminal event."""
        terminal = False

        def progress(event: ProgressEvent) -> None:
            nonlocal terminal
            # Core error callbacks precede the typed exception; map that exception
            # below so arbitrary error text never enters a widget.
            if event.status in {DownloadStatus.ERROR, DownloadStatus.CANCELLED} or terminal:
                return
            terminal = event.status is DownloadStatus.FINISHED
            self.progress.emit(self.job_id, event)

        try:
            path = downloader.download(self.request, progress, self.cancel_event)
            if not terminal:
                progress(ProgressEvent(DownloadStatus.FINISHED, file_path=path))
        except Exception as error:
            if not terminal:
                mapped = map_error(error)
                cancelled = isinstance(mapped, DownloadCancelledError)
                if not cancelled:
                    log_exception(_LOGGER, "Download worker failed.", error)
                self.progress.emit(
                    self.job_id,
                    ProgressEvent(
                        DownloadStatus.CANCELLED if cancelled else DownloadStatus.ERROR,
                        message=friendly_error(error),
                    ),
                )


class AnalysisWorker(QThread):
    """Analyze real metadata without blocking the GUI or waiting for artwork."""

    result = Signal(object, bytes)
    error = Signal(str)

    def __init__(self, url: str, cookies_browser: Browser | None = None) -> None:
        """Capture analysis input and explicit browser-session preference."""
        super().__init__()
        self.url = url.strip()
        self.cookies_browser = cookies_browser
        self.cancel_event = Event()

    def run(self) -> None:
        """Call core get_info and emit safe immutable metadata."""
        try:
            info = downloader.get_info(
                self.url, cookies_browser=self.cookies_browser, cancel_event=self.cancel_event
            )
            if not self.cancel_event.is_set():
                self.result.emit(info, b"")
        except Exception as error:
            if not self.cancel_event.is_set():
                log_exception(_LOGGER, "Analysis worker failed.", error)
                self.error.emit(friendly_error(error))


class ThumbnailWorker(QThread):
    """Fetch a bounded optional preview off the GUI thread."""

    result = Signal(object, bytes)

    def __init__(self, info: VideoInfo) -> None:
        """Keep the exact metadata snapshot to reject stale thumbnail results."""
        super().__init__()
        self.info = info
        self.cancel_event = Event()

    def run(self) -> None:
        """Read at most 10 MiB with socket timeout and cancellation boundaries."""
        try:
            if not self.info.thumbnail_url or self.cancel_event.is_set():
                return
            url = validate_url(self.info.thumbnail_url)
            with urlopen(url, timeout=10) as response:  # noqa: S310 - validated HTTP/HTTPS
                data = bytearray()
                while not self.cancel_event.is_set():
                    chunk = response.read(64 * 1024)
                    if not chunk:
                        self.result.emit(self.info, bytes(data))
                        return
                    data.extend(chunk)
                    if len(data) > 10 * 1024 * 1024:
                        _LOGGER.warning("Preview thumbnail exceeds the size limit.")
                        return
        except Exception as error:
            log_exception(_LOGGER, "Optional preview thumbnail failed.", error)


class EngineVersionsWorker(QThread):
    """Read engine versions through core without blocking the GUI."""

    result = Signal(str, str)

    def __init__(self) -> None:
        """Own a token for desktop shutdown."""
        super().__init__()
        self.cancel_event = Event()

    def run(self) -> None:
        """Discover FFmpeg and execute its bounded core version probes."""
        ffmpeg = self.tr("not found")
        try:
            paths = locate_ffmpeg()
            if paths is not None and not self.cancel_event.is_set():
                ffmpeg = get_ffmpeg_versions(paths).ffmpeg
        except MediaGrabError:
            ffmpeg = self.tr("unavailable")
        if not self.cancel_event.is_set():
            self.result.emit(YT_DLP_VERSION, ffmpeg)
