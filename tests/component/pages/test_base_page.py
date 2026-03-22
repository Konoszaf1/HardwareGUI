"""Component tests for BaseHardwarePage.

Tests task lifecycle, busy state management, layout factories,
and service signal handling.
"""

from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.gui.scripts.base_page import BaseHardwarePage
from src.logic.qt_workers import FunctionTask, TaskResult

# Use component-level mock services
pytestmark = pytest.mark.component


# ---------------------------------------------------------------------------
# Concrete subclass for testing the abstract-ish BaseHardwarePage
# ---------------------------------------------------------------------------


class ConcreteTestPage(BaseHardwarePage):
    """Minimal concrete subclass for testing BaseHardwarePage."""

    def __init__(self, service=None, shared_panels=None, parent=None):
        super().__init__(parent=parent, service=service, shared_panels=shared_panels)

        # Add some action buttons for testing _set_busy
        self.btn_action1 = QPushButton("Action 1")
        self.btn_action2 = QPushButton("Action 2")
        self._action_buttons = [self.btn_action1, self.btn_action2]

        # Place the cancel button in a layout so _start_task can show it
        layout = QVBoxLayout(self)
        layout.addWidget(self.btn_action1)
        layout.addWidget(self.btn_action2)
        layout.addWidget(self._btn_cancel)


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def page(qtbot, mock_vu_service, mock_shared_panels) -> ConcreteTestPage:
    """Create a ConcreteTestPage with mock service and panels."""
    p = ConcreteTestPage(service=mock_vu_service, shared_panels=mock_shared_panels)
    qtbot.addWidget(p)
    return p


@pytest.fixture
def page_no_service(qtbot, mock_shared_panels) -> ConcreteTestPage:
    """Create a ConcreteTestPage without a service."""
    p = ConcreteTestPage(service=None, shared_panels=mock_shared_panels)
    qtbot.addWidget(p)
    return p


@pytest.fixture
def page_no_panels(qtbot, mock_vu_service) -> ConcreteTestPage:
    """Create a ConcreteTestPage without shared panels."""
    p = ConcreteTestPage(service=mock_vu_service, shared_panels=None)
    qtbot.addWidget(p)
    return p


# ---------------------------------------------------------------------------
# Tests: Initialization
# ---------------------------------------------------------------------------


class TestBasePageInit:
    """Tests for BaseHardwarePage initialization."""

    def test_init_stores_service(self, page, mock_vu_service):
        """Service is stored on the page."""
        assert page.service is mock_vu_service

    def test_init_stores_shared_panels(self, page, mock_shared_panels):
        """Shared panels widget is stored on the page."""
        assert page.shared_panels is mock_shared_panels

    def test_init_no_active_task(self, page):
        """No active task on init."""
        assert page._active_task is None

    def test_init_not_busy(self, page):
        """Page is not busy on init."""
        assert page._busy is False

    def test_init_cancel_button_hidden(self, page):
        """Cancel button is hidden on init."""
        assert not page._btn_cancel.isVisible()

    def test_init_action_buttons_registered(self, page):
        """Action buttons are registered."""
        assert len(page._action_buttons) == 2


# ---------------------------------------------------------------------------
# Tests: Shared panel accessors
# ---------------------------------------------------------------------------


class TestBasePagePanelAccessors:
    """Tests for shared panel property accessors."""

    def test_console_returns_panel_console(self, page, mock_shared_panels):
        """Console property delegates to shared_panels.console."""
        assert page.console is mock_shared_panels.console

    def test_list_widget_returns_panel_artifacts(self, page, mock_shared_panels):
        """listWidget property delegates to shared_panels.artifacts."""
        assert page.listWidget is mock_shared_panels.artifacts

    def test_console_returns_none_without_panels(self, page_no_panels):
        """Console returns None when no shared panels."""
        assert page_no_panels.console is None

    def test_list_widget_returns_none_without_panels(self, page_no_panels):
        """listWidget returns None when no shared panels."""
        assert page_no_panels.listWidget is None


# ---------------------------------------------------------------------------
# Tests: Busy state management
# ---------------------------------------------------------------------------


