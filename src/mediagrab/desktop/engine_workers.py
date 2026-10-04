"""Desktop background adapters for environment and confirmed engine operations."""

import logging
from threading import Event
from typing import Literal

from PySide6.QtCore import QThread, Signal

from mediagrab.core.environment import inspect_environment
from mediagrab.core.errors import DownloadCancelledError
from mediagrab.core.logging_utils import log_exception
from mediagrab.core.updater import EngineRelease, UpdateError, check_latest, update_engine

_LOGGER = logging.getLogger(__name__)


class EngineTaskWorker(QThread):
    """Run bounded diagnostics/network/pip away from the GUI thread."""

    result = Signal(object)
    error = Signal(str)

    def __init__(
        self,
        operation: Literal["environment", "latest", "update"],
        release: EngineRelease | None = None,
    ) -> None:
        """Capture the operation; update workers are created after confirmation."""
        super().__init__()
        self.operation = operation
        self.release = release
        self.cancel_event = Event()

    def run(self) -> None:
        """Emit only immutable results and safe error messages."""
        try:
            if self.operation == "environment":
                result = inspect_environment(self.cancel_event)
            elif self.operation == "latest":
                result = check_latest(self.cancel_event)
            else:
                if self.release is None:
                    raise UpdateError("Check for an engine release first.")
                output = update_engine(
                    self.release,
                    confirmed=True,
                    downloads_active=False,
                    cancel_event=self.cancel_event,
                )
                _LOGGER.info("Engine pip output: %s", output)
                result = "Engine updated. Restart MediaGrab before downloading."
            if not self.cancel_event.is_set():
                self.result.emit(result)
        except DownloadCancelledError:
            self.error.emit("Operation cancelled. If pip started, run pip check before restarting.")
        except Exception as error:
            log_exception(_LOGGER, "Engine operation failed.", error)
            self.error.emit(
                str(error)
                if isinstance(error, UpdateError)
                else "Environment check failed. Open the logs folder for diagnostics."
            )
