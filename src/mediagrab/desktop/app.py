"""Launch the Phase 3 offline MediaGrab desktop prototype."""

import logging
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from mediagrab.desktop.main_window import MainWindow


def main() -> int:
    """Configure native Qt high-DPI scaling, apply QSS and enter the event loop."""
    logging.basicConfig(level=logging.INFO)
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("MediaGrab")
    app.setOrganizationName("MediaGrab")
    app.setStyle("Fusion")
    app.setStyleSheet(
        (Path(__file__).parent / "resources" / "dark.qss").read_text(encoding="utf-8")
    )
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