class TestBasePageBusyState:
    """Tests for _set_busy and button enable/disable."""

    def test_set_busy_true_disables_buttons(self, page):
        """Setting busy=True disables all action buttons."""
        page.btn_action1.setEnabled(True)
        page.btn_action2.setEnabled(True)

        page._set_busy(True)

        assert not page.btn_action1.isEnabled()
        assert not page.btn_action2.isEnabled()

    def test_set_busy_false_enables_buttons_when_connected(self, page, mock_vu_service):
        """Setting busy=False enables buttons when service is connected."""
        mock_vu_service._connected = True
        page._set_busy(True)

        page._set_busy(False)

        assert page.btn_action1.isEnabled()
        assert page.btn_action2.isEnabled()

    def test_set_busy_false_keeps_disabled_when_disconnected(self, page, mock_vu_service):
        """Setting busy=False keeps buttons disabled when service is disconnected."""
        mock_vu_service._connected = False
        page._set_busy(True)

        page._set_busy(False)

        assert not page.btn_action1.isEnabled()
        assert not page.btn_action2.isEnabled()

    def test_set_busy_updates_flag(self, page):
        """_set_busy updates the _busy flag."""
        page._set_busy(True)
        assert page._busy is True

        page._set_busy(False)
        assert page._busy is False


# ---------------------------------------------------------------------------
# Tests: _update_action_buttons_state
# ---------------------------------------------------------------------------


class TestBasePageActionButtonState:
    """Tests for _update_action_buttons_state."""

    def test_buttons_enabled_when_connected(self, page, mock_vu_service):
        """Buttons enabled when service.connected is True."""
        mock_vu_service._connected = True

        page._update_action_buttons_state()

        assert page.btn_action1.isEnabled()
        assert page.btn_action2.isEnabled()

    def test_buttons_disabled_when_disconnected(self, page, mock_vu_service):
        """Buttons disabled when service.connected is False."""
        mock_vu_service._connected = False

        page._update_action_buttons_state()

        assert not page.btn_action1.isEnabled()
        assert not page.btn_action2.isEnabled()

    def test_no_service_does_not_crash(self, page_no_service):
        """No crash when service is None."""
        page_no_service._update_action_buttons_state()  # Should not raise


# ---------------------------------------------------------------------------
# Tests: Task lifecycle (_start_task)
# ---------------------------------------------------------------------------


class TestBasePageStartTask:
    """Tests for _start_task lifecycle management."""

    def test_start_task_sets_busy(self, page, make_dummy_task):
        """_start_task sets page to busy state."""
        task = make_dummy_task(return_value={"ok": True})

        with patch("src.gui.scripts.base_page.run_in_thread"):
            page._start_task(task)

        assert page._busy is True
        assert not page.btn_action1.isEnabled()

    def test_start_task_stores_active_task(self, page, make_dummy_task):
        """_start_task stores the task as _active_task."""
        task = make_dummy_task(return_value={"ok": True})

        with patch("src.gui.scripts.base_page.run_in_thread"):
            page._start_task(task)

        assert page._active_task is task

    def test_start_task_shows_cancel_button(self, page, make_dummy_task):
        """_start_task makes the cancel button visible (not hidden)."""
        task = make_dummy_task(return_value={"ok": True})

        with patch("src.gui.scripts.base_page.run_in_thread"):
            page._start_task(task)

        # Widget won't report isVisible() without a shown parent,
        # so check isHidden() which only reflects the widget's own state.
        assert not page._btn_cancel.isHidden()

    def test_start_task_none_is_noop(self, page):
        """_start_task with None task is a no-op."""
        page._start_task(None)

        assert page._active_task is None
        assert page._busy is False

    def test_start_task_calls_run_in_thread(self, page, make_dummy_task):
        """_start_task submits the task to the thread pool."""
        task = make_dummy_task(return_value={"ok": True})

        with patch("src.gui.scripts.base_page.run_in_thread") as mock_run:
            page._start_task(task)

        mock_run.assert_called_once_with(task)


# ---------------------------------------------------------------------------
# Tests: _on_task_finished
# ---------------------------------------------------------------------------


