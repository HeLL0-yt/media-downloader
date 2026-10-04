"""Offline tests of real adapters, typed failures, concurrency and persistence."""

import logging
from collections.abc import Iterator
from dataclasses import replace
from io import BytesIO
from pathlib import Path
from threading import Event, Lock
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QSettings, QThread
from PySide6.QtWidgets import QDialog
from pytestqt.qtbot import QtBot

from mediagrab.core import downloader, errors
from mediagrab.core.models import (
    DownloadMode,
    DownloadRequest,
    DownloadStatus,
    ProgressCallback,
    ProgressEvent,
    VideoInfo,
)
from mediagrab.desktop import workers
from mediagrab.desktop.logging_setup import RedactedFormatter, configure_logging
from mediagrab.desktop.main_window import MainWindow
from mediagrab.desktop.queue_manager import QueueManager
from mediagrab.desktop.settings import DesktopSettings, SettingsDialog, SettingsStore
from mediagrab.desktop.workers import (
    AnalysisWorker,
    DownloadWorker,
    ThumbnailWorker,
    friendly_error,
)


@pytest.fixture
def request_data(tmp_path: Path) -> DownloadRequest:
    return DownloadRequest("https://example.com/video", tmp_path)


@pytest.fixture
def queue(qtbot: QtBot) -> Iterator[QueueManager]:
    manager = QueueManager()
    yield manager
    manager.shutdown()
    qtbot.waitUntil(lambda: not manager.workers)


def test_real_progress_order_and_final_path(
    qtbot: QtBot,
    monkeypatch: pytest.MonkeyPatch,
    request_data: DownloadRequest,
    queue: QueueManager,
) -> None:
    path = request_data.output_dir / "actual.mp4"
    called: list[QThread] = []

    def download(req: DownloadRequest, callback: ProgressCallback, token: Event) -> Path:
        assert req is request_data
        assert not token.is_set()
        called.append(QThread.currentThread())
        callback(ProgressEvent(DownloadStatus.DOWNLOADING, 50, 100, 20, 2))
        callback(ProgressEvent(DownloadStatus.PROCESSING))
        callback(ProgressEvent(DownloadStatus.FINISHED, file_path=path))
        return path

    monkeypatch.setattr(downloader, "download", download)
    received: list[ProgressEvent] = []
    queue.event_received.connect(lambda job, event: received.append(event))
    job = queue.add(request_data, "Real adapter")
    queue.start()
    qtbot.waitUntil(lambda: not queue.workers)
    assert [e.status for e in received] == [
        DownloadStatus.DOWNLOADING,
        DownloadStatus.PROCESSING,
        DownloadStatus.FINISHED,
    ]
    assert received[0].percent == 50
    assert received[0].speed_bytes_per_second == 20
    assert received[0].eta_seconds == 2
    assert queue.items[job].event.file_path == path
    assert called[0] is not queue.thread()


@pytest.mark.parametrize("limit", [1, 2, 3, 4])
def test_real_parallel_limit(
    qtbot: QtBot,
    monkeypatch: pytest.MonkeyPatch,
    request_data: DownloadRequest,
    queue: QueueManager,
    limit: int,
) -> None:
    lock = Lock()
    active = 0
    maximum = 0
    started: list[str] = []
    release = Event()

    def download(req: DownloadRequest, callback: ProgressCallback, token: Event) -> Path:
        nonlocal active, maximum
        with lock:
            active += 1
            maximum = max(maximum, active)
            started.append(req.url)
        try:
            while not release.wait(0.01):
                if token.is_set():
                    raise errors.DownloadCancelledError()
            return req.output_dir / "fixture.mp4"
        finally:
            with lock:
                active -= 1

    monkeypatch.setattr(downloader, "download", download)
    queue.set_parallel_limit(limit)
    ids = [
        queue.add(replace(request_data, url=f"https://example.com/{i}"), str(i)) for i in range(6)
    ]
    queue.start()
    qtbot.waitUntil(lambda: len(started) == limit)
    assert list(queue.workers) == ids[:limit]
    assert len(started) == limit
    release.set()
    qtbot.waitUntil(lambda: not queue.workers)
    assert maximum == limit
    assert all(item.event.status is DownloadStatus.FINISHED for item in queue.items.values())


