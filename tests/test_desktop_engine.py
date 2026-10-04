"""Offscreen disclaimer, environment panel and updater tests with no real pip/network."""

from collections.abc import Iterator
from pathlib import Path
from threading import Event
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QMessageBox
from pytestqt.qtbot import QtBot

from mediagrab.core.environment import EnvironmentItem, EnvironmentResult, Severity
from mediagrab.core.errors import DownloadCancelledError
from mediagrab.core.logging_utils import redact_message
from mediagrab.core.models import DownloadRequest, VideoInfo
from mediagrab.core.updater import EngineRelease, UpdateError
from mediagrab.desktop import about, app, engine_panel, engine_workers
from mediagrab.desktop.engine_workers import EngineTaskWorker
from mediagrab.desktop.main_window import MainWindow
from mediagrab.desktop.settings import DesktopSettings, SettingsStore

RELEASE = EngineRelease("2026.12.1", "https://files.pythonhosted.org/fixture.whl", "a" * 64)
REPORT = EnvironmentResult(
    (
        EnvironmentItem("yt-dlp", Severity.OK, "2026.8.19"),
        EnvironmentItem(
            "YouTube JavaScript", Severity.WARNING, "No runtime", "winget install DenoLand.Deno"
        ),
        EnvironmentItem("ffmpeg", Severity.OK, "8", location=Path("C:/Users/private/ffmpeg.exe")),
    )
)


@pytest.fixture
def window(qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[MainWindow]:
    monkeypatch.setattr(engine_workers, "inspect_environment", lambda _cancel: REPORT)
    store = SettingsStore(QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat))
    widget = MainWindow(DesktopSettings(output_dir=tmp_path), settings_store=store)

    def cleanup(widget: MainWindow) -> None:
        widget.close()
        qtbot.waitUntil(lambda: widget._ready_to_close, timeout=15000)

    qtbot.addWidget(widget, before_close_func=cleanup)
    widget.show()
    qtbot.waitUntil(lambda: widget.engine_panel.report is not None)
    yield widget


@pytest.mark.parametrize("accept", [False, True])
def test_disclaimer_acceptance_persists_once(
    qtbot: QtBot,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    accept: bool,
) -> None:
    store = SettingsStore(QSettings(str(tmp_path / "first.ini"), QSettings.Format.IniFormat))
    execute = Mock(
        return_value=QDialog.DialogCode.Accepted if accept else QDialog.DialogCode.Rejected
    )
    monkeypatch.setattr(about.DisclaimerDialog, "exec", execute)
    assert about.ensure_disclaimer(store) == accept
    assert store.backend.value("disclaimer/accepted_v1", False, type=bool) == accept
    if accept:
        assert about.ensure_disclaimer(store)
        execute.assert_called_once()
    else:
        assert not about.ensure_disclaimer(store)
        assert execute.call_count == 2
    dialog = about.DisclaimerDialog(acceptance=True)
    qtbot.addWidget(dialog)
    assert "Terms of Service" in dialog.findChild(QLabel).text()


def test_about_and_help_entries(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch, qtbot: QtBot
) -> None:
    dialog = about.AboutDialog()
    qtbot.addWidget(dialog)
    text = dialog.findChild(QLabel).text()
    assert all(value in text for value in ("MIT", "yt-dlp", "PySide6", "MediaGrab", "DRM"))
    monkeypatch.setattr(about.AboutDialog, "exec", lambda _self: QDialog.DialogCode.Rejected)
    monkeypatch.setattr(about.DisclaimerDialog, "exec", lambda _self: QDialog.DialogCode.Rejected)
    window._about()
    window._disclaimer()
    window._show_engine()
    assert window.engine_panel.isVisible()
    assert not window.engine_panel.isModal()


