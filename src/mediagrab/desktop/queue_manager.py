"""GUI-thread queue scheduling with replaceable signal-only download workers."""

from collections.abc import Callable
from dataclasses import dataclass, field
from uuid import uuid4

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from mediagrab.core.models import DownloadRequest, DownloadStatus, ProgressEvent
from mediagrab.desktop.workers import DownloadWorker

TERMINAL = frozenset({DownloadStatus.FINISHED, DownloadStatus.ERROR, DownloadStatus.CANCELLED})
type WorkerFactory = Callable[[str, DownloadRequest], DownloadWorker]


@dataclass(slots=True)
class QueueItem:
    """GUI-owned queue state; workers receive only the immutable request."""

    job_id: str
    title: str
    request: DownloadRequest
    event: ProgressEvent = field(default_factory=lambda: ProgressEvent(DownloadStatus.QUEUED))


class QueueManager(QObject):
    """Bound concurrent workers and retain them until native thread completion."""

    changed = Signal()
    event_received = Signal(str, object)
    idle = Signal()

    def __init__(
        self, parallel_limit: int = 2, worker_factory: WorkerFactory = DownloadWorker
    ) -> None:
        """Initialize an inactive queue with injectable workers."""
        super().__init__()
        if type(parallel_limit) is not int or not 1 <= parallel_limit <= 4:
            raise ValueError("Parallel limit must be an integer from 1 to 4.")
        self.parallel_limit = parallel_limit
        self.worker_factory = worker_factory
        self.items: dict[str, QueueItem] = {}
        self.workers: dict[str, DownloadWorker] = {}
        self.running = False
        self.closing = False
        self.suspended = False

    def add(self, request: DownloadRequest, title: str) -> str:
        """Append a request, starting it only if the queue is running."""
        if self.closing:
            raise RuntimeError("Queue is shutting down.")
        job_id = uuid4().hex
        self.items[job_id] = QueueItem(job_id, title, request)
        self.changed.emit()
        self._pump()
        return job_id

    def start(self) -> None:
        """Start queued items up to the parallel limit."""
        if not self.closing:
            self.running = True
            self._pump()

    def set_parallel_limit(self, limit: int) -> None:
        """Apply a validated limit; existing workers finish before downsizing."""
        if type(limit) is not int or not 1 <= limit <= 4:
            raise ValueError("Parallel limit must be an integer from 1 to 4.")
        self.parallel_limit = limit
        self._pump()

    def _pump(self) -> None:
        if not self.running or self.closing or self.suspended:
            return
        for item in self.items.values():
            if len(self.workers) >= self.parallel_limit:
                break
            if item.event.status is not DownloadStatus.QUEUED:
                continue
            worker = self.worker_factory(item.job_id, item.request)
            self.workers[item.job_id] = worker
            worker.progress.connect(self._progress)
            worker.finished.connect(self._stopped)
            item.event = ProgressEvent(DownloadStatus.DOWNLOADING)
            worker.start()
        self.changed.emit()

    @Slot(str, object)
    def _progress(self, job_id: str, event: ProgressEvent) -> None:
        item = self.items.get(job_id)
        if item is None or item.event.status in TERMINAL:
            return
        item.event = event
        self.event_received.emit(job_id, event)
        self.changed.emit()

    @Slot()
    def _stopped(self) -> None:
        # finished can precede native teardown. Poll without waiting on the GUI.
        QTimer.singleShot(0, self._reap)

    @Slot()
    def _reap(self) -> None:
        for job_id, worker in tuple(self.workers.items()):
            if worker.isFinished() and worker.wait(0):
                del self.workers[job_id]
                worker.deleteLater()
        if any(worker.isFinished() for worker in self.workers.values()):
            QTimer.singleShot(10, self._reap)
        self._pump()
        if not self.workers:
            self.idle.emit()
        self.changed.emit()

    def cancel(self, job_id: str) -> None:
        """Cancel queued work immediately or signal an active worker's Event."""
        item = self.items[job_id]
        if item.event.status in TERMINAL:
            return
        worker = self.workers.get(job_id)
        if worker is not None:
            worker.cancel_event.set()
        else:
            self._progress(job_id, ProgressEvent(DownloadStatus.CANCELLED))

    def retry(self, job_id: str) -> bool:
        """Reset failed/cancelled work after its old worker has exited."""
        item = self.items[job_id]
        if (
            self.closing
            or job_id in self.workers
            or item.event.status not in {DownloadStatus.ERROR, DownloadStatus.CANCELLED}
        ):
            return False
        item.event = ProgressEvent(DownloadStatus.QUEUED)
        self.changed.emit()
        self._pump()
        return True

    def remove(self, job_id: str) -> bool:
        """Remove inactive rows; running workers must first be cancelled."""
        if job_id in self.workers:
            return False
        del self.items[job_id]
        self.changed.emit()
        return True

    def shutdown(self) -> None:
        """Stop scheduling and request cancellation without blocking."""
        self.closing = True
        self.running = False
        for job_id in self.items:
            self.cancel(job_id)
        if not self.workers:
            self.idle.emit()
