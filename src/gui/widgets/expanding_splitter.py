"""Custom QSplitter Widget to handle the sidebar expansion and collapse."""

from PySide6.QtCore import QEvent, QTimer
from PySide6.QtWidgets import QListView, QSplitter, QWidget

from src.config import config
from src.gui.mixins.animation_mixin import AnimatedWidgetMixin


class ExpandingSplitter(QSplitter, AnimatedWidgetMixin):
    """An expanding sidebar that shows button text over the side list on hover.

    Uses configuration values for timing and dimensions to ensure consistency
    across the application. Animation logic is provided by AnimatedWidgetMixin.

    Attributes:
        buttons (list): List of SidebarButtons managed by this splitter.
    """

    def __init__(self, parent: QWidget | None = None):
        """Initialize the expanding splitter.

        Args:
            parent (QWidget | None): Parent widget.
        """
        super().__init__(parent)
        self._collapsed_width = config.ui.sidebar_collapsed_width
        self._expanded_width = config.ui.sidebar_expanded_width
        self.setMinimumWidth(self._collapsed_width)
        self.buttons: list = []
        self._is_expanded = False
        self.widget: QWidget | None = None
        self.listview: QListView | None = None
        self.sidebar: QWidget | None = None
        if self.parent():
            self.parent().installEventFilter(self)
        self.setHandleWidth(0)
        self.setContentsMargins(0, 0, 0, 0)

        # Timers for hover-based expand/collapse
        self.expand_timer = QTimer(self)
        self.expand_timer.setSingleShot(True)
        self.expand_timer.setInterval(config.ui.expand_hover_delay_ms)
        self.expand_timer.timeout.connect(self.expand)

        self.collapse_timer = QTimer()
        self.collapse_timer.setSingleShot(True)
        self.collapse_timer.timeout.connect(self.collapse)

        # Setup animation using mixin
        self.setup_variant_animation()

    def set_sidebar(self, sidebar: QWidget) -> None:
        """Set the sidebar widget and configure its splitter behavior.

        Args:
            sidebar (QWidget): The sidebar Widget that contains all SidebarButtons.
        """
        self.sidebar = sidebar
        self.setCollapsible(0, False)
        self.setStretchFactor(0, 0)  # Sidebar doesn't stretch

    def set_listview(self, listview: QListView) -> None:
        """Set the list view widget and configure its splitter behavior.

        Args:
            listview (QListView): The QListView Widget that contains all actions.
        """
        self.listview = listview
        self.setStretchFactor(1, 0)  # Listview doesn't stretch either

    def add_button(self, button) -> None:
        """Add a button to the sidebar and register for event filtering.

        Args:
            button (SidebarButton): The SidebarButton to add.
        """
        self.buttons.append(button)
        # Clear text immediately without animation
        button.setText("")
        button.installEventFilter(self)

    def eventFilter(self, obj, event):
        """Handle hover events for the sidebar and its buttons.

        Args:
            obj (QObject): The object receiving the event.
            event (QEvent): The event being dispatched.

        Returns:
            bool: True if the event was handled, False otherwise.
        """
        if event.type() == QEvent.Type.HoverEnter:
            if obj in self.buttons or obj == self:
                self._handle_hover_enter()
                return False
        elif event.type() in (QEvent.Type.HoverLeave, QEvent.Type.MouseButtonPress):
            if obj in self.buttons or obj == self:
                self._handle_hover_leave()
                return False
        elif obj == self.parent() and event.type() == QEvent.Type.Resize:
            self.collapse_immediate()

        return super().eventFilter(obj, event)

    def _handle_hover_enter(self) -> None:
        """Stop collapse timer and start expand timer."""
        self.collapse_timer.stop()
        if not self._is_expanded:
            self.expand_timer.start()

    def _handle_hover_leave(self) -> None:
        """Stop expand timer/animation and start collapse timer."""
        self.expand_timer.stop()
        self.stop_variant_animation()
        self.collapse_timer.start(config.ui.collapse_hover_delay_ms)

    def expand(self) -> None:
        """Expand the sidebar and hide the list view.

        Animates the splitter to show the full sidebar width and updates
        button states to show text labels.
        """
        if self._is_expanded:
            return

        self.animate_value(
            start_value=self.sizes()[1],
            end_value=0,
            on_value_changed=self._on_resize_animation,
        )

        # Update button states to show text
        for button in self.buttons:
            button.setMaximumWidth(16777215)
            button.set_collapsed(False)

    def collapse(self) -> None:
        """Collapse the sidebar and show the list view.

        Animates the splitter to show only the collapsed sidebar width
        and updates button states to hide text labels.
        """
        target_width = self.width() - self._collapsed_width

        self.animate_value(
            start_value=self.sizes()[1],
            end_value=target_width,
            on_value_changed=self._on_resize_animation,
        )

        self._is_expanded = False

        # Update button states to hide text
        for button in self.buttons:
            button.set_collapsed(True)

    def collapse_immediate(self) -> None:
        """Collapse immediately without animation.

        Used during window resize to avoid fighting with the resize operation.
        Respects minimum widths set on sidebar.
        """
        # Get minimum width of sidebar (first widget)
        sidebar_min_width = config.ui.sidebar_collapsed_width
        if self.sidebar:
            sidebar_min_width = max(sidebar_min_width, self.sidebar.minimumWidth())

        # Set sizes directly without animation
        # Ensure we always give at least sidebar_min_width to the sidebar
        current_width = self.width()
        if current_width > 0:
            list_width = max(0, current_width - sidebar_min_width)
            self.setSizes([sidebar_min_width, list_width])
        else:
            # If not yet shown, use a reasonable default ratio or just the min widths
            self.setSizes([sidebar_min_width, 150])

        self._is_expanded = False

        # Clear button text WITHOUT animation (set_collapsed would animate)
        for button in self.buttons:
            button.setText("")
            # Also ensure button itself doesn't try to be larger than collapsed width
            button.setMinimumWidth(config.ui.sidebar_collapsed_width)
            button.setMaximumWidth(config.ui.sidebar_collapsed_width)

    def _on_resize_animation(self, value: int) -> None:
        """Handle resizing of the splitter during animation.

        Unified handler for both expand and collapse animations.

        Args:
            value (int): Current animation value for splitter sizing.
        """
        self.setSizes([int(self.width() - value), int(value)])
        if value == 0:
            self._is_expanded = True
