"""Application menu bar widget."""

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QAction,
    QKeySequence,
)
from PySide6.QtWidgets import (
    QMenu,
    QMenuBar,
    QSizePolicy,
)

from src.gui.styles import Styles

if TYPE_CHECKING:
    from src.gui.main_window import MainWindow


class AppMenuBar(QMenuBar):
    """Application menu bar widget.

    Attributes:
        toggle_console_action (QAction): Action to toggle console visibility.
        toggle_artifacts_action (QAction): Action to toggle artifacts visibility.
    """

    def __init__(self, parent: "MainWindow") -> None:
        """Initialize the menu bar.

        Args:
            parent (MainWindow): The parent main window.
        """
        super().__init__(parent)
        self.setStyleSheet(Styles.MENU_BAR)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)

        self._setup_file_menu(parent)
        self.addMenu(QMenu("Edit", self))
        self._setup_view_menu(parent)
        self.addMenu(QMenu("Help", self))

    def _setup_file_menu(self, parent: "MainWindow") -> None:
        """Setup the file menu.

        Args:
            parent (MainWindow): The parent main window.
        """
        file_menu = QMenu("File", self)

        settings_action = QAction("Settings...", self)
        settings_action.triggered.connect(parent._on_settings)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(parent.close)
        file_menu.addAction(exit_action)

        self.addMenu(file_menu)

    def _setup_view_menu(self, parent: "MainWindow") -> None:
        """Setup the view menu.

        Args:
            parent (MainWindow): The parent main window.
        """
        view_menu = QMenu("View", self)

        self.toggle_console_action = QAction("Toggle Terminal", self)
        self.toggle_console_action.setShortcut(QKeySequence("Ctrl+`"))
        self.toggle_console_action.setCheckable(True)
        self.toggle_console_action.setChecked(False)
        self.toggle_console_action.triggered.connect(parent._on_toggle_console)
        view_menu.addAction(self.toggle_console_action)

        self.toggle_artifacts_action = QAction("Toggle Artifacts", self)
        self.toggle_artifacts_action.setShortcut(QKeySequence("Ctrl+1"))
        self.toggle_artifacts_action.setCheckable(True)
        self.toggle_artifacts_action.setChecked(False)
        self.toggle_artifacts_action.triggered.connect(parent._on_toggle_artifacts)
        view_menu.addAction(self.toggle_artifacts_action)

        self.addMenu(view_menu)
