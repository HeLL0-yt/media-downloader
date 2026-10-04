"""Launch the MediaGrab desktop downloader."""

import logging
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from mediagrab.desktop.about import ensure_disclaimer
from mediagrab.desktop.logging_setup import configure_logging
from mediagrab.desktop.main_window import MainWindow
from mediagrab.desktop.settings import SettingsStore, apply_theme
from mediagrab.resources import resource_path


def main() -> int:
    """Configure native Qt high-DPI scaling, apply QSS and enter the event loop."""
    if "--self-check" in sys.argv or "--smoke-test" in sys.argv:
        from mediagrab.self_check import main as check_main

        return check_main(sys.argv[1:])
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("MediaGrab")
    app.setOrganizationName("MediaGrab")
    app.setStyle("Fusion")
    app.setWindowIcon(QIcon(str(resource_path("mediagrab.ico"))))
    logger = logging.getLogger("mediagrab")
    previous = (logger.level, logger.propagate)
    handler = configure_logging()
    try:
        store = SettingsStore()
        try:
            if not ensure_disclaimer(store):
                return 0
        except OSError:
            logger.exception("Disclaimer acceptance could not be saved.")
            QMessageBox.critical(
                None, "MediaGrab", "Acceptance could not be saved. Check account permissions."
            )
            return 1
        settings = store.load()
        apply_theme(app, settings.theme)
        window = MainWindow(settings, settings_store=store)
        window.show()
        return app.exec()
    finally:
        logger.removeHandler(handler)
        handler.close()
        logger.setLevel(previous[0])
        logger.propagate = previous[1]


if __name__ == "__main__":
    raise SystemExit(main())
