"""Offscreen GUI integration with fake metadata, progress and safe close."""

from collections.abc import Iterator
from io import BytesIO
from pathlib import Path
from threading import Event

import pytest
from PySide6.QtCore import QMimeData, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QApplication, QFileDialog, QMenu, QPushButton
from pytestqt.qtbot import QtBot

from mediagrab.core import downloader
from mediagrab.core.models import DownloadMode, DownloadRequest, DownloadStatus, VideoInfo
from mediagrab.core.validators import validate_url
from mediagrab.desktop import workers
from mediagrab.desktop.main_window import MainWindow
from mediagrab.desktop.settings import DesktopSettings
from tests.desktop_fakes import FakeDownloadWorker, Simulation


@pytest.fixture
def window(qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[MainWindow]:
    def get_info(url: str, *, cookies_browser: str | None = None, cancel_event: Event) -> VideoInfo:
        cancel_event.wait(0.05)
        return VideoInfo(
            "Fixture video",
            validate_url(url),
            "fixture",
            uploader="Fixture uploader",
            duration=125,
            available_heights=(360, 480, 720, 1080, 1440, 2160),
            thumbnail_url="https://example.com/thumbnail",
        )

    monkeypatch.setattr(downloader, "get_info", get_info)
    fixture = (Path(workers.__file__).parent / "resources" / "demo.svg").read_bytes()
    monkeypatch.setattr(workers, "urlopen", lambda *args, **kwargs: BytesIO(fixture))
    widget = MainWindow(DesktopSettings(output_dir=tmp_path))
    widget.queue.worker_factory = lambda job_id, request: FakeDownloadWorker(
        job_id, request, Simulation(0.01, 10)
    )

    def cleanup(window: MainWindow) -> None:
        window.close()
        qtbot.waitUntil(lambda: window._ready_to_close, timeout=15000)

    qtbot.addWidget(widget, before_close_func=cleanup)
    widget.show()
    yield widget


def analyze(qtbot: QtBot, window: MainWindow) -> None:
    window.url.setText("https://example.com/video")
    qtbot.mouseClick(window.analyze_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: window.info is not None)


def test_window_analysis_and_download(
    qtbot: QtBot, window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert window.table.columnCount() == 8
    assert not window.add_button.isEnabled()
    analyze(qtbot, window)
    assert window.card.title.text() == "Fixture video"
    assert window.card.duration.text() == "Duration: 2:05"
    qtbot.waitUntil(
        lambda: (
            window.card.thumbnail.pixmap() is not None
            and not window.card.thumbnail.pixmap().isNull()
        )
    )
    qtbot.mouseClick(window.download_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: not window.queue.workers)
    assert window.table.rowCount() == 1
    assert window.table.item(0, 4).text() == "100%"
    assert window.table.item(0, 3).text() == "Finished"
    qtbot.waitUntil(lambda: "Environment:" in window.statusBar().currentMessage(), timeout=15000)
    assert window.engine_panel.report is not None


def test_mode_quality_and_add_queue(qtbot: QtBot, window: MainWindow) -> None:
    analyze(qtbot, window)
    window.mode.setCurrentIndex(1)
    window.bitrate.setCurrentIndex(2)
    assert not window.quality.isEnabled()
    assert window.bitrate.isEnabled()
    qtbot.mouseClick(window.add_button, Qt.MouseButton.LeftButton)
    item = next(iter(window.queue.items.values()))
    assert item.request.format.mode is DownloadMode.AUDIO
    assert item.request.format.audio_bitrate == 192
    assert item.event.status is DownloadStatus.QUEUED
    assert not window.queue.workers
    assert window.table.item(0, 2).text() == "192 kbps"
    window.mode.setCurrentIndex(0)
    window.quality.setCurrentIndex(3)
    qtbot.mouseClick(window.add_button, Qt.MouseButton.LeftButton)
    assert list(window.queue.items.values())[-1].request.format.max_height == 1080


def test_queue_action_buttons(qtbot: QtBot, window: MainWindow) -> None:
    analyze(qtbot, window)
    window.add_button.click()
    job = next(iter(window.queue.items))
    actions = window.table.cellWidget(0, 7)
    actions.findChild(QPushButton, "cancel").click()
    assert window.queue.items[job].event.status is DownloadStatus.CANCELLED
    actions.findChild(QPushButton, "retry").click()
    assert window.queue.items[job].event.status is DownloadStatus.QUEUED
    actions.findChild(QPushButton, "remove").click()
    assert not window.queue.items


def test_context_menu_and_open_folder(
    qtbot: QtBot, window: MainWindow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    analyze(qtbot, window)
    window.add_button.click()
    job = next(iter(window.queue.items))
    opened: list[QUrl] = []

    def open_url(url: QUrl) -> bool:
        opened.append(url)
        return True

    monkeypatch.setattr(QDesktopServices, "openUrl", open_url)
    window.table.cellWidget(0, 7).findChild(QPushButton, "open").click()
    assert Path(opened[0].toLocalFile()) == tmp_path

    window.table._menu(window.table.visualItemRect(window.table.item(0, 0)).center())
    menu = window.table.findChild(QMenu)
    assert menu is not None
    assert [action.text() for action in menu.actions()] == [
        "Cancel",
        "Retry",
        "Open folder",
        "Remove",
    ]
    assert not menu.actions()[1].isEnabled()
    menu.actions()[0].trigger()
    menu.close()
    assert window.queue.items[job].event.status is DownloadStatus.CANCELLED
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda _url: False)
    window._action(job, "open")
    assert window.message.text() == "The output folder could not be opened."


def test_invalid_and_stale_analysis(qtbot: QtBot, window: MainWindow) -> None:
    window.url.setText("invalid")
    window.analyze_button.click()
    qtbot.waitUntil(lambda: window.analysis is None)
    assert "valid HTTP" in window.message.text()
    assert not window.add_button.isEnabled()
    window.url.setText("https://example.com/first")
    window.analyze_button.click()
    window.url.setText("https://example.com/second")
    qtbot.waitUntil(lambda: window.analysis is None)
    assert window.info is None
    assert not window.download_button.isEnabled()
    analyze(qtbot, window)
    window.url.setText("https://example.com/changed")
    assert window.info is None


def test_clipboard_and_url_drop(qtbot: QtBot, window: MainWindow) -> None:
    QApplication.clipboard().setText("https://example.com/pasted")
    window._paste()
    assert window.url.text() == "https://example.com/pasted"
    QApplication.clipboard().setText("https://example.com/shortcut")
    window.url.setFocus()
    window.url.selectAll()
    qtbot.keyClick(window.url, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)
    assert window.url.text() == "https://example.com/shortcut"
    mime = QMimeData()
    mime.setUrls([QUrl("https://example.com/dropped")])
    drag = QDragEnterEvent(
        QPoint(10, 10),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    window.url.dragEnterEvent(drag)
    assert drag.isAccepted()
    drop = QDropEvent(
        QPointF(10, 10),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    window.url.dropEvent(drop)
    assert window.url.text() == "https://example.com/dropped"


def test_folder_picker_and_empty_destination(
    qtbot: QtBot, window: MainWindow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args: str(tmp_path))
    window._browse()
    assert window.folder.text() == str(tmp_path)
    analyze(qtbot, window)
    window.folder.clear()
    window.download_button.click()
    assert not window.queue.items
    assert window.message.text() == "Choose an output folder."


def test_close_during_analysis_and_active_queue(qtbot: QtBot, window: MainWindow) -> None:
    window.queue.worker_factory = lambda job_id, request: FakeDownloadWorker(
        job_id, request, Simulation(0.1, 100)
    )
    for index in range(4):
        window.queue.add(DownloadRequest("https://example.com/video", Path(".")), str(index))
    window.queue.start()
    window.url.setText("https://example.com/video")
    window.analyze_button.click()
    workers = [*window.queue.workers.values(), *window.aux_workers]
    window.close()
    assert window.closing
    assert window.isVisible()
    assert all(worker.cancel_event.is_set() for worker in workers)
    qtbot.waitUntil(lambda: window._ready_to_close, timeout=15000)
    assert not window.isVisible()
    assert not window.queue.workers
    assert not window.aux_workers
    assert all(
        item.event.status is DownloadStatus.CANCELLED for item in window.queue.items.values()
    )
