"""Tooltip service for sidebar buttons.

The tooltip service handles all timing logic for showing tooltips.
Individual buttons just report hover events to the service.
"""

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtWidgets import QLabel, QWidget

from src.config import config
from src.gui.styles import Styles
from src.logging_config import get_logger

logger = get_logger(__name__)


class TooltipService:
    """Singleton service that handles tooltip timing and display for sidebar buttons.

    Centralizes logic for:
    - Initial show delay (configured via config.tooltip.show_delay_ms)
    - "Grace period" for instant switching between adjacent buttons
    - Tooltip lifecycle management (creation, showing, hiding, destruction)

    Attributes:
        _instance (TooltipService | None): Singleton instance.
    """

    _instance: "TooltipService | None" = None

    def __init__(self) -> None:
        """Initialize the tooltip service."""
        self._tooltips: dict[QWidget, str] = {}  # button -> tooltip text
        self._current_button: QWidget | None = None
        self._is_warm: bool = False
        self.currently_shown_tooltip: QLabel | None = None

        # Timer for delayed show
        self._show_timer = QTimer()
        self._show_timer.setSingleShot(True)
        self._show_timer.timeout.connect(self._on_show_timer)

        # Timer for grace period
        self._grace_timer = QTimer()
        self._grace_timer.setSingleShot(True)
        self._grace_timer.timeout.connect(self._on_grace_expired)

    def is_warm(self) -> bool:
        """Return True if the tooltip service is in the warm state.

        Returns:
            bool: True if warm, False otherwise.
        """
        return self._is_warm

    @classmethod
    def instance(cls) -> "TooltipService":
        """Get or create the singleton service instance.

        Returns:
            TooltipService: The singleton instance.
        """
        if cls._instance is None:
            cls._instance = TooltipService()
        return cls._instance

    @classmethod
    def init(cls) -> "TooltipService":
        """Initialize the singleton (alias for instance())."""
        return cls.instance()

    def register_button(self, button: QWidget, text: str) -> None:
        """Register a button with its tooltip text (stores text only, not tooltip).

        Args:
            button (QWidget): Button to register.
            text (str): Tooltip text.
        """
        if button not in self._tooltips:
            self._tooltips[button] = text
            logger.debug("Registered tooltip for button '%s'", text)

    def _create_tooltip(self, text: str, parent: QWidget | None = None) -> QLabel:
        """Create a styled tooltip label for a button.

        Args:
            text (str): The text to display in the tooltip.
            parent (QWidget | None): Optional parent widget (usually the button).

        Returns:
            QLabel: A QLabel configured as a tooltip window.
        """
        tooltip = QLabel()
        tooltip.setWindowFlags(
            Qt.WindowType.ToolTip
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        tooltip.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        tooltip.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        tooltip.setStyleSheet(Styles.SIDEBAR_TOOLTIP)
        tooltip.setText(text)
        tooltip.adjustSize()
        return tooltip

    def on_button_enter(self, button: QWidget) -> None:
        """Called when mouse enters a button.

        Args:
            button (QWidget): The button that was entered.
        """
        self._grace_timer.stop()
        self._show_timer.stop()
        if self._current_button is not None and self._current_button != button:
            self._hide_current()

        self._current_button = button

        if self._is_warm:
            logger.debug("Warm state - showing tooltip immediately")
            self._show_tooltip(button)
        else:
            delay = config.tooltip.show_delay_ms
            logger.debug("Cold state - starting %dms delay", delay)
            self._show_timer.start(delay)

    def on_button_leave(self, button: QWidget) -> None:
        """Called when mouse leaves a button.

        Args:
            button (QWidget): The button that was left.
        """
        # Stop show timer if it was pending
        self._show_timer.stop()
        self._grace_timer.stop()

        # Only process if this is the current button
        if self._current_button == button:
            was_visible = self.currently_shown_tooltip is not None

            self._hide_current()

            if was_visible:
                self._is_warm = True
                grace = config.tooltip.grace_period_ms
                logger.debug("Starting %dms grace period", grace)
                self._grace_timer.start(grace)
            else:
                logger.debug("Tooltip wasn't visible - staying cold")
                self._current_button = None

    def _show_tooltip(self, button: QWidget) -> None:
        """Show the tooltip for a button (creates fresh tooltip each time).

        Args:
            button (QWidget): The button to show tooltip for.
        """
        text = self._tooltips.get(button)
        if text is None or not button.isVisible():
            return
        self._hide_current()
        tooltip = self._create_tooltip(text)
        button_rect = button.rect()
        top_right = button.mapToGlobal(QPoint(button_rect.width(), 0))

        x = top_right.x()
        y = top_right.y() + (button_rect.height() - tooltip.height()) // 2

        logger.debug("Showing tooltip '%s' at (%d, %d)", text, x, y)
        tooltip.move(x, y)
        tooltip.show()
        tooltip.raise_()
        self.currently_shown_tooltip = tooltip

    def _hide_current(self) -> None:
        """Hide and destroy the current tooltip."""
        if self.currently_shown_tooltip is not None:
            self.currently_shown_tooltip.hide()
            self.currently_shown_tooltip.deleteLater()
            self.currently_shown_tooltip = None

    def _on_show_timer(self) -> None:
        """Show timer expired - display tooltip."""
        if self._current_button is not None:
            self._show_tooltip(self._current_button)
            self._is_warm = True

    def _on_grace_expired(self) -> None:
        """Grace period expired - go cold."""
        logger.debug("Grace period expired - going cold")
        self._is_warm = False
        self._current_button = None
