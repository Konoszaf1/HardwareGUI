"""Shared panels widget with toggleable console and artifacts.

Provides IDE-style toggleable panels for console (bottom) and artifacts (right)
that persist within a hardware selection. When collapsed, panels hide completely
with only a small toggle button remaining.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.config import config
from src.gui.styles import Styles
from src.gui.utils.gui_helpers import append_log
from src.gui.utils.widget_factories import (
    create_artifact_list_widget,
    create_console_widget,
    create_input_field,
)


class HorizontalCollapsiblePanel(QFrame):
    """Collapsible panel that expands/collapses vertically (for bottom panel)."""

    toggled = Signal(bool)

    def __init__(self, title: str, start_collapsed: bool = False, parent=None):
        super().__init__(parent)
        self._expanded = not start_collapsed
        self._title = title

        self.setStyleSheet(Styles.COLLAPSIBLE_PANEL)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        # Toggle button (horizontal bar)
        self._toggle_btn = QPushButton()
        self._toggle_btn.setFixedHeight(config.ui.panel_toggle_size)
        self._toggle_btn.setCursor(Qt.PointingHandCursor)
        self._toggle_btn.clicked.connect(self._on_toggle)
        self._update_button()
        self._style_button()

        # Content container
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)

        self._layout.addWidget(self._toggle_btn)
        self._layout.addWidget(self._content, 1)

        # Apply initial collapsed state
        if start_collapsed:
            self._content.setVisible(False)

    def _style_button(self) -> None:
        self._toggle_btn.setStyleSheet(Styles.PANEL_TOGGLE_BUTTON)

    def _update_button(self) -> None:
        icon = "▼" if self._expanded else "▲"
        self._toggle_btn.setText(f"{icon}  {self._title}")

    def _on_toggle(self) -> None:
        self.set_expanded(not self._expanded)
        self.toggled.emit(self._expanded)

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        self._update_button()
        self._content.setVisible(expanded)
        if expanded:
            self.setMinimumHeight(config.ui.terminal_min_height)
            self.setMaximumHeight(16777215)
        else:
            self.setMinimumHeight(config.ui.panel_toggle_size)
            self.setMaximumHeight(config.ui.panel_toggle_size)

    @property
    def is_expanded(self) -> bool:
        return self._expanded

    def add_widget(self, widget: QWidget, stretch: int = 0) -> None:
        self._content_layout.addWidget(widget, stretch)


class VerticalCollapsiblePanel(QFrame):
    """Collapsible panel that expands/collapses horizontally (for side panel)."""

    toggled = Signal(bool)

    def __init__(self, title: str, start_collapsed: bool = False, parent=None):
        super().__init__(parent)
        self._expanded = not start_collapsed
        self._title = title

        self.setStyleSheet(Styles.COLLAPSIBLE_PANEL)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        # Toggle button (vertical bar on left side)
        self._toggle_btn = QPushButton()
        self._toggle_btn.setFixedWidth(config.ui.panel_toggle_size)
        self._toggle_btn.setCursor(Qt.PointingHandCursor)
        self._toggle_btn.clicked.connect(self._on_toggle)
        self._update_button()
        self._style_button()

        # Content container
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)

        # Button on left, content on right
        self._layout.addWidget(self._toggle_btn)
        self._layout.addWidget(self._content, 1)

        # Apply initial collapsed state and enforce strict width
        if start_collapsed:
            self._content.setVisible(False)
            self._content.setFixedWidth(0)
            self.setFixedWidth(config.ui.panel_toggle_size)
        else:
            self._content.setFixedWidth(config.ui.artifacts_expanded_width)
            self.setFixedWidth(config.ui.artifacts_expanded_width + config.ui.panel_toggle_size)

    def _style_button(self) -> None:
        self._toggle_btn.setStyleSheet(Styles.PANEL_TOGGLE_BUTTON_VERTICAL)

    def _update_button(self) -> None:
        # Use simple arrow that doesn't need rotation
        icon = "◀" if self._expanded else "▶"
        self._toggle_btn.setText(icon)

    def _on_toggle(self) -> None:
        self.set_expanded(not self._expanded)

    def set_expanded(self, expanded: bool) -> None:
        if self._expanded != expanded:
            self._expanded = expanded
            self._update_button()
            self._content.setVisible(expanded)
            if expanded:
                self._content.setFixedWidth(config.ui.artifacts_expanded_width)
                self.setFixedWidth(config.ui.artifacts_expanded_width + config.ui.panel_toggle_size)
            else:
                self._content.setFixedWidth(0)
                self.setFixedWidth(config.ui.panel_toggle_size)
            self.toggled.emit(expanded)

    @property
    def is_expanded(self) -> bool:
        return self._expanded

    def add_widget(self, widget: QWidget, stretch: int = 0) -> None:
        self._content_layout.addWidget(widget, stretch)


class SharedPanelsWidget(QWidget):
    """Container with toggleable console (bottom) and artifacts (right) panels.

    When panels are collapsed, they hide completely leaving only a small
    toggle button. Content expands to fill available space.
    """

    console_toggled = Signal(bool)
    artifacts_toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Console panel (bottom, horizontal collapse)
        self._console_panel = HorizontalCollapsiblePanel("TERMINAL", start_collapsed=True)
        self._console_panel.toggled.connect(self._on_console_toggled)

        self._console = create_console_widget()
        self._input_field = create_input_field()
        self._input_field.returnPressed.connect(self._on_input_return)

        self._console_panel.add_widget(self._input_field)
        self._console_panel.add_widget(self._console, stretch=1)

        # Artifacts panel (right, vertical collapse)
        self._artifacts_panel = VerticalCollapsiblePanel("ARTIFACTS", start_collapsed=True)
        self._artifacts_panel.toggled.connect(self._on_artifacts_toggled)

        self._artifacts = create_artifact_list_widget()
        self._artifacts_panel.add_widget(self._artifacts, stretch=1)

        # Panel state (start collapsed)
        self._console_visible = False
        self._artifacts_visible = False

    # ---- Public API ----

    @property
    def console(self) -> QPlainTextEdit:
        """Return the console widget."""
        return self._console

    @property
    def artifacts(self) -> QListWidget:
        """Return the artifacts list widget."""
        return self._artifacts

    @property
    def input_field(self):
        """Return the input field widget."""
        return self._input_field

    def log(self, msg: str) -> None:
        """Append message to console, auto-scroll if expanded."""
        append_log(self._console, msg)
        if self._console_visible:
            self._scroll_console_to_end()

    def clear(self) -> None:
        """Clear both console and artifacts."""
        self._console.clear()
        self._artifacts.clear()

    def show_console(self, visible: bool) -> None:
        """Show or collapse the console panel."""
        self._console_visible = visible
        self._console_panel.set_expanded(visible)
        if visible:
            self._scroll_console_to_end()

    def show_artifacts(self, visible: bool) -> None:
        """Show or collapse the artifacts panel."""
        self._artifacts_visible = visible
        self._artifacts_panel.set_expanded(visible)

    def is_console_visible(self) -> bool:
        return self._console_visible

    def is_artifacts_visible(self) -> bool:
        return self._artifacts_visible

    # ---- Input handling ----

    def show_input(self, prompt: str = "") -> None:
        """Show the input field with optional placeholder."""
        self._input_field.setPlaceholderText(prompt or "Type input here...")
        self._input_field.setVisible(True)
        self._input_field.setFocus()

    def _on_input_return(self) -> None:
        """Handle Enter in input field - to be connected by pages."""
        pass  # Will be connected by BaseHardwarePage

    # ---- Private ----

    def _on_console_toggled(self, expanded: bool) -> None:
        self._console_visible = expanded
        if expanded:
            self._scroll_console_to_end()
        self.console_toggled.emit(expanded)

    def _on_artifacts_toggled(self, expanded: bool) -> None:
        self._artifacts_visible = expanded
        self.artifacts_toggled.emit(expanded)

    def _scroll_console_to_end(self) -> None:
        """Scroll console to the end."""
        scrollbar = self._console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
