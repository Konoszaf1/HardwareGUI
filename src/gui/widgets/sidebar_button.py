"""Custom Button Type to handle expansion and collapse of the sidebar."""

from pathlib import Path

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtGui import QFontDatabase, QIcon, QPainter
from PySide6.QtWidgets import QSizePolicy, QStyle, QStyleOptionToolButton, QToolButton

from src.config import config
from src.gui.mixins.animation_mixin import AnimatedPropertyMixin
from src.gui.styles import Styles
from src.gui.services.tooltip_service import TooltipService

_goldman_font_loaded = False
_TEXT_LEFT_INSET = 12


def _load_goldman_font() -> None:
    """Load the bundled Goldman font once for sidebar labels."""
    global _goldman_font_loaded  # noqa: PLW0603
    if _goldman_font_loaded:
        return
    font_path = Path(__file__).resolve().parents[2] / "resources" / "fonts" / "Goldman-Regular.ttf"
    if font_path.exists():
        QFontDatabase.addApplicationFont(str(font_path))
    _goldman_font_loaded = True


class SidebarButton(QToolButton, AnimatedPropertyMixin):
    """Sidebar button with animated expand/collapse behavior.

    Uses configuration values for icon size and collapsed width to ensure
    consistency across the application. Tooltip timing is managed by TooltipManager.

    Attributes:
        _original_text (str | None): Original text of the button.
        _compact_text (str | None): Abbreviated text shown when collapsed.
        _tooltip_registered (bool): Whether the button is registered with the tooltip manager.
    """

    def __init__(self, parent=None):
        """Initialize the sidebar button.

        Args:
            parent (QWidget | None): Parent widget.
        """
        super().__init__(parent)
        _load_goldman_font()
        self._original_text: str | None = None
        self._compact_text: str | None = None
        self._tooltip_registered: bool = False
        icon_size = config.ui.sidebar_button_icon_size
        self.setIconSize(QSize(icon_size, icon_size))
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.setCheckable(True)
        self.setChecked(False)
        self.setAutoExclusive(True)
        self.setAutoRaise(False)
        self.setStyleSheet(Styles.SIDEBAR_BUTTON_COLLAPSED)
        self.setSizePolicy(self._create_size_policy())
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        # Ensure button never shrinks below icon size + padding
        self.setMinimumSize(icon_size, icon_size)
        self.setup_property_animation(b"minimumWidth")

    def _create_size_policy(self) -> QSizePolicy:
        """Create custom size policy that enables resizing.

        Returns:
            QSizePolicy: Size policy with fixed horizontal stretch and preferred vertical.
        """
        size_policy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        size_policy.setHorizontalStretch(0)
        size_policy.setVerticalStretch(0)
        if self.parent():
            size_policy.setHeightForWidth(self.parent().hasHeightForWidth())
        return size_policy

    def _ensure_registered(self) -> None:
        """Register with tooltip manager if not already done."""
        if not self._tooltip_registered and self._original_text:
            TooltipService.instance().register_button(self, self._original_text)
            self._tooltip_registered = True

    def enterEvent(self, event: QEvent) -> None:
        """Show tooltip when mouse enters button.

        Args:
            event (QEvent): Enter event.
        """
        self._ensure_registered()
        TooltipService.instance().on_button_enter(self)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        """Hide tooltip when mouse leaves button.

        Args:
            event (QEvent): Leave event.
        """
        TooltipService.instance().on_button_leave(self)
        super().leaveEvent(event)

    def set_collapsed(self, collapsed: bool) -> None:
        """Collapse or expand the button.

        Args:
            collapsed (bool): True to collapse (icon only), False to expand (show text).
        """
        if collapsed:
            super().setText(self._compact_text or "")
            self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            self.setStyleSheet(Styles.SIDEBAR_BUTTON_COLLAPSED)
            self.setMaximumWidth(config.ui.sidebar_collapsed_width)
            self.animate_property(
                start_value=self.width(),
                end_value=config.ui.sidebar_collapsed_width,
                on_finished=self._on_collapse_finished,
            )
        else:
            self.setStyleSheet(Styles.SIDEBAR_BUTTON_EXPANDED)
            self.setMaximumWidth(16777215)  # QWIDGETSIZE_MAX
            self.animate_property(
                start_value=self.width(),
                end_value=config.ui.sidebar_expanded_width,
                on_finished=self._on_expand_finished,
            )

    def _on_collapse_finished(self) -> None:
        """Restore compact text after collapse animation completes."""
        super().setText(self._compact_text or "")

    def _on_expand_finished(self) -> None:
        """Restore text after expand animation completes."""
        if self._original_text:
            super().setText(self._original_text)

    def setText(self, text: str) -> None:
        """Store original text and set button text.

        Args:
            text (str): The text to display on the button.
        """
        if not self._original_text:
            self._original_text = text
        super().setText(text)

    def set_compact_text(self, text: str) -> None:
        """Set the abbreviated label shown while the sidebar is collapsed."""
        self._compact_text = text

    def collapse_immediate_state(self) -> None:
        """Apply collapsed visual state without starting an animation."""
        super().setText(self._compact_text or "")
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.setStyleSheet(Styles.SIDEBAR_BUTTON_COLLAPSED)
        self.setMinimumWidth(config.ui.sidebar_collapsed_width)
        self.setMaximumWidth(config.ui.sidebar_collapsed_width)

    def paintEvent(self, event) -> None:  # noqa: N802
        """Paint button chrome normally, then draw text without Qt eliding."""
        option = QStyleOptionToolButton()
        self.initStyleOption(option)
        text = option.text
        option.text = ""
        option.icon = QIcon()

        painter = QPainter(self)
        self.style().drawComplexControl(QStyle.ComplexControl.CC_ToolButton, option, painter, self)

        text_rect = self.rect().adjusted(_TEXT_LEFT_INSET, 0, 0, 0)
        alignment = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        painter.setFont(self.font())
        painter.setPen(option.palette.buttonText().color())
        painter.setClipRect(self.rect())
        painter.drawText(text_rect, alignment | Qt.TextFlag.TextSingleLine, text)

    @staticmethod
    def create_batch(parent, descriptors) -> list["SidebarButton"]:
        """Create a list of SidebarButtons from descriptors.

        Args:
            parent (QWidget): Parent widget.
            descriptors (Iterable): Sequence of descriptor objects exposing "label",
                "id", "order", and optional "icon_path" attributes.

        Returns:
            list[SidebarButton]: Instantiated buttons.
        """
        buttons = []
        for desc in descriptors:
            btn = SidebarButton(parent)
            btn.setObjectName(desc.label)
            words = [word for word in desc.label.split() if word]
            btn.set_compact_text("".join(word[0] for word in words).upper())
            btn.setText(desc.label)
            btn.setAccessibleName(desc.label)
            btn.setProperty("id", desc.id)
            btn.setProperty("order", desc.order)
            buttons.append(btn)
        return buttons
