"""Custom QSplitter Widget to handle the sidebar expansion and collapse."""

from PySide6.QtCore import QEvent, QTimer
from PySide6.QtWidgets import QListView, QSplitter, QWidget

from src.config import config
from src.gui.animation_mixin import AnimatedWidgetMixin


class ExpandingSplitter(QSplitter, AnimatedWidgetMixin):
    """An expanding sidebar that shows button text over the side list on hover.

    Uses configuration values for timing and dimensions to ensure consistency
    across the application. Animation logic is provided by AnimatedWidgetMixin.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._collapsed_width = config.ui.sidebar_collapsed_width
        self._expanded_width = config.ui.sidebar_expanded_width
        self.setMinimumWidth(self._collapsed_width)
        self.buttons: list = []
        self._is_expanded = False
        self.widget: QWidget | None = None
        self.listview: QListView | None = None
        self.sidebar: QWidget | None = None
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
        """Set the sidebar widget.

        Args:
            sidebar: The sidebar Widget that contains all SidebarButtons.
        """
        self.sidebar = sidebar
        self.setCollapsible(0, False)

    def set_listview(self, listview: QListView) -> None:
        """Set the list view widget.

        Args:
            listview: The QListView Widget that contains all actions.
        """
        self.listview = listview

    def add_button(self, button) -> None:
        """Add a button to the sidebar and register for event filtering.

        Args:
            button: The SidebarButton to add.
        """
        self.buttons.append(button)
        button.set_collapsed(True)
        button.installEventFilter(self)

    def eventFilter(self, obj, event):
        """Handle hover events for the sidebar and its buttons."""
        if event.type() == QEvent.Type.HoverEnter:
            if obj in self.buttons or obj == self:
                self._handle_hover_enter()
                return False
        elif event.type() in (QEvent.Type.HoverLeave, QEvent.Type.MouseButtonPress):
            if obj in self.buttons or obj == self:
                self._handle_hover_leave()
                return False
        elif obj == self.parent() and event.type() == QEvent.Type.Resize:
            self.collapse()

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

    def _on_resize_animation(self, value: int) -> None:
        """Handle resizing of the splitter during animation.

        Unified handler for both expand and collapse animations.

        Args:
            value: Current animation value for splitter sizing.
        """
        self.setSizes([int(self.width() - value), int(value)])
        if value == 0:
            self._is_expanded = True
