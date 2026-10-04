"""Legacy simulation fixtures; production workers always call core."""

import logging
from dataclasses import dataclass
from threading import Event

from PySide6.QtCore import QThread, Signal

from mediagrab.core.models import DownloadRequest, DownloadStatus, ProgressEvent

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Simulation:
    """Deterministic timing and optional error injection for offline verification."""

    interval_seconds: float = 0.08
    steps: int = 40
    fail_at: int | None = None

    def __post_init__(self) -> None:
        """Validate timing and failure boundaries."""
        if self.interval_seconds <= 0 or self.steps < 1:
            raise ValueError("Simulation requires positive timing and steps.")
        if self.fail_at is not None and not 1 <= self.fail_at <= self.steps:
            raise ValueError("Failure step must fall within the simulation.")


class FakeDownloadWorker(QThread):
    """Simulate core ProgressEvent callbacks without network or media writes."""

    progress = Signal(str, object)

    def __init__(
        self, job_id: str, request: DownloadRequest, simulation: Simulation | None = None
    ) -> None:
        """Retain immutable input and a cooperative cancellation token."""
        super().__init__()
        self.job_id = job_id
        self.request = request
        self.simulation = simulation or Simulation()
        self.cancel_event = Event()

    def run(self) -> None:
        """Emit transfer, processing, and exactly one terminal event."""
        total = self.simulation.steps * 1024 * 1024
        for step in range(1, self.simulation.steps + 1):
            if self.cancel_event.wait(self.simulation.interval_seconds):
                self.progress.emit(self.job_id, ProgressEvent(DownloadStatus.CANCELLED))
                return
            if step == self.simulation.fail_at:
                _LOGGER.info("Simulated download failure")
                self.progress.emit(
                    self.job_id,
                    ProgressEvent(DownloadStatus.ERROR, message=self.tr("Simulated failure.")),
                )
                return
            self.progress.emit(
                self.job_id,
                ProgressEvent(
                    DownloadStatus.DOWNLOADING,
                    downloaded_bytes=step * 1024 * 1024,
                    total_bytes=total,
                    speed_bytes_per_second=1024 * 1024 / self.simulation.interval_seconds,
                    eta_seconds=(self.simulation.steps - step) * self.simulation.interval_seconds,
                ),
            )
        self.progress.emit(self.job_id, ProgressEvent(DownloadStatus.PROCESSING))
        cancelled = self.cancel_event.wait(self.simulation.interval_seconds)
        self.progress.emit(
            self.job_id,
            ProgressEvent(DownloadStatus.CANCELLED if cancelled else DownloadStatus.FINISHED),
        )
