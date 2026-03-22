from __future__ import annotations

import os
import re

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QPlainTextEdit

from src.config import config

THUMBNAIL_SIZE = QSize(config.thumbnails.icon_size, config.thumbnails.icon_size)

# Regex to strip any ANSI escape sequence (colors, cursor, etc.)
_ANSI_RE = re.compile(r"\033\[[0-9;]*[A-Za-z]")

# Box-drawing characters used by rich tables
_BOX_CHARS = frozenset("│─┼┤├┬┴┐┘┌└╴╵╶╷")

# Regex to strip DPI library log prefixes like:
#   "2026-03-20 14:38:41 - DPI(dpiio.py:128): INFO - "
_DPI_LOG_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s+-\s+\S+:\s+\w+\s+-\s+")

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

_STDERR_PREFIX = "[stderr] "

_FLUSH_INTERVAL_MS = 50  # Batch log lines and flush every 50ms


class LogBatcher:
    """Accumulates HTML log lines and flushes them to a QPlainTextEdit on a timer.

    This prevents per-line appendHtml() calls which cause expensive reflows.
    """

    _instances: dict[int, LogBatcher] = {}

    def __init__(self, console: QPlainTextEdit) -> None:
        self._console = console
        self._buffer: list[str] = []
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.setInterval(_FLUSH_INTERVAL_MS)
        self._timer.timeout.connect(self._flush)

    @classmethod
    def for_console(cls, console: QPlainTextEdit) -> LogBatcher:
        """Get or create a LogBatcher for a given console widget."""
        wid = id(console)
        batcher = cls._instances.get(wid)
        if batcher is None or batcher._console is not console:
            batcher = cls(console)
            cls._instances[wid] = batcher
        return batcher

    def append(self, html_line: str) -> None:
        """Queue a line and schedule a flush."""
        self._buffer.append(html_line)
        if not self._timer.isActive():
            self._timer.start()

    def _flush(self) -> None:
        """Flush all buffered lines to the console in one batch."""
        if not self._buffer or not self._console:
            return
        combined = "<br>".join(self._buffer)
        self._buffer.clear()
        self._console.appendHtml(combined)


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
    """Append a line to a QPlainTextEdit, parsing ANSI color codes.

    Lines containing box-drawing characters (from rich tables) get
    whitespace preserved via ``&nbsp;`` so column alignment is maintained.
    Stderr lines (from library logging) are shown in muted style with
    the ``[stderr]`` prefix and DPI log preamble stripped.
    """
    if not console:
        return

    line = text.rstrip("\n")

    # Detect and strip [stderr] prefix - style as muted text
    is_stderr = line.startswith(_STDERR_PREFIX)
    if is_stderr:
        line = line[len(_STDERR_PREFIX) :]
        if not line.strip():
            return  # skip blank stderr lines
        # Strip verbose DPI library log prefix (timestamp + source)
        line = _DPI_LOG_PREFIX_RE.sub("", line)

    # Detect table-formatted lines (box-drawing chars from rich)
    is_table = any(c in _BOX_CHARS for c in line)

    if is_table:
        # Strip ALL ANSI codes, escape HTML entities, preserve spaces
        line = _ANSI_RE.sub("", line)
        line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        line = line.replace(" ", "&nbsp;")
    else:
        line = _convert_ansi_to_html(line)
        # Strip any remaining ANSI codes not in our mapping
        line = _ANSI_RE.sub("", line)
        line = line.replace("\n", "<br>")

    if is_stderr:
        line = f'<span style="color: #6272a4;">{line}</span>'

    LogBatcher.for_console(console).append(line)


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
