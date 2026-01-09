"""Base class for hardware control pages with common functionality.

This module provides an abstract base class that consolidates common patterns
used across hardware control pages, including shared panel access, task lifecycle,
artifact watching, and service signal handling.
"""

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QPushButton,
    QWidget,
)

import device_scripts.setup_cal as setup_cal
from src.gui.shared_panels_widget import SharedPanelsWidget
from src.gui.utils.artifact_watcher import ArtifactWatcher
from src.gui.utils.image_viewer import ImageViewerDialog
from src.logging_config import get_logger
from src.logic.qt_workers import FunctionTask, run_in_thread
from src.logic.services.vu_service import VoltageUnitService

# Import status bar service lazily to avoid circular imports
_status_bar_service = None


def _get_status_bar():
    """Lazily get the StatusBarService instance.

    Returns:
        StatusBarService: The service instance if initialized, else None.
    """
    global _status_bar_service
    if _status_bar_service is not None:
        return _status_bar_service
    try:
        from src.gui.services.status_bar_service import StatusBarService

        _status_bar_service = StatusBarService.instance()
        return _status_bar_service
    except RuntimeError:
        return None  # Service not initialized yet, don't cache


logger = get_logger(__name__)


class BaseHardwarePage(QWidget):
    """Abstract base class for hardware control pages.

    Provides common functionality:
    - Shared panel access (console, artifacts, input field)
    - Task lifecycle management with busy states
    - Artifact watching for file updates
    - Scope verification handling

    Attributes:
        service (VoltageUnitService | None): Service for hardware operations.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        service: VoltageUnitService | None = None,
        shared_panels: SharedPanelsWidget | None = None,
    ):
        """Initialize the base page.

        Args:
            parent (QWidget | None): Parent widget.
            service (VoltageUnitService | None): Hardware service instance.
            shared_panels (SharedPanelsWidget | None): Shared panels widget.
        """
        super().__init__(parent)
        self.service = service
        self._shared_panels = shared_panels
        self._active_task: FunctionTask | None = None
        self._artifact_watcher: ArtifactWatcher | None = None
        self._busy = False

        # Buttons to enable/disable during task execution
        self._action_buttons: list[QPushButton] = []

        # Connect input field if available
        if self._shared_panels and self._shared_panels.input_field:
            self._shared_panels.input_field.returnPressed.connect(self._on_input_return)

    # ---- Shared panel accessors ----

    @property
    def shared_panels(self) -> SharedPanelsWidget | None:
        """Return the shared panels widget.

        Returns:
            SharedPanelsWidget | None: The shared panels widget.
        """
        return self._shared_panels

    @property
    def console(self):
        """Return the console widget from shared panels.

        Returns:
            QPlainTextEdit | None: The console widget.
        """
        return self._shared_panels.console if self._shared_panels else None

    @property
    def listWidget(self):
        """Return the artifacts list from shared panels.

        Returns:
            QListWidget | None: The artifacts list widget.
        """
        return self._shared_panels.artifacts if self._shared_panels else None

    @property
    def le_input(self):
        """Return the input field from shared panels.

        Returns:
            QLineEdit | None: The input field widget.
        """
        return self._shared_panels.input_field if self._shared_panels else None

    # ---- Busy state management ----

    def _set_busy(self, busy: bool) -> None:
        """Enable or disable action buttons based on busy state.

        When busy, all registered action buttons are disabled to prevent
        concurrent task execution.

        Args:
            busy (bool): True to enter busy state, False to enable buttons.
        """
        self._busy = busy
        for btn in self._action_buttons:
            btn.setEnabled(not busy)

    # ---- Task lifecycle ----

    def _ensure_artifact_watcher(self) -> None:
        """Set up artifact watcher if VU_SERIAL is known and list widget exists.

        Creates an ArtifactWatcher to monitor the calibration artifact directory
        for file changes and update thumbnails accordingly.
        """
        if self._artifact_watcher or not setup_cal.VU_SERIAL:
            return
        if not self._shared_panels:
            return

        artifact_dir = os.path.abspath(f"calibration_vu{setup_cal.VU_SERIAL}")
        self._artifact_watcher = ArtifactWatcher(self._shared_panels.artifacts, self)
        self._artifact_watcher.setup(artifact_dir)

    def _start_task(self, task: FunctionTask | None) -> None:
        """Start a task with signal connections and lifecycle management.

        Args:
            task (FunctionTask | None): FunctionTask instance from VoltageUnitService.
        """
        if not task:
            logger.warning("_start_task called with None task")
            return

        logger.info(f"Starting task: {task}")
        self._active_task = task
        self._ensure_artifact_watcher()

        signals = task.signals
        self._set_busy(True)

        signals.started.connect(lambda: self._log("Started."))
        signals.started.connect(
            lambda: _get_status_bar() and _get_status_bar().set_busy(f"Running: {task.name}")
        )
        signals.log.connect(lambda s: self._log(s))
        signals.error.connect(
            lambda e: (
                logger.error(f"Task error: {e}"),
                self._log(f"Error: {e}"),
                _get_status_bar() and _get_status_bar().show_temporary(f"Error: {task.name}"),
            )
        )

        signals.finished.connect(lambda result: self._on_task_finished(result))
        run_in_thread(task)

    def _on_task_finished(self, result) -> None:
        """Handle task completion.

        Args:
            result: The result of the task.
        """
        self._set_busy(False)
        self._active_task = None
        self._ensure_artifact_watcher()

        if self._artifact_watcher:
            self._artifact_watcher.refresh_thumbnails()

        # Handle coefficient updates if present
        data = getattr(result, "data", None)
        if isinstance(data, dict):
            coeffs = data.get("coeffs")
            if coeffs:
                for ch, vals in coeffs.items():
                    if len(vals) >= 2:
                        self._log(f"Coeff {ch}: k={vals[0]:.6f}, d={vals[1]:.6f}")

        self._log("Finished.")
        status_svc = _get_status_bar()
        if status_svc:
            status_svc.set_ready()

    # ---- Logging ----

    def _log(self, msg: str) -> None:
        """Append a message to the shared console.

        Args:
            msg (str): Message to log.
        """
        if self._shared_panels:
            self._shared_panels.log(msg)

    # ---- Event handlers ----

    def _on_image_double_clicked(self, item) -> None:
        """Open image viewer dialog for the clicked thumbnail.

        Args:
            item (QListWidgetItem): The double-clicked item.
        """
        path = item.data(Qt.UserRole)
        if path:
            dlg = ImageViewerDialog(path, self)
            dlg.exec()

    def _on_input_requested(self, prompt: str) -> None:
        """Show input field when service requests input.

        Args:
            prompt (str): Prompt text to display.
        """
        if not self.isVisible() or not self._shared_panels:
            return
        self._log(f"<b>Input requested:</b> {prompt}")
        self._shared_panels.show_input(prompt)

    def _on_input_return(self) -> None:
        """Handle Enter key in input field."""
        if not self._shared_panels or not self._shared_panels.input_field:
            return
        text = self._shared_panels.input_field.text()
        self._log(f"> {text}")
        self._shared_panels.input_field.clear()
        self._shared_panels.input_field.setVisible(False)
        if self.service and hasattr(self.service, "provide_input"):
            self.service.provide_input(text)

    def _on_scope_verified(self, verified: bool) -> None:
        """Handle scope verification state changes.

        Note: Status bar updates are handled globally by MainWindow.
        This method manages page-local button states and logging.

        Args:
            verified (bool): True if scope is verified, False otherwise.
        """
        for btn in self._action_buttons:
            btn.setEnabled(verified)

        if not verified:
            self._log("Actions disabled: Scope not verified.")
        else:
            self._log("Actions enabled: Scope verified.")

    def _connect_service_signals(self) -> None:
        """Connect common service signals. Call in subclass __init__."""
        if not self.service:
            return
        self.service.inputRequested.connect(self._on_input_requested)
        self.service.scopeVerified.connect(self._on_scope_verified)
        # Apply initial state
        self._on_scope_verified(self.service.is_scope_verified)
