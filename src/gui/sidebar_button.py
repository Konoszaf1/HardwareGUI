"""Custom Button Type to handle expansion and collapse of the sidebar."""

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtWidgets import QSizePolicy, QToolButton

from src.config import config
from src.gui.animation_mixin import AnimatedPropertyMixin
from src.gui.sidebar_tooltip import TooltipManager


class SidebarButton(QToolButton, AnimatedPropertyMixin):
    """Sidebar button with animated expand/collapse behavior.

    Uses configuration values for icon size and collapsed width to ensure
    consistency across the application. Tooltip timing is managed by TooltipManager.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._original_text: str | None = None
        self._tooltip_registered: bool = False

        # Use config for icon size instead of hardcoded value
        icon_size = config.ui.sidebar_button_icon_size
        self.setIconSize(QSize(icon_size, icon_size))

        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.setCheckable(True)
        self.setChecked(False)
        self.setAutoExclusive(True)
        self.setAutoRaise(False)
        self.setSizePolicy(self._create_size_policy())
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Setup animation using mixin
        self.setup_property_animation(b"minimumWidth")

    def _create_size_policy(self) -> QSizePolicy:
        """Create custom size policy that enables resizing."""
        size_policy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        size_policy.setHorizontalStretch(0)
        size_policy.setVerticalStretch(0)
        if self.parent():
            size_policy.setHeightForWidth(self.parent().hasHeightForWidth())
        return size_policy

    def _ensure_registered(self) -> None:
        """Register with tooltip manager if not already done."""
        if not self._tooltip_registered and self._original_text:
            TooltipManager.instance().register_button(self, self._original_text)
            self._tooltip_registered = True

    def enterEvent(self, event: QEvent) -> None:
        """Show tooltip when mouse enters button."""
        self._ensure_registered()
        TooltipManager.instance().on_button_enter(self)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        """Hide tooltip when mouse leaves button."""
        TooltipManager.instance().on_button_leave(self)
        super().leaveEvent(event)

    def set_collapsed(self, collapsed: bool) -> None:
        """Animate button between collapsed and expanded states.

        Args:
            collapsed: True to collapse (icon only), False to expand (show text).
        """
        if collapsed:
            super().setText("")
            self.animate_property(
                start_value=self.width(),
                end_value=config.ui.sidebar_collapsed_width,
                on_finished=self._on_collapse_finished,
            )
        else:
            self.animate_property(
                start_value=self.width(),
                end_value=config.ui.sidebar_expanded_width,
                on_finished=self._on_expand_finished,
            )

    def _on_collapse_finished(self) -> None:
        """Clear text after collapse animation completes."""
        super().setText("")

    def _on_expand_finished(self) -> None:
        """Restore text after expand animation completes."""
        if self._original_text:
            super().setText(f" {self._original_text}")

    def setText(self, text: str) -> None:
        """Store original text and set button text.

        Args:
            text: The text to display on the button.
        """
        if not self._original_text:
            self._original_text = text
        super().setText(text)
