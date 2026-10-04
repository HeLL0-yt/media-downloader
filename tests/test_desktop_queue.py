"""Offline concurrency, signal affinity, cancellation and retry verification."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QObject, QThread, QTimer, Slot
from pytestqt.qtbot import QtBot

from mediagrab.core.models import DownloadRequest, DownloadStatus, ProgressEvent
from mediagrab.desktop.queue_manager import QueueManager
from mediagrab.desktop.settings import DesktopSettings
from tests.desktop_fakes import FakeDownloadWorker, Simulation


@pytest.fixture
def request_data(tmp_path: Path) -> DownloadRequest:
    return DownloadRequest("https://example.com/video", tmp_path)


@pytest.fixture
def manager(qtbot: QtBot) -> Iterator[QueueManager]:
    queue = QueueManager(
        worker_factory=lambda job_id, request: FakeDownloadWorker(
            job_id, request, Simulation(interval_seconds=0.01, steps=12)
        )
    )
    yield queue
    queue.shutdown()
    qtbot.waitUntil(lambda: not queue.workers)


@pytest.mark.parametrize("limit", [1, 2, 3, 4])
def test_parallel_limit_and_fifo(
    qtbot: QtBot, manager: QueueManager, request_data: DownloadRequest, limit: int
) -> None:
    manager.parallel_limit = limit
    ids = [manager.add(request_data, str(index)) for index in range(6)]
    assert not manager.workers
    manager.start()
    assert list(manager.workers) == ids[:limit]
    maxima: list[int] = []
    manager.changed.connect(lambda: maxima.append(len(manager.workers)))
    qtbot.waitUntil(
        lambda: all(i.event.status is DownloadStatus.FINISHED for i in manager.items.values())
    )
    qtbot.waitUntil(lambda: not manager.workers)
    assert max(maxima) <= limit
    assert not list(request_data.output_dir.iterdir())


def test_cancel_queued_and_active_retry(
    qtbot: QtBot, manager: QueueManager, request_data: DownloadRequest
) -> None:
    manager.parallel_limit = 1
    first = manager.add(request_data, "First")
    second = manager.add(request_data, "Second")
    manager.cancel(second)
    assert manager.items[second].event.status is DownloadStatus.CANCELLED
    manager.start()
    assert not manager.remove(first)
    assert not manager.retry(first)
    manager.cancel(first)
    qtbot.waitUntil(lambda: not manager.workers)
    assert manager.items[first].event.status is DownloadStatus.CANCELLED
    assert manager.retry(first)
    qtbot.waitUntil(lambda: not manager.workers)
    assert manager.items[first].event.status is DownloadStatus.FINISHED
    assert not manager.retry(first)
    assert manager.remove(first)
    assert manager.remove(second)


def test_error_and_retry_with_fresh_worker(qtbot: QtBot, request_data: DownloadRequest) -> None:
    attempts = 0

    def factory(job_id: str, request: DownloadRequest) -> FakeDownloadWorker:
        nonlocal attempts
        attempts += 1
        return FakeDownloadWorker(
            job_id, request, Simulation(0.01, 3, fail_at=2 if attempts == 1 else None)
        )

    queue = QueueManager(worker_factory=factory)
    job = queue.add(request_data, "Error fixture")
    queue.start()
    qtbot.waitUntil(lambda: not queue.workers)
    assert queue.items[job].event.status is DownloadStatus.ERROR
    assert queue.items[job].event.message == "Simulated failure."
    assert queue.retry(job)
    qtbot.waitUntil(lambda: not queue.workers)
    assert attempts == 2
    assert queue.items[job].event.status is DownloadStatus.FINISHED
    queue.shutdown()


class Receiver(QObject):
    def __init__(self) -> None:
        super().__init__()
        self.events: list[ProgressEvent] = []
        self.threads: list[QThread] = []

    @Slot(str, object)
    def receive(self, _job_id: str, event: ProgressEvent) -> None:
        self.events.append(event)
        self.threads.append(QThread.currentThread())


def test_worker_signal_flow_and_gui_responsiveness(
    qtbot: QtBot, manager: QueueManager, request_data: DownloadRequest
) -> None:
    receiver = Receiver()
    manager.event_received.connect(receiver.receive)
    heartbeats: list[bool] = []
    timer = QTimer()
    timer.setInterval(2)
    timer.timeout.connect(lambda: heartbeats.append(True))
    timer.start()
    manager.add(request_data, "Signals")
    manager.start()
    qtbot.waitUntil(lambda: not manager.workers)
    timer.stop()
    assert len(heartbeats) > 2
    assert all(thread is receiver.thread() for thread in receiver.threads)
    assert [event.status for event in receiver.events][-2:] == [
        DownloadStatus.PROCESSING,
        DownloadStatus.FINISHED,
    ]
    transfers = [e for e in receiver.events if e.status is DownloadStatus.DOWNLOADING]
    assert all(e.speed_bytes_per_second and e.eta_seconds is not None for e in transfers)
    assert transfers[-1].percent == 100
    assert receiver.events[-1].file_path is None


def test_shutdown_cancels_all_without_starting_pending(
    qtbot: QtBot, manager: QueueManager, request_data: DownloadRequest
) -> None:
    for index in range(5):
        manager.add(request_data, str(index))
    manager.start()
    manager.shutdown()
    qtbot.waitUntil(lambda: not manager.workers)
    assert all(item.event.status is DownloadStatus.CANCELLED for item in manager.items.values())
    manager.start()
    assert not manager.workers
    assert not manager.retry(next(iter(manager.items)))
    with pytest.raises(RuntimeError):
        manager.add(request_data, "After shutdown")


@pytest.mark.parametrize("limit", [0, 5, True])
def test_invalid_parallel_limits(limit: int) -> None:
    with pytest.raises(ValueError):
        QueueManager(limit)
    with pytest.raises(ValueError):
        DesktopSettings(parallel_limit=limit)
