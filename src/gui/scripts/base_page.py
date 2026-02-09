"""Base class for hardware control pages with common functionality.

This module provides an abstract base class that consolidates common patterns
used across hardware control pages, including shared panel access, task lifecycle,
artifact watching, and service signal handling.
"""

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

import device_scripts.setup_cal as setup_cal
from src.config import config
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

    # ---- Layout Factory Methods ----

    def _create_scroll_area(
        self,
        min_width: int | None = None
    ) -> tuple[QScrollArea, QWidget, QVBoxLayout]:
        """Create a scroll area with properly configured content widget.

        This sets up the standard scrollable page structure with:
        - Scroll policies for both directions
        - Expanding size policy on content
        - Configurable minimum width

        Args:
            min_width: Minimum content width (default from config).

        Returns:
            Tuple of (scroll_area, content_widget, main_layout).
        """
        cfg = config.form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content = QWidget()
        content.setMinimumWidth(min_width or cfg.content_min_width)
        content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        main_layout = QVBoxLayout(content)
        main_layout.setSpacing(cfg.layout_spacing)
        main_layout.setContentsMargins(8, 8, 8, 8)

        scroll.setWidget(content)
        return scroll, content, main_layout

    def _create_group_box(
        self,
        title: str,
        min_width: int | None = None,
        min_height: int | None = None,
        expanding: bool = False,
    ) -> QGroupBox:
        """Create a group box with proper size policy.

        Group boxes default to Fixed vertical policy to prevent
        overlapping/squishing within scroll areas.

        Args:
            title: Group box title.
            min_width: Minimum width (optional).
            min_height: Minimum height (default from config).
            expanding: If True, use Expanding vertical policy.

        Returns:
            Configured QGroupBox instance.
        """
        cfg = config.form
        box = QGroupBox(title)
        box.setMinimumHeight(min_height or cfg.group_min_height)
        if min_width:
            box.setMinimumWidth(min_width)

        v_policy = QSizePolicy.Policy.Expanding if expanding else QSizePolicy.Policy.Preferred
        box.setSizePolicy(QSizePolicy.Policy.Expanding, v_policy)

        return box

    @property
    def _group_padding(self) -> tuple[int, int, int, int]:
        """Return the standard group box padding from config.

        Returns:
            tuple[int, int, int, int]: (left, top, right, bottom) margins.
        """
        return config.form.group_padding

    @property
    def _layout_spacing(self) -> int:
        """Return the standard layout spacing from config.

        Returns:
            int: Spacing in pixels between layout sections.
        """
        return config.form.layout_spacing

    def _create_form_layout(self, parent: QWidget | None = None) -> QFormLayout:
        """Create a form layout that prevents field squishing.

        Uses FieldsStayAtSizeHint policy and configures spacing/margins
        from the central config.

        Args:
            parent: Parent widget for the layout.

        Returns:
            Configured QFormLayout instance.
        """
        cfg = config.form
        layout = QFormLayout(parent)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        layout.setVerticalSpacing(cfg.form_spacing)
        layout.setContentsMargins(*cfg.group_padding)
        return layout

    def _configure_input(
        self,
        widget: QWidget,
        min_width: int | None = None,
        min_height: int | None = None,
    ) -> QWidget:
        """Configure an input widget with standard sizing.

        Sets minimum dimensions and Fixed vertical size policy
        to prevent the widget from being squished.

        Args:
            widget: Input widget (QSpinBox, QComboBox, QLineEdit, etc).
            min_width: Override minimum width.
            min_height: Override minimum height.

        Returns:
            The configured widget (for chaining).
        """
        cfg = config.form

        # Determine appropriate height based on widget type
        if min_height is None:
            if isinstance(widget, (QRadioButton, QCheckBox)):
                min_height = cfg.radio_height
            elif isinstance(widget, QPushButton):
                min_height = cfg.button_height
            else:
                min_height = cfg.input_height

        widget.setMinimumHeight(min_height)

        if min_width is None:
            min_width = cfg.input_width

        widget.setMinimumWidth(min_width)

        # Set Fixed vertical policy to prevent squishing
        widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

        return widget
