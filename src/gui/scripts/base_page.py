"""Base class for hardware control pages with common functionality.

This module provides an abstract base class that consolidates common patterns
used across hardware control pages, including shared panel access, task lifecycle,
artifact watching, and service signal handling.
"""

from PySide6.QtCore import QEvent, QObject, QTimer, Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.config import config
from src.gui.utils.artifact_watcher import ArtifactWatcher
from src.gui.utils.image_viewer import ImageViewerDialog
from src.gui.widgets.shared_panels_widget import SharedPanelsWidget
from src.logging_config import get_logger
from src.logic.protocols import ConnectableService
from src.logic.qt_workers import FunctionTask, run_in_thread


class _WheelRedirect(QObject):
    """Redirects wheel events to the nearest ancestor QScrollArea.

    Install on any widget inside a scroll area to prevent it from
    consuming wheel events (e.g. QComboBox, QSpinBox, matplotlib canvas).
    """

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        if event.type() == QEvent.Type.Wheel and isinstance(obj, QWidget):
            parent = obj.parentWidget()
            while parent is not None:
                if isinstance(parent, QScrollArea):
                    # Send directly to the scrollbar — QScrollArea internally
                    # delegates wheel events to the scrollbar, so bypassing
                    # the scroll area and going straight there is reliable.
                    QApplication.sendEvent(parent.verticalScrollBar(), event)
                    return True
                parent = parent.parentWidget()
        return False


# Lazy singleton — created after QApplication exists
_wheel_redirect_instance: _WheelRedirect | None = None


def _wheel_redirect() -> _WheelRedirect:
    global _wheel_redirect_instance
    if _wheel_redirect_instance is None:
        _wheel_redirect_instance = _WheelRedirect()
    return _wheel_redirect_instance