def test_cancel_error_retry_and_shutdown(
    qtbot: QtBot,
    monkeypatch: pytest.MonkeyPatch,
    request_data: DownloadRequest,
    queue: QueueManager,
) -> None:
    tokens: list[Event] = []

    def download(req: DownloadRequest, callback: ProgressCallback, token: Event) -> Path:
        tokens.append(token)
        callback(ProgressEvent(DownloadStatus.DOWNLOADING, 1, 2))
        if len(tokens) == 1:
            assert token.wait(3)
            callback(ProgressEvent(DownloadStatus.CANCELLED))
            raise errors.DownloadCancelledError()
        if len(tokens) == 2:
            callback(
                ProgressEvent(DownloadStatus.ERROR, message="unsafe https://example.com/secret")
            )
            raise errors.NetworkError("unsafe https://example.com/secret")
        return req.output_dir / "retried.mp4"

    monkeypatch.setattr(downloader, "download", download)
    queue.set_parallel_limit(1)
    job = queue.add(request_data, "Cancelled")
    pending = queue.add(request_data, "Pending")
    queue.cancel(pending)
    queue.start()
    qtbot.waitUntil(lambda: len(tokens) == 1)
    old = queue.workers[job]
    queue.cancel(job)
    assert old.cancel_event is tokens[0]
    assert tokens[0].is_set()
    assert not queue.remove(job)
    assert not queue.retry(job)
    qtbot.waitUntil(lambda: not queue.workers)
    assert queue.items[job].event.status is DownloadStatus.CANCELLED
    assert queue.retry(job)
    qtbot.waitUntil(lambda: not queue.workers)
    assert queue.items[job].event.status is DownloadStatus.ERROR
    assert queue.items[job].event.message == errors.NetworkError.default_message
    assert queue.retry(job)
    qtbot.waitUntil(lambda: not queue.workers)
    assert queue.items[job].event.status is DownloadStatus.FINISHED
    assert len({id(token) for token in tokens}) == 3
    assert queue.remove(job)
    assert queue.remove(pending)


@pytest.mark.parametrize(
    "error_type",
    [
        errors.InvalidUrlError,
        errors.InvalidRequestError,
        errors.OutputDirectoryError,
        errors.FfmpegNotFoundError,
        errors.FfmpegVersionError,
        errors.ExtractionError,
        errors.NetworkError,
        errors.LoginRequiredError,
        errors.GeoBlockedError,
        errors.PrivateVideoError,
        errors.AgeRestrictionError,
        errors.UnsupportedUrlError,
        errors.FormatUnavailableError,
        errors.DrmProtectedError,
        errors.PostProcessingError,
    ],
)
def test_worker_typed_errors(
    qtbot: QtBot,
    monkeypatch: pytest.MonkeyPatch,
    request_data: DownloadRequest,
    error_type: type[errors.MediaGrabError],
) -> None:
    error = error_type("secret https://example.com/?token=private")

    def download(req: DownloadRequest, callback: ProgressCallback, token: Event) -> Path:
        raise error

    monkeypatch.setattr(downloader, "download", download)
    worker = DownloadWorker("test", request_data)
    with qtbot.waitSignal(worker.progress) as signal:
        worker.start()
    qtbot.waitUntil(lambda: worker.isFinished() and worker.wait(0))
    assert signal.args[1].status is DownloadStatus.ERROR
    assert signal.args[1].message == error_type.default_message
    assert (
        friendly_error(RuntimeError("arbitrary secret")) == errors.ExtractionError.default_message
    )
    worker.deleteLater()


