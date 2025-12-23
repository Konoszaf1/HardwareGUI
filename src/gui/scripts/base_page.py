"""Base class for hardware control pages with common functionality.

This module provides an abstract base class that consolidates common patterns
used across hardware control pages, including console management, task lifecycle,
artifact watching, and service signal handling.
"""

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QWidget,
)

import setup_cal
from src.config import config
from src.gui.utils.artifact_watcher import ArtifactWatcher
from src.gui.utils.gui_helpers import append_log
from src.gui.utils.image_viewer import ImageViewerDialog
from src.gui.utils.widget_factories import (
    create_artifact_list_widget,
    create_console_widget,
    create_input_field,
)
from src.logging_config import get_logger
from src.logic.qt_workers import FunctionTask, run_in_thread
from src.logic.vu_service import VoltageUnitService

logger = get_logger(__name__)


class BaseHardwarePage(QWidget):
    """Abstract base class for hardware control pages.

    Provides common functionality:
    - Console widget creation and logging
    - Artifact list with file watcher
    - Input field for interactive prompts
    - Task lifecycle management with busy states
    - Scope verification handling

    Subclasses should:
    - Call super().__init__(parent, service)
    - Set up their specific UI layout
    - Populate self._action_buttons with buttons to enable/disable
    - Add self.console, self.listWidget, self.le_input to their layouts
    - Call self._connect_service_signals() at end of __init__ if needed
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        service: VoltageUnitService | None = None,
    ):
        super().__init__(parent)
        self.service = service
        self._active_task: FunctionTask | None = None
        self._artifact_watcher: ArtifactWatcher | None = None
        self._busy = False

        # Widgets to be added to subclass layouts
        self.console: QPlainTextEdit | None = None
        self.le_input: QLineEdit | None = None
        self.listWidget: QListWidget | None = None

        # Buttons to enable/disable during task execution
        self._action_buttons: list[QPushButton] = []

    # ---- Widget factories ----

    def _create_console(self, max_block_count: int | None = None) -> QPlainTextEdit:
        """Create and return a styled console widget."""
        if max_block_count is None:
            max_block_count = config.console.max_block_count
        self.console = create_console_widget(max_block_count)
        return self.console

    def _create_artifact_list(self) -> QListWidget:
        """Create and return an artifact thumbnail list widget."""
        self.listWidget = create_artifact_list_widget()
        self.listWidget.itemDoubleClicked.connect(self._on_image_double_clicked)
        return self.listWidget

    def _create_input_field(self) -> QLineEdit:
        """Create and return a hidden input field widget."""
        self.le_input = create_input_field()
        self.le_input.returnPressed.connect(self._on_input_return)
        return self.le_input

    # ---- Busy state management ----

    def _set_busy(self, busy: bool) -> None:
        """Enable or disable action buttons based on busy state.

        When busy, all registered action buttons are disabled to prevent
        concurrent task execution.

        Args:
            busy: True to enter busy state, False to enable buttons.
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
        if self.listWidget is None:
            return

        artifact_dir = os.path.abspath(f"calibration_vu{setup_cal.VU_SERIAL}")
        self._artifact_watcher = ArtifactWatcher(self.listWidget, self)
        self._artifact_watcher.setup(artifact_dir)

    def _start_task(self, task: FunctionTask | None) -> None:
        """Start a task with signal connections and lifecycle management.

        Args:
            task: FunctionTask instance from VoltageUnitService, or None.
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
        signals.log.connect(lambda s: append_log(self.console, s))
        signals.error.connect(
            lambda e: (logger.error(f"Task error: {e}"), self._log(f"Error: {e}"))
        )

        def _finished(result):
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

        signals.finished.connect(_finished)
        run_in_thread(task)

    # ---- Logging ----

    def _log(self, msg: str) -> None:
        """Append a message to the console."""
        append_log(self.console, msg)

    # ---- Event handlers ----

    def _on_image_double_clicked(self, item) -> None:
        """Open image viewer dialog for the clicked thumbnail."""
        path = item.data(Qt.UserRole)
        if path:
            dlg = ImageViewerDialog(path, self)
            dlg.exec()

    def _on_input_requested(self, prompt: str) -> None:
        """Show input field when service requests input."""
        if not self.isVisible() or self.le_input is None:
            return
        self._log(f"<b>Input requested:</b> {prompt}")
        self.le_input.setVisible(True)
        self.le_input.setPlaceholderText(prompt if prompt else "Type input here...")
        self.le_input.setFocus()

    def _on_input_return(self) -> None:
        """Handle Enter key in input field."""
        if self.le_input is None:
            return
        text = self.le_input.text()
        self._log(f"> {text}")
        self.le_input.clear()
        self.le_input.setVisible(False)
        if self.service and hasattr(self.service, "provide_input"):
            self.service.provide_input(text)

    def _on_scope_verified(self, verified: bool) -> None:
        """Handle scope verification state changes."""
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