def test_declining_first_launch_exits_without_window(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from mediagrab.desktop.logging_setup import configure_logging

    monkeypatch.setattr(app, "QApplication", lambda _args: Mock())
    monkeypatch.setattr(app, "ensure_disclaimer", lambda _store: False)
    monkeypatch.setattr(app, "configure_logging", lambda: configure_logging(tmp_path))
    constructor = Mock()
    monkeypatch.setattr(app, "MainWindow", constructor)
    assert app.main() == 0
    constructor.assert_not_called()


def test_environment_warnings_allow_downloads_and_diagnostics_are_private(
    window: MainWindow,
) -> None:
    assert "Engine/Environment" in window.statusBar().currentMessage()
    window.info = VideoInfo("Fixture", "https://example.com/video", "id")
    window._updating(False)
    assert window.download_button.isEnabled()
    text = window.engine_panel.details.toPlainText()
    assert "DenoLand.Deno" in text and "C:" in text
    diagnostics = window.engine_panel.diagnostics()
    assert "C:" not in diagnostics and "private" not in diagnostics
    window.engine_panel.copy_diagnostics()
    assert QApplication.clipboard().text() == diagnostics
    assert "PySide6" in diagnostics
    window._environment(EnvironmentResult((EnvironmentItem("yt-dlp", Severity.OK, "test"),)))
    assert "ready" in window.statusBar().currentMessage()
    window.closing = True
    window._environment(REPORT)
    window.closing = False


def test_open_logs_folder_uses_platform_url(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(engine_panel, "logs_directory", lambda: tmp_path / "logs")
    open_url = Mock(return_value=False)
    monkeypatch.setattr(engine_panel.QDesktopServices, "openUrl", open_url)
    window.engine_panel.open_logs()
    assert (tmp_path / "logs").is_dir()
    assert open_url.call_args.args[0].isLocalFile()
    assert "could not be opened" in window.engine_panel.status.text()


def latest(qtbot: QtBot, window: MainWindow, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(engine_workers, "check_latest", lambda _cancel: RELEASE)
    window.engine_panel.latest.click()
    qtbot.waitUntil(lambda: window.engine_panel.worker is None)
    assert window.engine_panel.update.isEnabled()


def test_confirmation_declined_and_active_guard(
    qtbot: QtBot,
    window: MainWindow,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    latest(qtbot, window, monkeypatch)
    install = Mock()
    monkeypatch.setattr(engine_workers, "update_engine", install)
    question = Mock(return_value=QMessageBox.StandardButton.No)
    monkeypatch.setattr(engine_panel.QMessageBox, "question", question)
    window.engine_panel.update.click()
    install.assert_not_called()
    assert not window.updating
    window.queue.workers["active"] = Mock()
    window.engine_panel.update.click()
    assert "Finish or cancel" in window.engine_panel.status.text()
    question.assert_called_once()
    window.queue.workers.clear()


@pytest.mark.parametrize("mode", ["success", "failure", "cancel"])
def test_update_async_locks_engine_and_reaps_worker(
    qtbot: QtBot,
    window: MainWindow,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    latest(qtbot, window, monkeypatch)
    started = Event()
    release = Event()

    def install(
        _release: EngineRelease, *, confirmed: bool, downloads_active: bool, cancel_event: Event
    ) -> str:
        assert confirmed and not downloads_active
        started.set()
        if mode == "cancel":
            assert cancel_event.wait(3)
            raise DownloadCancelledError()
        assert release.wait(3)
        if mode == "failure":
            raise UpdateError("Pip failure")
        return "captured output"

    monkeypatch.setattr(engine_workers, "update_engine", install)
    monkeypatch.setattr(
        engine_panel.QMessageBox, "question", lambda *_args: QMessageBox.StandardButton.Yes
    )
    window.engine_panel.update.click()
    qtbot.waitUntil(started.is_set)
    assert window.updating and window.queue.suspended
    assert not window.analyze_button.isEnabled()
    window.url.setText("https://example.com/video")
    window._analyze()
    assert window.analysis is None
    count = len(window.queue.items)
    window._add()
    assert len(window.queue.items) == count
    job = window.queue.add(DownloadRequest("https://example.com/video", Path(".")), "staged")
    window.queue.start()
    assert job not in window.queue.workers
    # An event-loop callback still runs while the mocked installer is waiting.
    window.engine_panel.hide()
    window.engine_panel.show()
    if mode == "cancel":
        window.engine_panel.cancel.click()
    else:
        release.set()
    qtbot.waitUntil(lambda: window.engine_panel.worker is None)
    assert window.engine_panel.restart_required
    assert window.updating and window.queue.suspended
    assert not window.engine_panel.update.isEnabled()
    assert "Restart" in window.engine_panel.status.text()


def test_close_cancels_update_and_waits_for_thread(
    qtbot: QtBot, window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    latest(qtbot, window, monkeypatch)
    started = Event()
    returned = Event()

    def install(_release: EngineRelease, **kwargs: object) -> str:
        started.set()
        assert kwargs["cancel_event"].wait(3)
        returned.set()
        raise DownloadCancelledError()

    monkeypatch.setattr(engine_workers, "update_engine", install)
    monkeypatch.setattr(
        engine_panel.QMessageBox, "question", lambda *_args: QMessageBox.StandardButton.Yes
    )
    window.engine_panel.update.click()
    qtbot.waitUntil(started.is_set)
    window.close()
    qtbot.waitUntil(lambda: window._ready_to_close)
    assert returned.is_set() and not window.aux_workers


@pytest.mark.parametrize("operation", ["environment", "latest", "update"])
def test_worker_safe_errors_and_missing_release(
    qtbot: QtBot,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    failure = Mock(side_effect=RuntimeError("private cookie material"))
    monkeypatch.setattr(engine_workers, "inspect_environment", failure)
    monkeypatch.setattr(engine_workers, "check_latest", failure)
    worker = EngineTaskWorker(operation)
    with qtbot.waitSignal(worker.error) as signal:
        worker.start()
    qtbot.waitUntil(lambda: worker.isFinished() and worker.wait(0))
    assert "private" not in signal.args[0]
    worker.deleteLater()


def test_path_redaction() -> None:
    for value in (
        "Failure C:\\Users\\private\\Videos\\movie.mp4",
        'File "/home/private/movie.mp4"',
    ):
        assert "private" not in redact_message(value)


def test_analysis_result_survives_reaping_before_queued_signal(
    window: MainWindow,
    qtbot: QtBot,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from mediagrab.core import downloader

    info = VideoInfo("Fast result", "https://example.com/video", "fixture")
    monkeypatch.setattr(downloader, "get_info", lambda *_args, **_kwargs: info)
    window.url.setText(info.webpage_url)
    window._analyze()
    worker = window.analysis
    assert worker.wait(2000)
    # Force the native cleanup timer to win before the queued result slot.
    window._reap()
    assert window.analysis is None
    qtbot.waitUntil(lambda: window.info is info)
    assert window.download_button.isEnabled()


def test_update_result_processed_before_reap_unlocks(
    qtbot: QtBot,
    window: MainWindow,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    latest(qtbot, window, monkeypatch)
    monkeypatch.setattr(engine_workers, "update_engine", lambda *_args, **_kwargs: "installed")
    monkeypatch.setattr(
        engine_panel.QMessageBox, "question", lambda *_args: QMessageBox.StandardButton.Yes
    )
    window.engine_panel.confirm_update()
    worker = window.engine_panel.worker
    assert worker.wait(2000)
    window._reap()
    assert window.engine_panel.worker is worker
    assert worker in window.aux_workers
    assert window.queue.suspended
    qtbot.waitUntil(lambda: window.engine_panel.worker is None)
    assert window.engine_panel.restart_required and window.queue.suspended


def test_refresh_and_offline_check_leave_queue_available(
    qtbot: QtBot,
    window: MainWindow,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window.engine_panel.refresh.click()
    qtbot.waitUntil(lambda: window.engine_panel.worker is None)
    assert "Environment checked" in window.engine_panel.status.text()
    monkeypatch.setattr(
        engine_workers, "check_latest", Mock(side_effect=UpdateError("Offline. Retry."))
    )
    window.engine_panel.latest.click()
    qtbot.waitUntil(lambda: window.engine_panel.worker is None)
    assert "Offline" in window.engine_panel.status.text()
    assert not window.queue.suspended


def test_first_run_storage_error_is_friendly(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from mediagrab.desktop.logging_setup import configure_logging

    monkeypatch.setattr(app, "QApplication", lambda _args: Mock())
    monkeypatch.setattr(app, "ensure_disclaimer", Mock(side_effect=OSError("private folder")))
    monkeypatch.setattr(app, "configure_logging", lambda: configure_logging(tmp_path))
    message = Mock()
    monkeypatch.setattr(app.QMessageBox, "critical", message)
    assert app.main() == 1
    assert "private folder" not in message.call_args.args[-1]
