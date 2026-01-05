"""Custom Sidebar widget with preconfigured layout."""

from PySide6.QtWidgets import QWidget

from src.config import config


class Sidebar(QWidget):
    """A sidebar widget with preconfigured minimum width for hardware buttons.

    This widget sets up the standard sidebar configuration. The layout
    (including the vertical spacer) is defined in the UI file.

    Attributes:
        None
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the sidebar with standard configuration.

        Args:
            parent (QWidget | None): Parent widget.
        """
        super().__init__(parent)
        self.setMinimumWidth(config.ui.sidebar_collapsed_width)
