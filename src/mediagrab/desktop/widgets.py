"""Metadata card, drag/drop input and queue table for the desktop prototype."""

from functools import partial

from PySide6.QtCore import QModelIndex, QPoint, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPainter, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionProgressBar,
    QStyleOptionViewItem,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from mediagrab.core.models import DownloadMode, DownloadStatus, VideoInfo
from mediagrab.desktop.queue_manager import QueueItem


class UrlInput(QLineEdit):
    """Accept ordinary text paste and URL drops without fetching content."""

    def __init__(self) -> None:
        """Enable the native line edit clipboard and drop support."""
        super().__init__()
        self.setAcceptDrops(True)
        self.setPlaceholderText(self.tr("Paste a video URL"))

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Accept URL or text payloads."""
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        """Place the first URL or text in the input."""
        urls = event.mimeData().urls()
        self.setText(urls[0].toString() if urls else event.mimeData().text().strip())
        event.acceptProposedAction()


class InfoCard(QGroupBox):
    """Display signal-delivered metadata and decode thumbnails on the GUI thread."""

    def __init__(self) -> None:
        """Build the empty metadata card."""
        super().__init__(self.tr("Media information"))
        layout = QHBoxLayout(self)
        self.thumbnail = QLabel(self.tr("No thumbnail"))
        self.thumbnail.setFixedSize(192, 108)
        self.thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.thumbnail)
        labels = QVBoxLayout()
        self.title = QLabel(self.tr("Analyze a URL to preview simulated information"))
        self.title.setWordWrap(True)
        self.title.setTextFormat(Qt.TextFormat.PlainText)
        self.uploader = QLabel()
        self.uploader.setTextFormat(Qt.TextFormat.PlainText)
        self.duration = QLabel()
        for label in (self.title, self.uploader, self.duration):
            labels.addWidget(label)
        layout.addLayout(labels, 1)

    def show_info(self, info: VideoInfo, thumbnail: bytes) -> None:
        """Render an immutable worker snapshot."""
        self.title.setText(info.title)
        self.uploader.setText(
            self.tr("Uploader: %1").replace("%1", info.uploader or self.tr("Unknown"))
        )
        duration = self.tr("Unknown")
        if info.duration is not None:
            minutes, seconds = divmod(int(info.duration), 60)
            duration = f"{minutes}:{seconds:02d}"
        self.duration.setText(self.tr("Duration: %1").replace("%1", duration))
        pixmap = QPixmap()
        if pixmap.loadFromData(thumbnail):
            self.thumbnail.setPixmap(
                pixmap.scaled(
                    self.thumbnail.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )


class ProgressDelegate(QStyledItemDelegate):
    """Paint queue transfer percentages using the current Qt style."""

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        """Draw a progress bar or an unknown/processing label."""
        bar = QStyleOptionProgressBar()
        bar.rect = option.rect.adjusted(5, 5, -5, -5)
        bar.minimum = 0
        bar.maximum = 100
        value = index.data(Qt.ItemDataRole.UserRole)
        bar.progress = int(value) if value is not None else 0
        bar.text = str(index.data(Qt.ItemDataRole.DisplayRole))
        bar.textVisible = True
        bar.state = option.state | QStyle.StateFlag.State_Horizontal
        bar.palette = option.palette
        widget = option.widget
        if widget is not None:
            widget.style().drawControl(QStyle.ControlElement.CE_ProgressBar, bar, painter, widget)


class QueueTable(QTableWidget):
    """Render queue state and emit user actions for the owning main window."""

    action = Signal(str, str)

    def __init__(self) -> None:
        """Create columns, progress delegate and context menu."""
        super().__init__(0, 8)
        self.setHorizontalHeaderLabels(
            [
                self.tr("Title"),
                self.tr("Mode"),
                self.tr("Quality"),
                self.tr("Status"),
                self.tr("Progress"),
                self.tr("Speed"),
                self.tr("ETA"),
                self.tr("Actions"),
            ]
        )
        self.setItemDelegateForColumn(4, ProgressDelegate(self))
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)
        self.verticalHeader().hide()
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Interactive)
        self.setColumnWidth(7, 340)
        for column in range(1, 7):
            self.setColumnWidth(column, 105 if column != 3 else 145)
        self._ids: list[str] = []

    def _labels(self) -> dict[str, str]:
        return {
            "cancel": self.tr("Cancel"),
            "retry": self.tr("Retry"),
            "open": self.tr("Open folder"),
            "remove": self.tr("Remove"),
        }

    def update_items(self, items: dict[str, QueueItem], active: set[str]) -> None:
        """Update existing cells, rebuilding action widgets only after row changes."""
        rebuild = list(items) != self._ids
        if rebuild:
            self._ids = list(items)
            self.setRowCount(0)
            self.setRowCount(len(items))
        statuses = {
            DownloadStatus.QUEUED: self.tr("Queued"),
            DownloadStatus.DOWNLOADING: self.tr("Downloading"),
            DownloadStatus.PROCESSING: self.tr("Processing"),
            DownloadStatus.FINISHED: self.tr("Finished (simulated)"),
            DownloadStatus.ERROR: self.tr("Error"),
            DownloadStatus.CANCELLED: self.tr("Cancelled"),
        }
        for row, item in enumerate(items.values()):
            event = item.event
            choice = item.request.format
            video = choice.mode is DownloadMode.VIDEO
            quality = (
                (
                    self.tr("%1p").replace("%1", str(choice.max_height))
                    if choice.max_height
                    else self.tr("Best")
                )
                if video
                else (
                    self.tr("%1 kbps").replace("%1", str(choice.audio_bitrate))
                    if choice.audio_bitrate
                    else self.tr("Best VBR")
                )
            )
            progress = self.tr("Unknown") if event.percent is None else f"{event.percent:.0f}%"
            if event.status is DownloadStatus.PROCESSING:
                progress = self.tr("Processing")
            speed = (
                self.tr("—")
                if event.speed_bytes_per_second is None
                else self.tr("%1 MiB/s").replace(
                    "%1", f"{event.speed_bytes_per_second / 1024**2:.1f}"
                )
            )
            eta = (
                self.tr("—")
                if event.eta_seconds is None
                else self.tr("%1 s").replace("%1", f"{event.eta_seconds:.0f}")
            )
            values = (
                item.title,
                self.tr("Video") if video else self.tr("MP3"),
                quality,
                statuses[event.status],
                progress,
                speed,
                eta,
            )
            for column, value in enumerate(values):
                cell = self.item(row, column)
                if cell is None:
                    cell = QTableWidgetItem()
                    self.setItem(row, column, cell)
                cell.setText(value)
                cell.setToolTip(event.message or "")
                if column == 4:
                    cell.setData(Qt.ItemDataRole.UserRole, event.percent)
            if rebuild:
                actions = QWidget()
                layout = QHBoxLayout(actions)
                layout.setContentsMargins(3, 2, 3, 2)
                for name, label in self._labels().items():
                    button = QPushButton(label)
                    button.setObjectName(name)
                    button.clicked.connect(partial(self._emit_action, item.job_id, name))
                    layout.addWidget(button)
                self.setCellWidget(row, 7, actions)
                self.setRowHeight(row, 48)
            actions = self.cellWidget(row, 7)
            for button in actions.findChildren(QPushButton):
                button.setEnabled(self._enabled(item, button.objectName(), active))

    @staticmethod
    def _enabled(item: QueueItem, action: str, active: set[str]) -> bool:
        status = item.event.status
        if action == "cancel":
            return status in {
                DownloadStatus.QUEUED,
                DownloadStatus.DOWNLOADING,
                DownloadStatus.PROCESSING,
            }
        if action == "retry":
            return item.job_id not in active and status in {
                DownloadStatus.ERROR,
                DownloadStatus.CANCELLED,
            }
        if action == "remove":
            return item.job_id not in active
        return True

    def _menu(self, point: QPoint) -> None:
        row = self.rowAt(point.y())
        if row < 0:
            return
        menu = QMenu(self)
        actions = self.cellWidget(row, 7)
        for button in actions.findChildren(QPushButton):
            action = menu.addAction(button.text())
            action.setEnabled(button.isEnabled())
            action.triggered.connect(
                partial(self._emit_action, self._ids[row], button.objectName())
            )
        menu.aboutToHide.connect(menu.deleteLater)
        menu.popup(self.viewport().mapToGlobal(point))

    def _emit_action(self, job_id: str, name: str, _checked: bool = False) -> None:
        self.action.emit(job_id, name)
