"""Persistent first-run acceptance and application/license information."""

import platform

from PySide6 import __version__ as PYSIDE_VERSION
from PySide6.QtCore import qVersion
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QWidget

from mediagrab import __version__
from mediagrab.core.env_check import YT_DLP_VERSION
from mediagrab.desktop.settings import SettingsStore

DISCLAIMER = (
    "For personal use only. Download only content you have permission to use. "
    "Respect copyright and each platform's Terms of Service. "
    "MediaGrab does not circumvent DRM or other access restrictions."
)


class DisclaimerDialog(QDialog):
    """Require acceptance at first launch; allow later review from Help/About."""

    def __init__(self, parent: QWidget | None = None, *, acceptance: bool = False) -> None:
        """Display the same responsible-use text in both entry points."""
        super().__init__(parent)
        self.setWindowTitle("Responsible use disclaimer")
        layout = QVBoxLayout(self)
        label = QLabel(DISCLAIMER)
        label.setWordWrap(True)
        label.setMinimumWidth(440)
        layout.addWidget(label)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
            if acceptance
            else QDialogButtonBox.StandardButton.Close
        )
        if acceptance:
            buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Accept")
            buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Exit")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


def ensure_disclaimer(store: SettingsStore) -> bool:
    """Persist acceptance only after the user explicitly accepts the dialog."""
    if store.backend.value("disclaimer/accepted_v1", False, type=bool):
        return True
    dialog = DisclaimerDialog(acceptance=True)
    try:
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False
        store.backend.setValue("disclaimer/accepted_v1", True)
        store.backend.sync()
        from PySide6.QtCore import QSettings

        if store.backend.status() != QSettings.Status.NoError:
            raise OSError("Disclaimer acceptance could not be saved.")
        return True
    finally:
        dialog.deleteLater()


class AboutDialog(QDialog):
    """Show installed versions, source license/link and the responsible-use text."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build a read-only information dialog with an official repository link."""
        super().__init__(parent)
        self.setWindowTitle("About MediaGrab")
        layout = QVBoxLayout(self)
        label = QLabel(
            f"<b>MediaGrab {__version__}</b><br>Python {platform.python_version()}<br>"
            f"yt-dlp {YT_DLP_VERSION}<br>"
            f"PySide6 {PYSIDE_VERSION} / Qt {qVersion()}<br>"
            'Source license: MIT<br><a href="https://github.com/mr-ransaz/MediaGrab">'
            "MediaGrab repository</a><br><br>" + DISCLAIMER
        )
        label.setOpenExternalLinks(True)
        label.setWordWrap(True)
        label.setMinimumWidth(480)
        layout.addWidget(label)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