def test_analysis_browser_token_and_canonical_metadata(
    qtbot: QtBot,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info = VideoInfo(
        "Canonical", "https://example.com/canonical", "fixture", available_heights=(540, 1080)
    )
    get_info = Mock(return_value=info)
    monkeypatch.setattr(downloader, "get_info", get_info)
    worker = AnalysisWorker(" https://example.com/input ", "firefox")
    with qtbot.waitSignal(worker.result) as signal:
        worker.start()
    qtbot.waitUntil(lambda: worker.isFinished() and worker.wait(0))
    assert signal.args == [info, b""]
    get_info.assert_called_once_with(
        "https://example.com/input",
        cookies_browser="firefox",
        cancel_event=worker.cancel_event,
    )
    worker.deleteLater()


@pytest.mark.parametrize("cancel", [False, True])
def test_analysis_error_and_cancel(
    qtbot: QtBot,
    monkeypatch: pytest.MonkeyPatch,
    cancel: bool,
) -> None:
    def get_info(*args: object, **kwargs: object) -> VideoInfo:
        raise errors.NetworkError("secret")

    monkeypatch.setattr(downloader, "get_info", get_info)
    worker = AnalysisWorker("https://example.com/input")
    messages: list[str] = []
    worker.error.connect(messages.append)
    if cancel:
        worker.cancel_event.set()
    worker.start()
    qtbot.waitUntil(lambda: worker.isFinished() and worker.wait(0))
    qtbot.wait(10)
    assert messages == ([] if cancel else [errors.NetworkError.default_message])
    worker.deleteLater()


@pytest.mark.parametrize("kind", ["valid", "oversize", "error", "cancel", "invalid"])
def test_thumbnail_fetch_limits_and_failures(
    qtbot: QtBot,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    def fetch(url: str, *, timeout: int) -> BytesIO:
        assert timeout == 10
        if kind == "error":
            raise TimeoutError("https://example.com/?token=secret")
        return BytesIO(b"x" * (10 * 1024 * 1024 + 1) if kind == "oversize" else b"image")

    monkeypatch.setattr(workers, "urlopen", fetch)
    info = VideoInfo(
        "Image",
        "https://example.com/video",
        "fixture",
        thumbnail_url="file:///secret" if kind == "invalid" else "https://example.com/image",
    )
    worker = ThumbnailWorker(info)
    results: list[bytes] = []
    worker.result.connect(lambda info, data: results.append(data))
    if kind == "cancel":
        worker.cancel_event.set()
    worker.start()
    qtbot.waitUntil(lambda: worker.isFinished() and worker.wait(0))
    qtbot.wait(10)
    assert results == ([b"image"] if kind == "valid" else [])
    worker.deleteLater()


def test_settings_round_trip_and_corruption(tmp_path: Path) -> None:
    backend = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    store = SettingsStore(backend)
    assert store.load() == DesktopSettings()
    settings = DesktopSettings(
        tmp_path, 4, DownloadMode.AUDIO, 1080, 192, False, False, "edge", "light"
    )
    store.save(settings)
    assert (
        SettingsStore(QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)).load()
        == settings
    )
    for field, value in [
        ("parallel_limit", 8),
        ("mode", "bad"),
        ("max_height", "bad"),
        ("theme", "bad"),
        ("cookies_browser", "bad"),
    ]:
        backend.setValue(field, value)
    loaded = store.load()
    assert loaded.parallel_limit == 2
    assert loaded.mode is DownloadMode.VIDEO
    assert loaded.theme == "dark"
    assert loaded.cookies_browser is None


def test_settings_dialog_controls(qtbot: QtBot, tmp_path: Path) -> None:
    dialog = SettingsDialog(DesktopSettings(output_dir=tmp_path))
    qtbot.addWidget(dialog)
    dialog.show()
    assert dialog.bitrate.isHidden()
    dialog.mode.setCurrentIndex(1)
    assert dialog.quality.isHidden()
    assert not dialog.bitrate.isHidden()
    dialog.bitrate.setCurrentIndex(dialog.bitrate.findData(192))
    dialog.parallel.setValue(4)
    dialog.compatibility.setChecked(False)
    dialog.artwork.setChecked(False)
    dialog.cookies.setCurrentIndex(dialog.cookies.findData("chrome"))
    dialog.theme.setCurrentIndex(dialog.theme.findData("light"))
    result = dialog.preferences()
    assert result == DesktopSettings(
        tmp_path, 4, DownloadMode.AUDIO, None, 192, False, False, "chrome", "light"
    )


def test_window_settings_quality_and_close_real_workers(
    qtbot: QtBot,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    info = VideoInfo(
        "Actual title",
        "https://example.com/canonical",
        "fixture",
        uploader="Actual uploader",
        available_heights=(540, 1080),
    )
    monkeypatch.setattr(downloader, "get_info", lambda *args, **kwargs: info)
    monkeypatch.setattr(workers, "locate_ffmpeg", lambda: None)
    store = SettingsStore(QSettings(str(tmp_path / "prefs.ini"), QSettings.Format.IniFormat))
    settings = DesktopSettings(tmp_path, 1, max_height=1080)
    window = MainWindow(settings, settings_store=store)

    def cleanup(widget: MainWindow) -> None:
        widget.close()
        qtbot.waitUntil(lambda: widget._ready_to_close)

    qtbot.addWidget(window, before_close_func=cleanup)
    window.show()
    window.url.setText("https://example.com/input")
    window.analyze_button.click()
    qtbot.waitUntil(lambda: window.info is info)
    assert window.card.title.text() == "Actual title"
    assert window.card.duration.text() == "Duration: Unknown"
    assert [window.quality.itemData(i) for i in range(window.quality.count())] == [None, 1080, 540]
    assert window.quality.currentData() == 1080
    assert window.bitrate.isHidden()
    changed = replace(
        settings,
        mode=DownloadMode.AUDIO,
        parallel_limit=3,
        cookies_browser="firefox",
        prefer_compatibility=False,
        embed_thumbnail=False,
        theme="light",
    )
    monkeypatch.setattr(SettingsDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    monkeypatch.setattr(SettingsDialog, "preferences", lambda self: changed)
    window._settings_dialog()
    assert store.load() == changed
    assert window.queue.parallel_limit == 3
    assert window.quality.isHidden()
    started = Event()
    returned = Event()

    def download(req: DownloadRequest, callback: ProgressCallback, token: Event) -> Path:
        assert req.cookies_browser == "firefox"
        assert not req.prefer_compatibility
        assert not req.embed_thumbnail
        assert req.format.mode is DownloadMode.AUDIO
        started.set()
        assert token.wait(3)
        returned.set()
        raise errors.DownloadCancelledError()

    monkeypatch.setattr(downloader, "download", download)
    window.download_button.click()
    qtbot.waitUntil(started.is_set)
    job = next(iter(window.queue.items))
    assert window.queue.items[job].request.url == info.webpage_url
    window.close()
    qtbot.waitUntil(lambda: window._ready_to_close)
    assert returned.is_set()
    assert not window.queue.workers
    assert not window.aux_workers
    assert window.queue.items[job].event.status is DownloadStatus.CANCELLED


def test_rotating_logs_redact_tracebacks(tmp_path: Path) -> None:
    logger = logging.getLogger("mediagrab")
    previous = (logger.level, logger.propagate)
    handler = configure_logging(tmp_path)
    try:
        try:
            raise RuntimeError("https://example.com/?token=secret")
        except RuntimeError:
            logger.exception("A worker failed.")
        handler.flush()
        output = (tmp_path / "mediagrab.log").read_text(encoding="utf-8")
        assert "Traceback" in output
        assert "RuntimeError" in output
        assert "secret" not in output
        assert "raise RuntimeError" not in output
        assert handler.maxBytes == 2 * 1024 * 1024
        assert handler.backupCount == 4
        assert not logger.propagate
        handler.maxBytes = 100
        for _ in range(8):
            logger.warning("Rotating record %s", "x" * 100)
        assert len(list(tmp_path.glob("mediagrab.log*"))) == 5
    finally:
        logger.removeHandler(handler)
        handler.close()
        logger.setLevel(previous[0])
        logger.propagate = previous[1]
    record = logging.LogRecord("test", logging.ERROR, __file__, 1, "Cookie: private", (), None)
    assert "private" not in RedactedFormatter().format(record)
    assert record.msg == "Cookie: private"


@pytest.mark.parametrize("field,value", [("max_height", -1), ("audio_bitrate", 256)])
def test_invalid_stored_quality_recovers(tmp_path: Path, field: str, value: int) -> None:
    backend = QSettings(str(tmp_path / "broken.ini"), QSettings.Format.IniFormat)
    backend.setValue(field, value)
    assert SettingsStore(backend).load() == DesktopSettings()


def test_custom_default_height_in_dialog(qtbot: QtBot) -> None:
    dialog = SettingsDialog(DesktopSettings(max_height=540))
    qtbot.addWidget(dialog)
    assert dialog.quality.currentData() == 540
    assert dialog.preferences().max_height == 540
