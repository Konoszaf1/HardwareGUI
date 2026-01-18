from __future__ import annotations

import os

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QPlainTextEdit

from src.config import config

THUMBNAIL_SIZE = QSize(config.thumbnails.icon_size, config.thumbnails.icon_size)

# ANSI escape code to HTML span mapping
# Maps common terminal color codes to styled HTML spans
_ANSI_TO_HTML = {
    "\033[31m": '<span style="color: #ff5555;">',  # Red
    "\033[32m": '<span style="color: #50fa7b;">',  # Green
    "\033[33m": '<span style="color: #f1fa8c;">',  # Yellow
    "\033[34m": '<span style="color: #8be9fd;">',  # Blue
    "\033[35m": '<span style="color: #ff79c6;">',  # Magenta
    "\033[36m": '<span style="color: #8be9fd;">',  # Cyan
    "\033[1m": '<span style="font-weight: bold; color: #ffffff;">',  # Bold
    "\033[0m": "</span>",  # Reset
}


def _convert_ansi_to_html(text: str) -> str:
    """Convert ANSI escape codes to HTML spans.

    Args:
        text: Text potentially containing ANSI escape codes.

    Returns:
        Text with ANSI codes replaced by HTML spans.
    """
    for ansi_code, html_span in _ANSI_TO_HTML.items():
        text = text.replace(ansi_code, html_span)
    return text


def append_log(console: QPlainTextEdit, text: str) -> None:
    """Append a line to a QPlainTextEdit, parsing ANSI color codes."""
    if not console:
        return

    line = text.rstrip("\n")
    line = _convert_ansi_to_html(line)
    line = line.replace("\n", "<br>")
    console.appendHtml(line)


def add_thumbnail_item(list_widget: QListWidget, path: str, tooltip: str | None = None) -> None:
    """Add or update a thumbnail item for an image file to the given QListWidget.

    - Uses IconMode settings already configured by the page.
    - If the item for this path already exists, it is updated.
    """
    if not list_widget or not path:
        return

    if not os.path.exists(path):
        return

    # Try to load pixmap and scale preserving aspect ratio
    pixmap = QPixmap(path)
    if not pixmap.isNull():
        # If the image is very large, generate a scaled thumbnail
        thumb = pixmap.scaled(THUMBNAIL_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon = QIcon(thumb)
    else:
        icon = QIcon()

    # Check if an item for this path already exists (by data role)
    for i in range(list_widget.count()):
        item = list_widget.item(i)
        if item and item.data(Qt.UserRole) == path:
            item.setIcon(icon)
            item.setText(os.path.basename(path))
            if tooltip is not None:
                item.setToolTip(tooltip)
            return

    # Create new item
    item = QListWidgetItem(icon, os.path.basename(path))
    item.setData(Qt.UserRole, path)
    if tooltip:
        item.setToolTip(tooltip)

    # Provide a reasonable size hint so items have visual space
    # Width matches thumbnail, height allows for compact text
    item.setSizeHint(QSize(THUMBNAIL_SIZE.width() + 10, THUMBNAIL_SIZE.height() + 20))

    list_widget.addItem(item)
