"""Validated desktop preferences, QSettings persistence and settings dialog."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from mediagrab.core.errors import MediaGrabError
from mediagrab.core.models import (
    AUDIO_BITRATES,
    VIDEO_HEIGHTS,
    Browser,
    DownloadMode,
    FormatChoice,
)
from mediagrab.resources import resource_path


@dataclass(frozen=True, slots=True)
class DesktopSettings:
    """Persistent defaults; browser cookies remain disabled unless selected."""

    output_dir: Path = field(default_factory=lambda: Path.home() / "Downloads")
    parallel_limit: int = 2
    mode: DownloadMode = DownloadMode.VIDEO
    max_height: int | None = None
    audio_bitrate: int | None = None
    prefer_compatibility: bool = True
    embed_thumbnail: bool = True
    cookies_browser: Browser | None = None
    theme: str = "dark"

    def __post_init__(self) -> None:
        """Reject unsupported defaults at the persistence boundary."""
        if type(self.parallel_limit) is not int or not 1 <= self.parallel_limit <= 4:
            raise ValueError("Parallel limit must be an integer from 1 to 4.")
        FormatChoice(self.mode, self.max_height, self.audio_bitrate)
        if self.cookies_browser not in (None, "chrome", "firefox", "edge"):
            raise ValueError("Unsupported browser.")
        if self.theme not in ("dark", "light"):
            raise ValueError("Unsupported theme.")


class SettingsStore:
    """Read/write application defaults through an injectable QSettings backend."""

    def __init__(self, backend: QSettings | None = None) -> None:
        """Use explicit organization names, independent of app initialization."""
        self.backend = backend if backend is not None else QSettings("MediaGrab", "MediaGrab")

    def load(self) -> DesktopSettings:
        """Validate stored values and recover safely from corrupt preferences."""
        defaults = DesktopSettings()
        values: dict[str, object] = {}
        for name in defaults.__dataclass_fields__:
            default = getattr(defaults, name)
            value = self.backend.value(name, default)
            try:
                if name == "output_dir":
                    value = Path(str(value)) if value else default
                elif name == "mode":
                    value = DownloadMode(value)
                elif name in {"max_height", "audio_bitrate"}:
                    value = int(value) if value not in (None, "", "best") else None
                elif name == "parallel_limit":
                    value = int(value)
                    if not 1 <= value <= 4:
                        value = default
                elif name in {"prefer_compatibility", "embed_thumbnail"}:
                    value = value if type(value) is bool else str(value).lower() == "true"
                elif name == "cookies_browser":
                    value = value if value in ("chrome", "firefox", "edge") else None
                elif name == "theme":
                    value = value if value in ("dark", "light") else default
                values[name] = value
            except ValueError, TypeError:
                values[name] = default
        try:
            return DesktopSettings(**values)
        except ValueError, TypeError, MediaGrabError:
            return defaults

    def save(self, settings: DesktopSettings) -> None:
        """Save defaults only, never browser cookie material or queue contents."""
        for name in settings.__dataclass_fields__:
            value = getattr(settings, name)
            self.backend.setValue(name, str(value) if isinstance(value, Path) else value)
        self.backend.sync()
        if self.backend.status() != QSettings.Status.NoError:
            raise OSError("Desktop preferences could not be saved.")


class SettingsDialog(QDialog):
    """Edit download defaults without modifying immutable queued requests."""

    def __init__(self, settings: DesktopSettings, parent: QWidget | None = None) -> None:
        """Build the complete Phase 4 preference form."""
        super().__init__(parent)
        self.setWindowTitle(self.tr("Settings"))
        layout = QVBoxLayout(self)
        self.form = QFormLayout()
        layout.addLayout(self.form)
        self.folder = QLineEdit(str(settings.output_dir))
        browse = QPushButton(self.tr("Browse…"))
        browse.clicked.connect(self._browse)
        row = QHBoxLayout()
        row.addWidget(self.folder)
        row.addWidget(browse)
        self.form.addRow(self.tr("Default folder"), row)
        self.mode = QComboBox()
        self.mode.addItem(self.tr("Video (MP4)"), DownloadMode.VIDEO)
        self.mode.addItem(self.tr("MP3"), DownloadMode.AUDIO)
        self.mode.setCurrentIndex(self.mode.findData(settings.mode))
        self.quality = QComboBox()
        self.quality.addItem(self.tr("Best"), None)
        for height in VIDEO_HEIGHTS:
            self.quality.addItem(f"{height}p", height)
        if settings.max_height is not None and settings.max_height not in VIDEO_HEIGHTS:
            self.quality.addItem(f"{settings.max_height}p", settings.max_height)
        self.quality.setCurrentIndex(self.quality.findData(settings.max_height))
        self.bitrate = QComboBox()
        self.bitrate.addItem(self.tr("Best VBR"), None)
        for bitrate in AUDIO_BITRATES:
            self.bitrate.addItem(self.tr("%1 kbps").replace("%1", str(bitrate)), bitrate)
        self.bitrate.setCurrentIndex(self.bitrate.findData(settings.audio_bitrate))
        self.parallel = QSpinBox()
        self.parallel.setRange(1, 4)
        self.parallel.setValue(settings.parallel_limit)
        self.compatibility = QCheckBox(self.tr("Prefer H.264/AAC compatibility"))
        self.compatibility.setChecked(settings.prefer_compatibility)
        self.artwork = QCheckBox(self.tr("Embed MP3 thumbnail (best effort)"))
        self.artwork.setChecked(settings.embed_thumbnail)
        self.cookies = QComboBox()
        self.cookies.addItem(self.tr("Disabled"), None)
        for browser in ("chrome", "firefox", "edge"):
            self.cookies.addItem(browser.title(), browser)
        self.cookies.setCurrentIndex(self.cookies.findData(settings.cookies_browser))
        self.cookies.setToolTip(
            self.tr("Uses your signed-in browser session. Cookies are not saved by MediaGrab.")
        )
        self.theme = QComboBox()
        self.theme.addItem(self.tr("Dark"), "dark")
        self.theme.addItem(self.tr("Light"), "light")
        self.theme.setCurrentIndex(self.theme.findData(settings.theme))
        self.form.addRow(self.tr("Default mode"), self.mode)
        self.form.addRow(self.tr("Video quality"), self.quality)
        self.form.addRow(self.tr("Audio bitrate"), self.bitrate)
        self.form.addRow(self.tr("Parallel downloads"), self.parallel)
        self.form.addRow(self.compatibility)
        self.form.addRow(self.artwork)
        self.form.addRow(self.tr("Cookies from browser"), self.cookies)
        self.form.addRow(self.tr("Theme"), self.theme)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.mode.currentIndexChanged.connect(self._mode_changed)
        self._mode_changed()

    def _mode_changed(self) -> None:
        video = self.mode.currentData() == DownloadMode.VIDEO
        self.form.setRowVisible(self.quality, video)
        self.form.setRowVisible(self.bitrate, not video)

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, self.tr("Choose default folder"), self.folder.text()
        )
        if folder:
            self.folder.setText(folder)

    def preferences(self) -> DesktopSettings:
        """Return the validated form snapshot."""
        return DesktopSettings(
            output_dir=Path(self.folder.text()).expanduser(),
            parallel_limit=self.parallel.value(),
            mode=DownloadMode(self.mode.currentData()),
            max_height=self.quality.currentData(),
            audio_bitrate=self.bitrate.currentData(),
            prefer_compatibility=self.compatibility.isChecked(),
            embed_thumbnail=self.artwork.isChecked(),
            cookies_browser=cast(Browser | None, self.cookies.currentData()),
            theme=self.theme.currentData(),
        )


def apply_theme(application: QApplication, theme: str) -> None:
    """Apply the selected packaged theme to the application."""
    stylesheet = resource_path(f"{theme}.qss").read_text(encoding="utf-8")
    application.setStyleSheet(stylesheet)
