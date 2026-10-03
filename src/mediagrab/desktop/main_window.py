"""Phase 3 desktop layout and asynchronous worker ownership."""

from pathlib import Path

from PySide6.QtCore import QTimer, QUrl, Slot
from PySide6.QtGui import QCloseEvent, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
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
    VIDEO_HEIGHTS,
    DownloadMode,
    DownloadRequest,
    FormatChoice,
    ProgressEvent,
    VideoInfo,
)
from mediagrab.desktop.queue_manager import QueueManager
from mediagrab.desktop.settings import DesktopSettings
from mediagrab.desktop.widgets import InfoCard, QueueTable, UrlInput
from mediagrab.desktop.workers import EngineVersionsWorker, FakeAnalysisWorker


class MainWindow(QMainWindow):
    """Present offline simulation controls and retain every running thread."""

    def __init__(self, settings: DesktopSettings | None = None) -> None:
        """Build widgets and start a background engine version probe."""
        super().__init__()
        settings = settings or DesktopSettings()
        self.setWindowTitle(self.tr("MediaGrab — Phase 3 simulation"))
        self.resize(1360, 820)
        self.queue = QueueManager(settings.parallel_limit)
        self.info: VideoInfo | None = None
        self.analysis: FakeAnalysisWorker | None = None
        self.aux_workers: list[FakeAnalysisWorker | EngineVersionsWorker] = []
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
        layout.addWidget(
            QLabel(
                self.tr(
                    "Simulation only: no websites are contacted and no media files are created."
                )
            )
        )
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
        layout.addLayout(url_row)
        self.card = InfoCard()
        layout.addWidget(self.card)
        controls = QHBoxLayout()
        form = QFormLayout()
        self.mode = QComboBox()
        self.mode.addItem(self.tr("Video (MP4)"), DownloadMode.VIDEO)
        self.mode.addItem(self.tr("MP3"), DownloadMode.AUDIO)
        self.quality = QComboBox()
        self.quality.addItem(self.tr("Best"), None)
        for height in VIDEO_HEIGHTS:
            self.quality.addItem(self.tr("Up to %1p").replace("%1", str(height)), height)
        self.bitrate = QComboBox()
        self.bitrate.addItem(self.tr("Best VBR"), None)
        for bitrate in AUDIO_BITRATES:
            self.bitrate.addItem(self.tr("%1 kbps").replace("%1", str(bitrate)), bitrate)
        form.addRow(self.tr("Mode"), self.mode)
        form.addRow(self.tr("Video quality"), self.quality)
        form.addRow(self.tr("Audio bitrate"), self.bitrate)
        controls.addLayout(form)
        destination = QVBoxLayout()
        folder_row = QHBoxLayout()
        self.folder = QLineEdit(str(settings.output_dir))
        self.folder.setAccessibleName(self.tr("Output folder"))
        browse = QPushButton(self.tr("Browse…"))
        browse.clicked.connect(self._browse)
        folder_row.addWidget(self.folder, 1)
        folder_row.addWidget(browse)
        destination.addWidget(QLabel(self.tr("Output folder")))
        destination.addLayout(folder_row)
        buttons = QHBoxLayout()
        self.add_button = QPushButton(self.tr("Add to queue"))
        self.add_button.clicked.connect(self._add)
        self.download_button = QPushButton(self.tr("Download"))
        self.download_button.setObjectName("downloadButton")
        self.download_button.clicked.connect(self._download)
        start = QPushButton(self.tr("Start queue"))
        start.clicked.connect(self.queue.start)
        for button in (self.add_button, self.download_button, start):
            buttons.addWidget(button)
        destination.addLayout(buttons)
        controls.addLayout(destination, 1)
        layout.addLayout(controls)
        self.message = QLabel(self.tr("Ready for simulated analysis."))
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        self.table = QueueTable()
        layout.addWidget(self.table, 1)
        self.statusBar().showMessage(self.tr("Reading engine versions…"))
        self.mode.currentIndexChanged.connect(self._mode_changed)
        self._mode_changed()
        self._invalidate()

    @Slot()
    def _mode_changed(self) -> None:
        video = self.mode.currentData() == DownloadMode.VIDEO
        self.quality.setEnabled(video)
        self.bitrate.setEnabled(not video)

    @Slot()
    def _invalidate(self) -> None:
        self.info = None
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
        worker = FakeAnalysisWorker(self.url.text())
        worker.result.connect(self._analyzed)
        worker.error.connect(self.message.setText)
        self.analysis = worker
        self.aux_workers.append(worker)
        self.message.setText(self.tr("Analyzing (simulated)…"))
        worker.start()

    @Slot(object, bytes)
    def _analyzed(self, info: VideoInfo, thumbnail: bytes) -> None:
        if self.closing or info.webpage_url != self.url.text().strip():
            return
        self.info = info
        self.card.show_info(info, thumbnail)
        self.add_button.setEnabled(True)
        self.download_button.setEnabled(True)
        self.message.setText(
            self.tr("Simulated information ready. Add a task or start a simulated download.")
        )

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
            )
        except MediaGrabError:
            self.message.setText(self.tr("Check the URL, output folder and format settings."))
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
            self.tr("yt-dlp: %1 | FFmpeg: %2 | Simulation")
            .replace("%1", yt_dlp)
            .replace("%2", ffmpeg)
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
