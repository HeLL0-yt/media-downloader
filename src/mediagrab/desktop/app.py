"""Launch the MediaGrab desktop downloader."""

import logging
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from mediagrab.desktop.logging_setup import configure_logging
from mediagrab.desktop.main_window import MainWindow
from mediagrab.desktop.settings import SettingsStore, apply_theme


def main() -> int:
    """Configure native Qt high-DPI scaling, apply QSS and enter the event loop."""
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("MediaGrab")
    app.setOrganizationName("MediaGrab")
    app.setStyle("Fusion")
    logger = logging.getLogger("mediagrab")
    previous = (logger.level, logger.propagate)
    handler = configure_logging()
    try:
        store = SettingsStore()
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