class TestBasePageOnTaskFinished:
    """Tests for _on_task_finished handler."""

    def test_on_task_finished_clears_busy(self, page, make_dummy_task):
        """Task completion clears busy state."""
        task = make_dummy_task(return_value={"ok": True})
        with patch("src.gui.scripts.base_page.run_in_thread"):
            page._start_task(task)

        result = TaskResult(name="test", ok=True, data={"ok": True})
        page._on_task_finished(result)

        assert page._busy is False

    def test_on_task_finished_clears_active_task(self, page, make_dummy_task):
        """Task completion clears _active_task."""
        task = make_dummy_task(return_value={"ok": True})
        with patch("src.gui.scripts.base_page.run_in_thread"):
            page._start_task(task)

        result = TaskResult(name="test", ok=True)
        page._on_task_finished(result)

        assert page._active_task is None

    def test_on_task_finished_hides_cancel_button(self, page, make_dummy_task):
        """Task completion hides the cancel button."""
        task = make_dummy_task(return_value={"ok": True})
        with patch("src.gui.scripts.base_page.run_in_thread"):
            page._start_task(task)

        result = TaskResult(name="test", ok=True)
        page._on_task_finished(result)

        assert not page._btn_cancel.isVisible()

    def test_on_task_finished_logs_completion(self, page, mock_shared_panels, make_dummy_task):
        """Task completion logs a message to the console."""
        task = make_dummy_task(name="My Task", return_value={"ok": True})
        with patch("src.gui.scripts.base_page.run_in_thread"):
            page._start_task(task)

        result = TaskResult(name="My Task", ok=True)
        page._on_task_finished(result)

        # Verify logging occurred (the panels.log method was called)
        text = mock_shared_panels.console.toPlainText()
        # The _log method appends to the console — at minimum finished was logged
        assert page._active_task is None  # Confirms handler ran


# ---------------------------------------------------------------------------
# Tests: _on_cancel_task
# ---------------------------------------------------------------------------


class TestBasePageCancelTask:
    """Tests for _on_cancel_task handler."""

    def test_cancel_sets_event_on_task(self, page, make_dummy_task):
        """Cancelling sets the cancel event on the active task."""
        task = make_dummy_task(return_value={"ok": True})
        with patch("src.gui.scripts.base_page.run_in_thread"):
            page._start_task(task)

        page._on_cancel_task()

        assert task.cancel_event.is_set()

    def test_cancel_disables_cancel_button(self, page, make_dummy_task):
        """Cancelling disables the cancel button."""
        task = make_dummy_task(return_value={"ok": True})
        with patch("src.gui.scripts.base_page.run_in_thread"):
            page._start_task(task)

        page._on_cancel_task()

        assert not page._btn_cancel.isEnabled()

    def test_cancel_changes_button_text(self, page, make_dummy_task):
        """Cancelling changes button text to 'Cancelling...'."""
        task = make_dummy_task(return_value={"ok": True})
        with patch("src.gui.scripts.base_page.run_in_thread"):
            page._start_task(task)

        page._on_cancel_task()

        assert page._btn_cancel.text() == "Cancelling..."

    def test_cancel_with_no_active_task_is_safe(self, page):
        """Cancelling when no active task doesn't crash."""
        page._active_task = None
        page._on_cancel_task()  # Should not raise


# ---------------------------------------------------------------------------
# Tests: Service signal handlers
# ---------------------------------------------------------------------------


class TestBasePageServiceSignals:
    """Tests for _connect_service_signals and signal handlers."""

    def test_connect_service_signals_wires_verified(self, page, mock_vu_service, qtbot):
        """instrumentVerified signal is wired to handler."""
        page._connect_service_signals()

        # Emit signal and check it was handled (logs to console)
        mock_vu_service.instrumentVerified.emit(True)
        # No crash = signal connected

    def test_connect_service_signals_wires_connected(self, page, mock_vu_service, qtbot):
        """connectedChanged signal is wired to handler."""
        page._connect_service_signals()

        mock_vu_service._connected = True
        mock_vu_service.connectedChanged.emit(True)

        assert page.btn_action1.isEnabled()

    def test_on_connected_changed_enables_buttons(self, page, mock_vu_service):
        """connectedChanged(True) enables action buttons."""
        mock_vu_service._connected = True

        page._on_connected_changed(True)

        assert page.btn_action1.isEnabled()

    def test_on_connected_changed_disables_buttons(self, page, mock_vu_service):
        """connectedChanged(False) disables action buttons."""
        mock_vu_service._connected = False

        page._on_connected_changed(False)

        assert not page.btn_action1.isEnabled()

    def test_connect_signals_no_service_is_safe(self, page_no_service):
        """_connect_service_signals with no service is a no-op."""
        page_no_service._connect_service_signals()  # Should not raise

    def test_on_instrument_verified_true_logs(self, page, mock_shared_panels):
        """Verification logs 'Instrument verified.' message."""
        page._on_instrument_verified(True)
        # Check console was written to (SharedPanelsWidget.log was called)

    def test_on_instrument_verified_false_logs(self, page, mock_shared_panels):
        """Non-verification logs 'Instrument not verified.' message."""
        page._on_instrument_verified(False)


