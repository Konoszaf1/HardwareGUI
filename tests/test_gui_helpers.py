"""Tests for src/gui/utils/gui_helpers.py ANSI conversion and logging utilities."""

from unittest.mock import Mock
from PySide6.QtWidgets import QPlainTextEdit, QListWidget
from PySide6.QtCore import Qt

from src.gui.utils.gui_helpers import (
    _convert_ansi_to_html,
    append_log,
    add_thumbnail_item,
)


class TestConvertAnsiToHtml:
    """Test ANSI escape code to HTML conversion."""

    def test_convert_red(self):
        """Red ANSI code should convert to red HTML span."""
        result = _convert_ansi_to_html("\033[31mError\033[0m")

        assert '<span style="color: #ff5555;">' in result
        assert "Error" in result
        assert "</span>" in result

    def test_convert_green(self):
        """Green ANSI code should convert to green HTML span."""
        result = _convert_ansi_to_html("\033[32mSuccess\033[0m")

        assert '<span style="color: #50fa7b;">' in result

    def test_convert_bold(self):
        """Bold ANSI code should convert to bold HTML span."""
        result = _convert_ansi_to_html("\033[1mHeader\033[0m")

        assert "font-weight: bold" in result

    def test_no_ansi_codes_unchanged(self):
        """Text without ANSI codes should pass through unchanged."""
        text = "Plain text without colors"
        result = _convert_ansi_to_html(text)

        assert result == text

    def test_chained_codes(self):
        """Multiple ANSI codes in one string should all be converted."""
        result = _convert_ansi_to_html("\033[31mRed\033[0m and \033[32mGreen\033[0m")

        assert "#ff5555" in result
        assert "#50fa7b" in result
        assert result.count("</span>") >= 2


class TestAppendLog:
    """Test append_log() function - the main public API."""

    def test_append_log_calls_appendHtml(self, qtbot):
        """append_log should call appendHtml on the console widget."""
        console = QPlainTextEdit()
        qtbot.addWidget(console)

        append_log(console, "Test message")

        html = console.toPlainText()
        assert "Test message" in html

    def test_append_log_converts_ansi(self, qtbot):
        """append_log should convert ANSI codes to HTML spans."""
        console = Mock()
        console.appendHtml = Mock()

        append_log(console, "\033[31mRed text\033[0m")

        call_args = console.appendHtml.call_args[0][0]
        assert '<span style="color: #ff5555;">' in call_args
        assert "Red text" in call_args
        assert "</span>" in call_args

    def test_append_log_strips_trailing_newline(self, qtbot):
        """append_log should strip trailing newlines."""
        console = QPlainTextEdit()
        qtbot.addWidget(console)

        append_log(console, "Message\n")

        text = console.toPlainText()
        assert not text.endswith("\n\n")

    def test_append_log_converts_internal_newlines_to_br(self):
        """append_log should convert internal newlines to <br>."""
        console = Mock()
        console.appendHtml = Mock()

        append_log(console, "Line1\nLine2")

        call_args = console.appendHtml.call_args[0][0]
        assert "<br>" in call_args

    def test_append_log_none_console_safe(self):
        """append_log should handle None console gracefully."""
        append_log(None, "Test message")  # Should not raise


class TestAddThumbnailItem:
    """Test add_thumbnail_item() function."""

    def test_add_item_to_list(self, qtbot, tmp_path):
        """add_thumbnail_item should add an item to the list widget."""
        list_widget = QListWidget()
        qtbot.addWidget(list_widget)

        img_path = tmp_path / "test.png"
        img_path.write_bytes(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
            b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
            b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )

        add_thumbnail_item(list_widget, str(img_path))

        assert list_widget.count() == 1

    def test_item_stores_path_in_user_role(self, qtbot, tmp_path):
        """add_thumbnail_item should store full path in UserRole."""
        list_widget = QListWidget()
        qtbot.addWidget(list_widget)

        img_path = tmp_path / "test.png"
        img_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

        add_thumbnail_item(list_widget, str(img_path))

        item = list_widget.item(0)
        assert item.data(Qt.UserRole) == str(img_path)

    def test_item_displays_basename(self, qtbot, tmp_path):
        """add_thumbnail_item should display only the filename, not full path."""
        list_widget = QListWidget()
        qtbot.addWidget(list_widget)

        img_path = tmp_path / "my_image.png"
        img_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

        add_thumbnail_item(list_widget, str(img_path))

        item = list_widget.item(0)
        assert item.text() == "my_image.png"

    def test_updates_existing_item(self, qtbot, tmp_path):
        """add_thumbnail_item should update existing item with same path."""
        list_widget = QListWidget()
        qtbot.addWidget(list_widget)

        img_path = tmp_path / "test.png"
        img_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

        add_thumbnail_item(list_widget, str(img_path))
        add_thumbnail_item(list_widget, str(img_path), tooltip="Updated")

        assert list_widget.count() == 1
        assert list_widget.item(0).toolTip() == "Updated"

    def test_none_list_widget_safe(self, tmp_path):
        """add_thumbnail_item should handle None list_widget gracefully."""
        img_path = tmp_path / "test.png"
        img_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

        add_thumbnail_item(None, str(img_path))  # Should not raise

    def test_nonexistent_path_safe(self, qtbot):
        """add_thumbnail_item should handle non-existent path gracefully."""
        list_widget = QListWidget()
        qtbot.addWidget(list_widget)

        add_thumbnail_item(list_widget, "/nonexistent/path.png")

        assert list_widget.count() == 0

    def test_empty_path_safe(self, qtbot):
        """add_thumbnail_item should handle empty path gracefully."""
        list_widget = QListWidget()
        qtbot.addWidget(list_widget)

        add_thumbnail_item(list_widget, "")

        assert list_widget.count() == 0
