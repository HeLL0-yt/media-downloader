"""Verify entry-point configuration and version-probe failure handling offline."""

from pathlib import Path
from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from mediagrab.core.errors import FfmpegVersionError
from mediagrab.core.ffmpeg import FfmpegPaths, FfmpegVersions
from mediagrab.desktop import app, workers
from mediagrab.desktop.main_window import MainWindow
from mediagrab.desktop.workers import EngineVersionsWorker, Simulation


def test_entry_point(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    application = Mock()

    def execute() -> int:
        window = next(w for w in QApplication.topLevelWidgets() if isinstance(w, MainWindow))
        assert window.isVisible()
        assert "Phase 3 simulation" in window.windowTitle()
        window.close()
        qtbot.waitUntil(lambda: window._ready_to_close, timeout=15000)
        window.deleteLater()
        return 0

    application.exec.side_effect = execute
    monkeypatch.setattr(app, "QApplication", lambda _argv: application)
    assert app.main() == 0
    application.setApplicationName.assert_called_once_with("MediaGrab")
    application.setStyle.assert_called_once_with("Fusion")
    assert "QProgressBar::chunk" in application.setStyleSheet.call_args.args[0]


@pytest.mark.parametrize("broken", [False, True])
def test_engine_version_signals(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch, broken: bool
) -> None:
    paths = FfmpegPaths(Path("ffmpeg.exe"), Path("ffprobe.exe"))
    monkeypatch.setattr(workers, "locate_ffmpeg", lambda: paths)

    def versions(_paths: FfmpegPaths) -> FfmpegVersions:
        if broken:
            raise FfmpegVersionError()
        return FfmpegVersions("test-version", "test-version")

    monkeypatch.setattr(workers, "get_ffmpeg_versions", versions)
    worker = EngineVersionsWorker()
    with qtbot.waitSignal(worker.result) as signal:
        worker.start()
    qtbot.waitUntil(lambda: worker.isFinished() and worker.wait(0))
    assert signal.args[1] == ("unavailable" if broken else "test-version")
    worker.deleteLater()


@pytest.mark.parametrize("simulation", [(0, 1, None), (0.01, 0, None), (0.01, 2, 3)])
def test_invalid_simulation(simulation: tuple[float, int, int | None]) -> None:
    with pytest.raises(ValueError):
        Simulation(*simulation)