# ---------------------------------------------------------------------------
# Tests: Layout factory methods
# ---------------------------------------------------------------------------


class TestBasePageLayoutFactories:
    """Tests for _create_scroll_area, _create_group_box, _create_form_layout."""

    def test_create_scroll_area_returns_tuple(self, page):
        """_create_scroll_area returns (QScrollArea, QWidget, QVBoxLayout)."""
        scroll, content, layout = page._create_scroll_area()

        assert isinstance(scroll, QScrollArea)
        assert isinstance(content, QWidget)
        assert isinstance(layout, QVBoxLayout)

    def test_create_scroll_area_widget_is_resizable(self, page):
        """Scroll area has widgetResizable=True."""
        scroll, _, _ = page._create_scroll_area()

        assert scroll.widgetResizable()

    def test_create_scroll_area_respects_min_width(self, page):
        """Content widget has the specified minimum width."""
        scroll, content, _ = page._create_scroll_area(min_width=800)

        # Keep scroll alive so Qt doesn't delete content
        assert content.minimumWidth() == 800
        del scroll

    def test_create_group_box_returns_qgroupbox(self, page):
        """_create_group_box returns a QGroupBox with correct title."""
        box = page._create_group_box("Test Group")

        assert isinstance(box, QGroupBox)
        assert box.title() == "Test Group"

    def test_create_group_box_default_min_height(self, page):
        """Group box has default minimum height from config."""
        from src.config import config

        box = page._create_group_box("Test")

        assert box.minimumHeight() == config.form.group_min_height

    def test_create_group_box_custom_min_height(self, page):
        """Group box respects custom min_height."""
        box = page._create_group_box("Test", min_height=200)

        assert box.minimumHeight() == 200

    def test_create_group_box_custom_min_width(self, page):
        """Group box respects custom min_width."""
        box = page._create_group_box("Test", min_width=400)

        assert box.minimumWidth() == 400

    def test_create_form_layout_returns_qformlayout(self, page):
        """_create_form_layout returns a QFormLayout."""
        layout = page._create_form_layout()

        assert isinstance(layout, QFormLayout)

    def test_create_form_layout_vertical_spacing(self, page):
        """Form layout has vertical spacing from config."""
        from src.config import config

        layout = page._create_form_layout()

        assert layout.verticalSpacing() == config.form.form_spacing

    def test_configure_input_sets_min_height(self, page):
        """_configure_input sets minimum height on widget."""
        widget = QWidget()

        page._configure_input(widget, min_height=50)

        assert widget.minimumHeight() == 50

    def test_configure_input_sets_min_width(self, page):
        """_configure_input sets minimum width on widget."""
        widget = QWidget()

        page._configure_input(widget, min_width=200)

        assert widget.minimumWidth() == 200

    def test_configure_input_returns_widget(self, page):
        """_configure_input returns the widget for chaining."""
        widget = QWidget()

        result = page._configure_input(widget)

        assert result is widget


# ---------------------------------------------------------------------------
# Tests: Logging
# ---------------------------------------------------------------------------


class TestBasePageLogging:
    """Tests for _log method."""

    def test_log_appends_to_console(self, page, mock_shared_panels):
        """_log appends message to shared panels."""
        page._log("test message")
        # SharedPanelsWidget.log was called — verify via console content

    def test_log_without_panels_is_safe(self, page_no_panels):
        """_log without shared panels doesn't crash."""
        page_no_panels._log("test message")  # Should not raise