class _ResizeScrollTracker(QObject):
    """Keeps a target widget visible during scroll-area resizes.

    Used to sync page scrolling pixel-for-pixel with the terminal
    expansion animation — each frame the scroll area shrinks, this
    filter calls ensureWidgetVisible to compensate.
    """

    def __init__(self, scroll_area: QScrollArea, target: QWidget):
        super().__init__(scroll_area)
        self._scroll = scroll_area
        self._target = target

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        if event.type() == QEvent.Type.Resize and self._target is not None:
            self._scroll.ensureWidgetVisible(self._target, 0, 50)
        return False

    def detach(self) -> None:
        if self._scroll is not None:
            self._scroll.removeEventFilter(self)
        self._target = None
        self._scroll = None
        self.deleteLater()

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
        service (ConnectableService | None): Service for hardware operations.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        service: ConnectableService | None = None,
        shared_panels: SharedPanelsWidget | None = None,
    ):
        """Initialize the base page.

        Args:
            parent (QWidget | None): Parent widget.
            service (ConnectableService | None): Hardware service instance.
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

        # Cancel button - hidden by default, subclasses place in their layouts
        self._btn_cancel = QPushButton("Cancel")
        self._btn_cancel.setAccessibleName("Cancel task")
        self._btn_cancel.hide()
        self._cancel_connected = False
        self._resize_tracker: _ResizeScrollTracker | None = None

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
        concurrent task execution.  When clearing busy, delegates to
        ``_update_action_buttons_state`` so connection state is respected.

        Args:
            busy (bool): True to enter busy state, False to enable buttons.
        """
        self._busy = busy
        if busy:
            for btn in self._action_buttons:
                btn.setEnabled(False)
        else:
            self._update_action_buttons_state()

    # ---- Task lifecycle ----

    def _ensure_artifact_watcher(self) -> None:
        """Set up artifact watcher if service has an artifact directory.

        Creates an ArtifactWatcher to monitor the calibration artifact directory
        for file changes and update thumbnails accordingly.
        """
        if self._artifact_watcher:
            return
        if not self._shared_panels or not self.service:
            return
        artifact_dir = getattr(self.service, "artifact_dir", None)
        if not artifact_dir:
            return

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

        logger.info("Starting task: %s", task)
        self._active_task = task
        self._ensure_artifact_watcher()

        signals = task.signals
        self._set_busy(True)

        # Show cancel button only if it's been placed in a layout
        if self._btn_cancel.parent() is not None:
            self._btn_cancel.setText("Cancel")
            self._btn_cancel.setEnabled(True)
            self._btn_cancel.show()
            if self._cancel_connected:
                self._btn_cancel.clicked.disconnect(self._on_cancel_task)
            self._btn_cancel.clicked.connect(self._on_cancel_task)
            self._cancel_connected = True

        signals.started.connect(lambda: self._log(f"Started: {task.name}"))
        signals.started.connect(
            lambda: _get_status_bar() and _get_status_bar().set_busy(f"Running: {task.name}")
        )

        # If the terminal is about to auto-open, track resize events on the
        # scroll area so the clicked button's group box scrolls into view
        # pixel-for-pixel as the terminal rises.
        self._install_resize_tracker()

        signals.log.connect(lambda s: self._log(s))
        signals.error.connect(
            lambda e: (
                logger.error("Task error: %s", e),
                self._log(f"Error: {e}"),
                _get_status_bar() and _get_status_bar().show_temporary(f"Error: {task.name}"),
            )
        )

        signals.finished.connect(lambda result: self._on_task_finished(result))
        run_in_thread(task)

    def _on_cancel_task(self) -> None:
        """Request cancellation of the active task."""
        if self._active_task:
            self._active_task.cancel()
            self._btn_cancel.setEnabled(False)
            self._btn_cancel.setText("Cancelling...")
            self._log("Cancellation requested...")

    def _on_task_finished(self, result) -> None:
        """Handle task completion.

        Args:
            result: The result of the task.
        """
        task_name = self._active_task.name if self._active_task else "task"
        if self._btn_cancel.parent() is not None:
            self._btn_cancel.hide()
            if self._cancel_connected:
                self._btn_cancel.clicked.disconnect(self._on_cancel_task)
                self._cancel_connected = False
        self._set_busy(False)
        self._active_task = None
        self._ensure_artifact_watcher()

        if self._artifact_watcher:
            self._artifact_watcher.refresh_thumbnails()

        self._log(f"Finished: {task_name}")
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

    def _install_resize_tracker(self) -> None:
        """Install a resize tracker if the terminal is about to auto-open.

        The tracker calls ensureWidgetVisible on every resize frame,
        keeping the clicked button's group box visible pixel-for-pixel
        as the terminal rises and the scroll area shrinks.
        """
        # Only needed when the console is about to expand
        if not self._shared_panels or self._shared_panels.is_console_visible():
            return

        focus = QApplication.focusWidget()
        if focus is None:
            return

        # Walk up to find the nearest QGroupBox ancestor
        group: QWidget | None = focus
        while group is not None and not isinstance(group, QGroupBox):
            group = group.parentWidget()
        if group is None:
            return

        # Find the scroll area that contains this group box
        scroll: QWidget | None = group.parentWidget()
        while scroll is not None and not isinstance(scroll, QScrollArea):
            scroll = scroll.parentWidget()
        if not isinstance(scroll, QScrollArea):
            return

        # Detach any previous tracker
        self._detach_resize_tracker()

        self._resize_tracker = _ResizeScrollTracker(scroll, group)
        scroll.installEventFilter(self._resize_tracker)
        # Auto-detach after the animation completes (~150ms + margin)
        QTimer.singleShot(300, self._detach_resize_tracker)

    def _detach_resize_tracker(self) -> None:
        """Remove the resize tracker if active."""
        if self._resize_tracker is not None:
            self._resize_tracker.detach()
            self._resize_tracker = None

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

    def _update_action_buttons_state(self) -> None:
        """Enable or disable action buttons based on service connection state.

        Buttons are enabled only when the service reports ``connected == True``.
        """
        if not self.service:
            return
        enabled = self.service.connected
        for btn in self._action_buttons:
            btn.setEnabled(enabled)

    def _on_instrument_verified(self, verified: bool) -> None:
        """Handle instrument verification state changes.

        Note: Status bar updates are handled globally by MainWindow.
        This method logs verification state but does **not** toggle
        buttons - that is handled by ``_update_action_buttons_state``.

        Args:
            verified (bool): True if instrument is verified, False otherwise.
        """
        if verified:
            self._log("Instrument verified.")
        else:
            self._log("Instrument not verified.")

    def _on_connected_changed(self, connected: bool) -> None:
        """Handle service connection state changes.

        Args:
            connected (bool): True when hardware is connected.
        """
        self._update_action_buttons_state()

    def _connect_service_signals(self) -> None:
        """Connect common service signals. Call in subclass __init__."""
        if not self.service:
            return
        self.service.instrumentVerified.connect(self._on_instrument_verified)
        self.service.connectedChanged.connect(self._on_connected_changed)
        # Apply initial state - buttons disabled until connected
        self._update_action_buttons_state()

    # ---- Layout Factory Methods ----

    def _create_scroll_area(
        self, min_width: int | None = None
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
            if isinstance(widget, QRadioButton | QCheckBox):
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

        # Force QComboBox popup to close after selection (Qt bug in QScrollArea)
        if isinstance(widget, QComboBox):
            widget.activated.connect(widget.hidePopup)

        # Redirect wheel events to the scroll area so scrolling doesn't
        # stop when the cursor is over a combo box, spin box, etc.
        widget.installEventFilter(_wheel_redirect())

        return widget
