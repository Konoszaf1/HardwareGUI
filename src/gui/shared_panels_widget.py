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
    """Collapsible panel that expands/collapses vertically (for bottom panel).

    Attributes:
        toggled (Signal): Signal emitted when panel is toggled (bool expanded).
    """

    toggled = Signal(bool)

    def __init__(self, title: str, start_collapsed: bool = False, parent: QWidget | None = None):
        """Initialize the horizontal collapsible panel.

        Args:
            title (str): Title of the panel.
            start_collapsed (bool): Whether to start in collapsed state.
            parent (QWidget | None): Parent widget.
        """
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
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
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
        """Apply styles to the toggle button."""
        self._toggle_btn.setStyleSheet(Styles.PANEL_TOGGLE_BUTTON)

    def _update_button(self) -> None:
        """Update toggle button text/icon based on state."""
        icon = "▼" if self._expanded else "▲"
        self._toggle_btn.setText(f"{icon}  {self._title}")

    def _on_toggle(self) -> None:
        """Handle toggle button click."""
        self.set_expanded(not self._expanded)
        self.toggled.emit(self._expanded)

    def set_expanded(self, expanded: bool) -> None:
        """Set the expanded state of the panel.

        Args:
            expanded (bool): True to expand, False to collapse.
        """
        self._expanded = expanded
        self._update_button()
        self._content.setVisible(expanded)
        if expanded:
            self.setMinimumHeight(config.ui.terminal_min_height)
            self.setMaximumHeight(config.ui.max_widget_size)
        else:
            self.setMinimumHeight(config.ui.panel_toggle_size)
            self.setMaximumHeight(config.ui.panel_toggle_size)

    @property
    def is_expanded(self) -> bool:
        """Return whether the panel is currently expanded.

        Returns:
            bool: True if expanded.
        """
        return self._expanded

    def add_widget(self, widget: QWidget, stretch: int = 0) -> None:
        """Add a widget to the content area.

        Args:
            widget (QWidget): Widget to add.
            stretch (int): Stretch factor.
        """
        self._content_layout.addWidget(widget, stretch)


class VerticalCollapsiblePanel(QFrame):
    """Collapsible panel that expands/collapses horizontally (for side panel).

    Attributes:
        toggled (Signal): Signal emitted when panel is toggled (bool expanded).
    """

    toggled = Signal(bool)

    def __init__(self, title: str, start_collapsed: bool = False, parent: QWidget | None = None):
        """Initialize the vertical collapsible panel.

        Args:
            title (str): Title of the panel.
            start_collapsed (bool): Whether to start in collapsed state.
            parent (QWidget | None): Parent widget.
        """
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
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
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
        """Apply styles to the toggle button."""
        self._toggle_btn.setStyleSheet(Styles.PANEL_TOGGLE_BUTTON_VERTICAL)

    def _update_button(self) -> None:
        """Update toggle button text/icon based on state."""
        # Use simple arrow that doesn't need rotation
        icon = "◀" if self._expanded else "▶"
        self._toggle_btn.setText(icon)

    def _on_toggle(self) -> None:
        """Handle toggle button click."""
        self.set_expanded(not self._expanded)

    def set_expanded(self, expanded: bool, immediate: bool = False) -> None:
        """Set the expanded state.

        Args:
            expanded (bool): Target expanded state.
            immediate (bool): If True, apply layout changes instantly.
        """
        if self._expanded != expanded or immediate:
            self._expanded = expanded
            self._update_button()

            if immediate:
                self._content.setVisible(expanded)
                if expanded:
                    self._content.setMinimumWidth(0)
                    self._content.setMaximumWidth(config.ui.artifacts_expanded_width)
                    self.setFixedWidth(
                        config.ui.artifacts_expanded_width + config.ui.panel_toggle_size
                    )
                else:
                    self._content.setFixedWidth(0)
                    self.setFixedWidth(config.ui.panel_toggle_size)
                    self.setMinimumWidth(config.ui.panel_toggle_size)
                    self.setMaximumWidth(config.ui.panel_toggle_size)
            else:
                # During transition, always keep content visible so it doesn't flicker
                self._content.setVisible(True)

                # IMPORTANT: Keep the content fixed at its expanded width even when shrinking.
                # This allows the parent stack to 'mask' it, creating a sliding effect
                # instead of a jagged squeezing effect.
                self._content.setFixedWidth(config.ui.artifacts_expanded_width)

                # Allow the parent stack/window to drive the outer width
                self.setMinimumWidth(config.ui.panel_toggle_size)
                self.setMaximumWidth(
                    config.ui.artifacts_expanded_width + config.ui.panel_toggle_size
                )

            self.toggled.emit(expanded)

    @property
    def is_expanded(self) -> bool:
        """Return whether the panel is currently expanded.

        Returns:
            bool: True if expanded.
        """
        return self._expanded

    def add_widget(self, widget: QWidget, stretch: int = 0) -> None:
        """Add a widget to the content area.

        Args:
            widget (QWidget): Widget to add.
            stretch (int): Stretch factor.
        """
        self._content_layout.addWidget(widget, stretch)


