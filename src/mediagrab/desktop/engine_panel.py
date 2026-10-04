"""Non-modal environment panel and confirmed engine update controls."""

import platform
import sys
from collections.abc import Callable
from typing import Literal

from PySide6 import __version__ as PYSIDE_VERSION
from PySide6.QtCore import QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from mediagrab import __version__
from mediagrab.core.environment import EnvironmentResult
from mediagrab.core.logging_utils import redact_message
from mediagrab.core.updater import EngineRelease, is_newer
from mediagrab.desktop.engine_workers import EngineTaskWorker
from mediagrab.desktop.logging_setup import logs_directory


class EnginePanel(QDialog):
    """Display diagnostics without blocking downloads or the application loop."""

    environment_changed = Signal(object)

    def __init__(
        self,
        parent: QWidget,
        register: Callable[[EngineTaskWorker], None],
        busy: Callable[[], bool],
        updating: Callable[[bool], None],
    ) -> None:
        """Keep worker ownership in the main window even when this panel is hidden."""
        super().__init__(parent)
        self.setWindowTitle("Engine / Environment")
        self.resize(820, 620)
        self.register = register
        self.busy = busy
        self.updating = updating
        self.report: EnvironmentResult | None = None
        self.release: EngineRelease | None = None
        self.worker: EngineTaskWorker | None = None
        self.restart_required = False
        self._finished_received = False
        layout = QVBoxLayout(self)
        self.details = QPlainTextEdit("Checking environment…")
        self.details.setReadOnly(True)
        layout.addWidget(self.details)
        self.status = QLabel(
            "Update MediaGrab to get a newer engine. Bundled engines cannot use pip."
            if getattr(sys, "frozen", False)
            else "Engine updates require confirmation and an idle download queue."
        )
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        row = QHBoxLayout()
        self.refresh = QPushButton("Refresh environment")
        self.latest = QPushButton("Check latest release")
        self.update = QPushButton("Update engine…")
        self.cancel = QPushButton("Cancel operation")
        self.update.setEnabled(False)
        self.cancel.setEnabled(False)
        self.refresh.clicked.connect(lambda: self.start("environment"))
        self.latest.clicked.connect(lambda: self.start("latest"))
        self.update.clicked.connect(self.confirm_update)
        self.cancel.clicked.connect(self.cancel_operation)
        for button in (self.refresh, self.latest, self.update, self.cancel):
            row.addWidget(button)
        layout.addLayout(row)
        tools = QHBoxLayout()
        logs = QPushButton("Open logs folder")
        logs.clicked.connect(self.open_logs)
        copy = QPushButton("Copy diagnostics")
        copy.clicked.connect(self.copy_diagnostics)
        tools.addWidget(logs)
        tools.addWidget(copy)
        layout.addLayout(tools)

    def set_report(self, report: EnvironmentResult) -> None:
        """Display versions, severities, locations and actionable repair commands."""
        self.report = report
        self.details.setPlainText(
            "\n\n".join(
                f"[{item.severity}] {item.name}: {item.detail}"
                + (f"\nLocation: {item.location}" if item.location else "")
                + (f"\nFix: {item.fix_hint}" if item.fix_hint else "")
                for item in report.items
            )
        )

    def start(self, operation: Literal["environment", "latest", "update"]) -> None:
        """Start a single asynchronous operation, retaining its native thread."""
        if self.worker is not None or self.restart_required:
            return
        worker = EngineTaskWorker(operation, self.release)
        self.worker = worker
        self._finished_received = False
        self.refresh.setEnabled(False)
        self.latest.setEnabled(False)
        self.update.setEnabled(False)
        self.cancel.setEnabled(True)
        self.status.setText("Working…")
        worker.result.connect(self._result)
        worker.error.connect(self._failed)
        worker.finished.connect(self._finished)
        self.register(worker)
        worker.start()

    @Slot(object)
    def _result(self, result: object) -> None:
        if isinstance(result, EnvironmentResult):
            self.set_report(result)
            self.environment_changed.emit(result)
            self.status.setText("Environment checked. Warnings do not block downloads.")
        elif isinstance(result, EngineRelease):
            self.release = result
            self.status.setText(
                f"Latest official release: {result.version}. "
                + (
                    "Update MediaGrab to get a newer engine."
                    if getattr(sys, "frozen", False)
                    else "Update available."
                    if is_newer(result)
                    else "Engine is current."
                )
            )
        else:
            self.restart_required = True
            self.status.setText(str(result))

    @Slot(str)
    def _failed(self, message: str) -> None:
        if self.worker and self.worker.operation == "update":
            self.restart_required = True
            message += " Restart MediaGrab after checking/repairing the venv."
        self.status.setText(message)

    @Slot()
    def _finished(self) -> None:
        # MainWindow retains and reaps the thread. Keep the update lock until it exits.
        self.cancel.setEnabled(False)
        self._finished_received = True

    def reap(self) -> None:
        """Release UI operation state only after native thread completion."""
        if (
            self.worker is None
            or not self._finished_received
            or not self.worker.isFinished()
            or not self.worker.wait(0)
        ):
            return
        was_update = self.worker.operation == "update"
        self.worker = None
        if was_update:
            self.updating(self.restart_required)
        self.refresh.setEnabled(not self.restart_required)
        self.latest.setEnabled(not self.restart_required)
        self.update.setEnabled(
            bool(self.release and is_newer(self.release))
            and not self.restart_required
            and not getattr(sys, "frozen", False)
        )

    @Slot()
    def confirm_update(self) -> None:
        """Require explicit confirmation and an idle engine before creating pip work."""
        if getattr(sys, "frozen", False):
            self.status.setText(
                "Update MediaGrab to get a newer engine. Bundled engines cannot use pip."
            )
            return
        if self.worker is not None or self.release is None or self.restart_required:
            return
        if self.busy():
            self.status.setText("Finish or cancel downloads and analysis before updating.")
            return
        answer = QMessageBox.question(
            self,
            "Confirm engine update",
            f"Install yt-dlp {self.release.version} into this virtual environment using pip?\n"
            "The official wheel SHA-256 will be verified. Restart is required.\n"
            "Cancelling pip during installation can require venv repair.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes or self.busy():
            return
        self.updating(True)
        self.start("update")

    @Slot()
    def cancel_operation(self) -> None:
        """Signal the operation without terminating its Qt thread."""
        if self.worker:
            self.worker.cancel_event.set()
            self.status.setText("Cancelling operation…")

    @Slot()
    def open_logs(self) -> None:
        """Open the bounded diagnostic folder through the platform file manager."""
        folder = logs_directory()
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError:
            self.status.setText("The logs folder could not be created. Check account permissions.")
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder))):
            self.status.setText("The logs folder could not be opened.")

    def diagnostics(self) -> str:
        """Return shareable versions and status, excluding paths, URLs and cookies."""
        lines = [
            f"MediaGrab {__version__}",
            f"Python {platform.python_version()}",
            f"PySide6 {PYSIDE_VERSION}",
            f"OS {platform.system()}",
            f"Frozen: {bool(getattr(sys, 'frozen', False))}",
        ]
        if self.report:
            lines.extend(
                f"{item.name}: {item.severity} — {redact_message(item.detail)}"
                for item in self.report.items
            )
        return "\n".join(lines)

    @Slot()
    def copy_diagnostics(self) -> None:
        """Copy structured diagnostics without raw logs or user folder locations."""
        QApplication.clipboard().setText(self.diagnostics())
        self.status.setText("Redacted diagnostics copied (no folder locations or raw logs).")
