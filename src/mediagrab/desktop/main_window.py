"""Real desktop downloads and asynchronous worker ownership."""

from pathlib import Path

from PySide6.QtCore import QTimer, QUrl, Slot
from PySide6.QtGui import QCloseEvent, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from mediagrab.core.errors import MediaGrabError
from mediagrab.core.models import (
    AUDIO_BITRATES,
    DownloadMode,
    DownloadRequest,
    FormatChoice,
    ProgressEvent,
    VideoInfo,
)
from mediagrab.desktop.queue_manager import QueueManager
from mediagrab.desktop.settings import DesktopSettings, SettingsDialog, SettingsStore, apply_theme
from mediagrab.desktop.widgets import InfoCard, QueueTable, UrlInput
from mediagrab.desktop.workers import (
    AnalysisWorker,
    EngineVersionsWorker,
    ThumbnailWorker,
    friendly_error,
)


class MainWindow(QMainWindow):
    """Present real download controls and retain every running thread."""

    def __init__(
        self,
        settings: DesktopSettings | None = None,
        *,
        settings_store: SettingsStore | None = None,
    ) -> None:
        """Build widgets and start a background engine version probe."""
        super().__init__()
        self.settings_store = settings_store or SettingsStore()
        settings = settings or self.settings_store.load()
        self.settings = settings
        self.setWindowTitle(self.tr("MediaGrab"))
        self.resize(1360, 820)
        self.queue = QueueManager(settings.parallel_limit)
        self.info: VideoInfo | None = None
        self.analysis: AnalysisWorker | None = None
        self.aux_workers: list[AnalysisWorker | EngineVersionsWorker | ThumbnailWorker] = []
        self.closing = False
        self._ready_to_close = False
        self._build(settings)
        self.queue.changed.connect(self._refresh)
        self.queue.event_received.connect(self._queue_event)
        self.table.action.connect(self._action)
        self.timer = QTimer(self)
        self.timer.setInterval(20)
        self.timer.timeout.connect(self._reap)
        self.timer.start()
        probe = EngineVersionsWorker()
        probe.result.connect(self._versions)
        self.aux_workers.append(probe)
        probe.start()

    def _build(self, settings: DesktopSettings) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(12)
        url_row = QHBoxLayout()
        self.url = UrlInput()
        self.url.setAccessibleName(self.tr("Video URL"))
        self.url.textChanged.connect(self._invalidate)
        self.url.returnPressed.connect(self._analyze)
        paste = QPushButton(self.tr("Paste"))
        paste.clicked.connect(self._paste)
        self.analyze_button = QPushButton(self.tr("Analyze"))
        self.analyze_button.clicked.connect(self._analyze)
        url_row.addWidget(self.url, 1)
        url_row.addWidget(paste)
        url_row.addWidget(self.analyze_button)
        settings_button = QPushButton(self.tr("Settings…"))
        settings_button.clicked.connect(self._settings_dialog)
        url_row.addWidget(settings_button)
        layout.addLayout(url_row)
        self.card = InfoCard()
        layout.addWidget(self.card)
        self.form = QFormLayout()
        form = self.form
        self.mode = QComboBox()
        self.mode.addItem(self.tr("Video (MP4)"), DownloadMode.VIDEO)
        self.mode.addItem(self.tr("MP3"), DownloadMode.AUDIO)
        self.quality = QComboBox()
        self.quality.addItem(self.tr("Best"), None)
        self.bitrate = QComboBox()
        self.bitrate.addItem(self.tr("Best VBR"), None)
        for bitrate in AUDIO_BITRATES:
            self.bitrate.addItem(self.tr("%1 kbps").replace("%1", str(bitrate)), bitrate)
        form.addRow(self.tr("Mode"), self.mode)
        form.addRow(self.tr("Video quality"), self.quality)
        form.addRow(self.tr("Audio bitrate"), self.bitrate)

        folder_row = QHBoxLayout()
        self.folder = QLineEdit(str(settings.output_dir))
        self.folder.setAccessibleName(self.tr("Output folder"))
        browse = QPushButton(self.tr("Browse…"))
        browse.clicked.connect(self._browse)
        folder_row.addWidget(self.folder, 1)
        folder_row.addWidget(browse)
        form.addRow(self.tr("Output folder"), folder_row)
        layout.addLayout(form)
        buttons = QHBoxLayout()
        self.add_button = QPushButton(self.tr("Add to queue"))
        self.add_button.clicked.connect(self._add)
        self.download_button = QPushButton(self.tr("Download"))
        self.download_button.setObjectName("downloadButton")
        self.download_button.clicked.connect(self._download)
        for button in (self.download_button, self.add_button):
            buttons.addWidget(button)
        buttons.addStretch()
        layout.addLayout(buttons)
        self.message = QLabel(self.tr("Ready."))
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        self.table = QueueTable()
        self.table.setMinimumHeight(280)
        layout.addWidget(self.table, 1)
        self.statusBar().showMessage(self.tr("Reading engine versions…"))
        self.mode.currentIndexChanged.connect(self._mode_changed)
        self._apply_settings(settings)
        self._invalidate()

    def _populate_quality(self) -> None:
        self.quality.clear()
        self.quality.addItem(self.tr("Best"), None)
        heights = self.info.available_heights if self.info else ()
        for height in reversed(heights):
            self.quality.addItem(f"{height}p", height)
        index = self.quality.findData(self.settings.max_height)
        self.quality.setCurrentIndex(max(0, index))

    def _apply_settings(self, settings: DesktopSettings) -> None:
        self.settings = settings
        self.folder.setText(str(settings.output_dir))
        self.mode.setCurrentIndex(self.mode.findData(settings.mode))
        self.bitrate.setCurrentIndex(self.bitrate.findData(settings.audio_bitrate))
        self._populate_quality()
        self.queue.set_parallel_limit(settings.parallel_limit)
        self._mode_changed()
        apply_theme(QApplication.instance(), settings.theme)

    @Slot()
    def _settings_dialog(self) -> None:
        dialog = SettingsDialog(self.settings, self)
        try:
            if dialog.exec() == QDialog.DialogCode.Accepted:
                settings = dialog.preferences()
                if not dialog.folder.text().strip():
                    self.message.setText(self.tr("Choose a default output folder."))
                    return
                self.settings_store.save(settings)
                self._apply_settings(settings)
        except OSError:
            self.message.setText(self.tr("Settings could not be saved. Check account permissions."))
        finally:
            dialog.deleteLater()

    @Slot(str)
    def _analysis_error(self, message: str) -> None:
        worker = self.sender()
        if not self.closing and worker is self.analysis and worker.url == self.url.text().strip():
            self.message.setText(message)

    @Slot(object, bytes)
    def _thumbnail_ready(self, info: VideoInfo, thumbnail: bytes) -> None:
        if not self.closing and info is self.info:
            self.card.show_thumbnail(thumbnail)

    @Slot()
    def _mode_changed(self) -> None:
        video = self.mode.currentData() == DownloadMode.VIDEO
        self.quality.setEnabled(video)
        self.bitrate.setEnabled(not video)
        self.form.setRowVisible(self.quality, video)
        self.form.setRowVisible(self.bitrate, not video)

    @Slot()
    def _invalidate(self) -> None:
        self.info = None
        if hasattr(self, "card"):
            self.card.clear_info()
        self.add_button.setEnabled(False)
        self.download_button.setEnabled(False)

    @Slot()
    def _paste(self) -> None:
        self.url.setText(QApplication.clipboard().text().strip())

    @Slot()
    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, self.tr("Choose output folder"), self.folder.text()
        )
        if folder:
            self.folder.setText(folder)

    @Slot()
    def _analyze(self) -> None:
        if self.closing or self.analysis is not None:
            return
        self._invalidate()
        self.analyze_button.setEnabled(False)
        worker = AnalysisWorker(self.url.text(), self.settings.cookies_browser)
        worker.result.connect(self._analyzed)
        worker.error.connect(self._analysis_error)
        self.analysis = worker
        self.aux_workers.append(worker)
        self.message.setText(self.tr("Analyzing…"))
        worker.start()

    @Slot(object, bytes)
    def _analyzed(self, info: VideoInfo, thumbnail: bytes) -> None:
        worker = self.sender()
        if self.closing or worker is not self.analysis or worker.url != self.url.text().strip():
            return
        self.info = info
        self.card.show_info(info, thumbnail)
        self._populate_quality()
        if info.thumbnail_url:
            preview = ThumbnailWorker(info)
            preview.result.connect(self._thumbnail_ready)
            self.aux_workers.append(preview)
            preview.start()
        self.add_button.setEnabled(True)
        self.download_button.setEnabled(True)
        self.message.setText(self.tr("Information ready. Add a task or download."))

    @Slot()
    def _add(self) -> None:
        if self.info is None or self.closing:
            return
        if not self.folder.text().strip():
            self.message.setText(self.tr("Choose an output folder."))
            return
        video = self.mode.currentData() == DownloadMode.VIDEO
        try:
            request = DownloadRequest(
                self.info.webpage_url,
                Path(self.folder.text()).expanduser(),
                FormatChoice(
                    mode=DownloadMode(self.mode.currentData()),
                    max_height=self.quality.currentData() if video else None,
                    audio_bitrate=self.bitrate.currentData() if not video else None,
                ),
                prefer_compatibility=self.settings.prefer_compatibility,
                embed_thumbnail=self.settings.embed_thumbnail,
                cookies_browser=self.settings.cookies_browser,
            )
        except MediaGrabError as error:
            self.message.setText(friendly_error(error))
            return
        self.queue.add(request, self.info.title)

    @Slot()
    def _download(self) -> None:
        count = len(self.queue.items)
        self._add()
        if len(self.queue.items) > count:
            self.queue.start()

    @Slot()
    def _refresh(self) -> None:
        self.table.update_items(self.queue.items, set(self.queue.workers))

    @Slot(str, object)
    def _queue_event(self, _job_id: str, event: ProgressEvent) -> None:
        if event.message:
            self.message.setText(event.message)

    @Slot(str, str)
    def _action(self, job_id: str, action: str) -> None:
        if self.closing:
            return
        if action == "cancel":
            self.queue.cancel(job_id)
        elif action == "retry":
            self.queue.retry(job_id)
        elif action == "remove":
            self.queue.remove(job_id)
        elif action == "open":
            folder = self.queue.items[job_id].request.output_dir
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder.absolute()))):
                self.message.setText(self.tr("The output folder could not be opened."))

    @Slot(str, str)
    def _versions(self, yt_dlp: str, ffmpeg: str) -> None:
        self.statusBar().showMessage(
            self.tr("yt-dlp: %1 | FFmpeg: %2").replace("%1", yt_dlp).replace("%2", ffmpeg)
        )

    @Slot()
    def _reap(self) -> None:
        for worker in tuple(self.aux_workers):
            if worker.isFinished() and worker.wait(0):
                self.aux_workers.remove(worker)
                if worker is self.analysis:
                    self.analysis = None
                    self.analyze_button.setEnabled(not self.closing)
                worker.deleteLater()
        if self.closing and not self.aux_workers and not self.queue.workers:
            self._ready_to_close = True
            self.timer.stop()
            self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Keep the event loop alive until all cancelled workers have exited."""
        if self._ready_to_close:
            event.accept()
            return
        event.ignore()
        if not self.closing:
            self.closing = True
            self.centralWidget().setEnabled(False)
            self.message.setText(self.tr("Stopping workers…"))
            self.queue.shutdown()
            for worker in self.aux_workers:
                worker.cancel_event.set()