class SharedPanelsWidget(QWidget):
    """Container with toggleable console (bottom) and artifacts (right) panels.

    When panels are collapsed, they hide completely leaving only a small
    toggle button. Content expands to fill available space.

    Attributes:
        console_toggled (Signal): Signal emitted when console is toggled.
        artifacts_toggled (Signal): Signal emitted when artifacts are toggled.
    """

    console_toggled = Signal(bool)
    artifacts_toggled = Signal(bool)

    def __init__(self, parent: QWidget | None = None):
        """Initialize the shared panels widget.

        Args:
            parent (QWidget | None): Parent widget.
        """
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
        """Return the console widget.

        Returns:
            QPlainTextEdit: The console.
        """
        return self._console

    @property
    def artifacts(self) -> QListWidget:
        """Return the artifacts list widget.

        Returns:
            QListWidget: The artifacts list.
        """
        return self._artifacts

    @property
    def input_field(self) -> QPlainTextEdit:  # Assuming it returns a text edit or line edit
        """Return the input field widget.

        Returns:
            QWidget: The input field.
        """
        return self._input_field

    def log(self, msg: str) -> None:
        """Append message to console, auto-scroll if expanded.

        Args:
            msg (str): Message to log.
        """
        append_log(self._console, msg)
        if self._console_visible:
            self._scroll_console_to_end()

    def clear(self) -> None:
        """Clear both console and artifacts."""
        self._console.clear()
        self._artifacts.clear()

    def show_console(self, visible: bool) -> None:
        """Show or collapse the console panel.

        Args:
            visible (bool): True to show, False to collapse.
        """
        self._console_visible = visible
        self._console_panel.set_expanded(visible)
        if visible:
            self._scroll_console_to_end()

    def show_artifacts(self, visible: bool) -> None:
        """Show or collapse the artifacts panel.

        Args:
            visible (bool): True to show, False to collapse.
        """
        self._artifacts_visible = visible
        self._artifacts_panel.set_expanded(visible)

    def is_console_visible(self) -> bool:
        """Return whether the console is visible.

        Returns:
            bool: True if visible.
        """
        return self._console_visible

    def is_artifacts_visible(self) -> bool:
        """Return whether the artifacts panel is visible.

        Returns:
            bool: True if visible.
        """
        return self._artifacts_visible

    # ---- Input handling ----

    def show_input(self, prompt: str = "") -> None:
        """Show the input field with optional placeholder.

        Args:
            prompt (str): Placeholder text.
        """
        self._input_field.setPlaceholderText(prompt or "Type input here...")
        self._input_field.setVisible(True)
        self._input_field.setFocus()

    def _on_input_return(self) -> None:
        """Handle Enter in input field - to be connected by pages."""
        pass  # Will be connected by BaseHardwarePage

    # ---- Private ----

    def _on_console_toggled(self, expanded: bool) -> None:
        """Handle console toggle signal.

        Args:
            expanded (bool): New state.
        """
        self._console_visible = expanded
        if expanded:
            self._scroll_console_to_end()
        self.console_toggled.emit(expanded)

    def _on_artifacts_toggled(self, expanded: bool) -> None:
        """Handle artifacts toggle signal.

        Args:
            expanded (bool): New state.
        """
        self._artifacts_visible = expanded
        self.artifacts_toggled.emit(expanded)

    def _scroll_console_to_end(self) -> None:
        """Scroll console to the end."""
        scrollbar = self._console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
