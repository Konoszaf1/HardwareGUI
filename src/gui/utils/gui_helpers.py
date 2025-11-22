from __future__ import annotations

import os
from typing import Optional

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QPlainTextEdit


THUMBNAIL_SIZE = QSize(128, 128)


def append_log(console: QPlainTextEdit, text: str) -> None:
    """Append a line to a QPlainTextEdit, parsing ANSI color codes."""
    if not console:
        return
    
    # Basic ANSI to HTML conversion
    # This is a simplified parser for common colors used in the script
    line = text.rstrip("\n")
    
    # Replace ANSI color codes with HTML spans
    # Red
    line = line.replace("\033[31m", '<span style="color: #ff5555;">')
    # Green
    line = line.replace("\033[32m", '<span style="color: #50fa7b;">')
    # Bold / Bright (often used for headers)
    line = line.replace("\033[1m", '<span style="font-weight: bold; color: #ffffff;">')
    # Reset
    line = line.replace("\033[0m", '</span>')
    
    # Handle newlines for HTML
    line = line.replace("\n", "<br>")
    
    console.appendHtml(line)


def add_thumbnail_item(list_widget: QListWidget, path: str, tooltip: Optional[str] = None) -> None:
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
    # Width matches thumbnail, height allows for text
    item.setSizeHint(QSize(THUMBNAIL_SIZE.width() + 10, THUMBNAIL_SIZE.height() + 40))

    list_widget.addItem(item)
