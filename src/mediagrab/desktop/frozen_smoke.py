"""Explicit deployment-only GUI smoke without saved acceptance or network traffic."""

import tempfile
import time
from pathlib import Path

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtGui import QIcon, QImageReader
from PySide6.QtWidgets import QApplication, QLabel, QStyleFactory

from mediagrab.desktop.about import AboutDialog, DisclaimerDialog
from mediagrab.desktop.main_window import MainWindow
from mediagrab.desktop.settings import DesktopSettings, SettingsStore, apply_theme
from mediagrab.resources import resource_path
from mediagrab.self_check import validate_environment


def check_ui() -> dict[str, object]:
    """Show real widgets, await offline environment workers and close cooperatively."""
    application = QApplication([])
    application.setStyle("Fusion")
    application.setQuitOnLastWindowClosed(False)
    with tempfile.TemporaryDirectory(prefix="mediagrab-settings-") as directory:
        store = SettingsStore(
            QSettings(str(Path(directory) / "smoke.ini"), QSettings.Format.IniFormat)
        )
        for theme in ("light", "dark"):
            apply_theme(application, theme)
        icon = QIcon(str(resource_path("mediagrab.ico")))
        if icon.isNull():
            raise RuntimeError("Icon could not be loaded.")
        application.setWindowIcon(icon)
        window = MainWindow(DesktopSettings(output_dir=Path(directory)), settings_store=store)
        about = AboutDialog(window)
        disclaimer = DisclaimerDialog(window, acceptance=True)
        window.show()
        about.show()
        disclaimer.show()
        window.engine_panel.show()
        deadline = time.monotonic() + 45
        failure: list[str] = []
        complete = False

        def poll() -> None:
            nonlocal complete
            if window.closing:
                if window._ready_to_close:
                    application.quit()
                return
            report = window.engine_panel.report
            if report is None and time.monotonic() < deadline:
                return
            try:
                if report is None:
                    raise RuntimeError("Environment panel did not finish within 45 seconds.")
                validate_environment(report)
                if not window.engine_panel.details.toPlainText():
                    raise RuntimeError("Environment panel is empty.")
                if "MIT" not in about.findChild(QLabel).text():
                    raise RuntimeError("About text is missing.")
                if "Terms of Service" not in disclaimer.findChild(QLabel).text():
                    raise RuntimeError("Disclaimer text is missing.")
                formats = {bytes(value).decode() for value in QImageReader.supportedImageFormats()}
                if not {"jpeg", "png", "ico", "svg"} <= formats:
                    raise RuntimeError(f"Required Qt image plugins are missing: {sorted(formats)}")
                complete = True
            except Exception as error:
                failure.append(str(error))
            finally:
                about.close()
                disclaimer.close()
                window.engine_panel.close()
                window.close()

        timer = QTimer(window)
        timer.timeout.connect(poll)
        timer.start(100)
        application.exec()
        if failure or not complete:
            raise RuntimeError("; ".join(failure) or "GUI smoke did not complete.")
        return {"ok": True, "platform": application.platformName(), "styles": QStyleFactory.keys()}
