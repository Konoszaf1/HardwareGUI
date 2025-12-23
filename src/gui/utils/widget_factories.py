"""Factory functions for commonly used widget configurations.

This module provides factory functions that create pre-configured widgets
with consistent styling and behavior, reducing code duplication across pages.
"""

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QPlainTextEdit,
    QListWidget,
    QListView,
    QLineEdit,
    QFrame,
    QVBoxLayout,
    QLabel,
    QPushButton,
)

from src.gui.styles import Styles


def create_console_widget(max_block_count: int = 20000) -> QPlainTextEdit:
    """Create a read-only console widget with Dracula theme styling.

    Args:
        max_block_count: Maximum number of lines to retain in the console.

    Returns:
        Configured QPlainTextEdit widget.
    """
    console = QPlainTextEdit()
    console.setObjectName("console")
    console.setReadOnly(True)
    console.setUndoRedoEnabled(False)
    console.setTextInteractionFlags(
        Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
    )
    console.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
    console.setMaximumBlockCount(max_block_count)
    console.setStyleSheet(Styles.CONSOLE)
    return console


def create_artifact_list_widget(
    icon_size: QSize = QSize(128, 128),
    grid_size: QSize = QSize(140, 160),
    spacing: int = 10,
) -> QListWidget:
    """Create a horizontal icon-mode list for artifact thumbnails.

    Args:
        icon_size: Size of thumbnail icons.
        grid_size: Size of grid cells.
        spacing: Spacing between items.

    Returns:
        Configured QListWidget widget.
    """
    list_widget = QListWidget()
    list_widget.setObjectName("artifacts")
    list_widget.setMovement(QListView.Movement.Static)
    list_widget.setProperty("isWrapping", False)
    list_widget.setResizeMode(QListView.ResizeMode.Adjust)
    list_widget.setViewMode(QListView.ViewMode.IconMode)
    list_widget.setFlow(QListView.Flow.LeftToRight)
    list_widget.setIconSize(icon_size)
    list_widget.setGridSize(grid_size)
    list_widget.setSpacing(spacing)
    return list_widget


def create_input_field(
    placeholder: str = "Type input here and press Enter...",
) -> QLineEdit:
    """Create a hidden-by-default input field.

    Args:
        placeholder: Placeholder text when empty.

    Returns:
        Configured QLineEdit widget (hidden by default).
    """
    le_input = QLineEdit()
    le_input.setPlaceholderText(placeholder)
    le_input.setVisible(False)
    return le_input


def create_test_card(
    title: str,
    info_lines: list[str],
    button: QPushButton,
) -> QFrame:
    """Create a styled card for test actions.

    Args:
        title: Card title text.
        info_lines: List of info lines to display.
        button: Action button to include.

    Returns:
        Configured QFrame widget.
    """
    card = QFrame()
    card.setFrameShape(QFrame.Shape.StyledPanel)
    card.setFrameShadow(QFrame.Shadow.Raised)
    card.setStyleSheet(Styles.TEST_CARD)

    layout = QVBoxLayout(card)
    layout.setSpacing(5)
    layout.setContentsMargins(10, 10, 10, 10)

    lbl_title = QLabel(title)
    lbl_title.setStyleSheet(Styles.CARD_TITLE)
    layout.addWidget(lbl_title)

    for line in info_lines:
        lbl = QLabel(line)
        lbl.setStyleSheet(Styles.CARD_INFO)
        layout.addWidget(lbl)

    layout.addStretch()
    layout.addWidget(button)

    return card
