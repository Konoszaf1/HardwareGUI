"""Main Window of the application."""

import contextlib

from PySide6.QtCore import (
    QPoint,
    Qt,
)
from PySide6.QtGui import (
    QAction,
    QColor,
    QKeySequence,
    QMouseEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QMainWindow,
    QMenu,
    QMenuBar,
    QSizePolicy,
    QWidget,
)

from src.config import config
from src.gui.button_factory import build_tool_buttons
from src.gui.services.shared_panels_service import SharedPanelsService
from src.gui.services.status_bar_service import StatusBarService
from src.gui.styles import Styles
from src.gui.widgets.action_stacked_widget import ContentWithPanels
from src.logic.presenter import ActionsPresenter
from src.populate_items import ACTIONS, HARDWARE
from src.ui_main_window import Ui_MainWindow


class MainWindow(QMainWindow):
    """Frameless main window for hardware control.

    Layout:
        - Left: Sidebar with hardware buttons + action list
        - Right: Action pages (with persistent panels per hardware)

    Attributes:
        ui (Ui_MainWindow): The UI definition.
        splitter (ExpandingSplitter): Custom splitter for sidebar/actions.
        actions (list[ActionDescriptor]): List of available actions.
        presenter (ActionsPresenter): Logical presenter.
        buttons (list[SidebarButton]): Hardware sidebar buttons.
    """

    def __init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self._init_attributes()
        self._init_services()

        self.setup_splitter()
        self.presenter.connect_actions_and_stacked_view(self.actions)

        self._setup_status_bar()
        self._setup_menu_bar()
        self._style_title_bar()
        self._setup_window_properties()

    def _init_attributes(self) -> None:
        """Initialize basic attributes and resize state."""
        self.splitter = None
        self.sidebar = None
        self.list_view = None
        self.actions = None
        self.presenter = None
        self.buttons = build_tool_buttons(self, HARDWARE)
        self.stacked_widget = self.ui.stackedWidget

        # Window drag state
        self.dragging = False
        self.drag_position = QPoint()

    def _init_services(self) -> None:
        """Initialize application services."""
        self.panels_service = SharedPanelsService.init()
        self._current_panels = None
        self._artifacts_expanded = False
        self._artifacts_anim = None
        self._current_hardware_id: int | None = None

    def _setup_status_bar(self) -> None:
        """Configure the status bar and connect signals."""
        self.ui.statusbar.setStyleSheet(Styles.STATUS_BAR)
        self.ui.statusbar.setVisible(True)
        self.ui.statusbar.setSizeGripEnabled(True)
        StatusBarService.init(self.ui.statusbar)

        if self.presenter and self.presenter.service:
            self.presenter.service.scopeVerified.connect(self._on_scope_status_changed)

    def _setup_window_properties(self) -> None:
        """Configure window flags and effects."""
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(config.ui.window_min_width, config.ui.window_min_height)

        self.ui.minimizePushButton.clicked.connect(self.showMinimized)
        self.ui.maximizePushButton.clicked.connect(self.toggle_max_restore)
        self.ui.closePushButton.clicked.connect(self.close)

        self.ui.maximizePushButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.ui.minimizePushButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 0)
        self.centralWidget().setGraphicsEffect(shadow)

    def setup_splitter(self) -> None:
        """Populate the splitter with sidebar and list view."""
        self.splitter = self.ui.splitter
        self.list_view = self.ui.listView
        self.sidebar = self.ui.sidebar
        self.actions = ACTIONS

        # Splitter minimum width = sidebar collapsed + list view minimum
        self.splitter.setMinimumWidth(config.ui.sidebar_collapsed_width + 150)

        shared_panels = self.panels_service.get_panels(1)
        self._current_panels = shared_panels
        self._artifacts_expanded = shared_panels.is_artifacts_visible()
        shared_panels.artifacts_toggled.connect(self._on_artifacts_panel_toggled)
        shared_panels.console_toggled.connect(self._on_console_panel_toggled)

        self.content_with_panels = ContentWithPanels(self.stacked_widget, shared_panels, self)

        # Enable mouse tracking on central widget to propagate hover events to MainWindow
        self.ui.centralwidget.setMouseTracking(True)

        self.content_with_panels.setVisible(False)

        parent_widget = self.ui.centralwidget
        grid_layout = parent_widget.layout()
        grid_layout.setContentsMargins(0, 0, 0, 0)  # No margins - borderless
        grid_layout.removeWidget(self.stacked_widget)
        grid_layout.addWidget(self.content_with_panels, 1, 1)
        grid_layout.setColumnStretch(0, 0)
        grid_layout.setColumnStretch(1, 1)

        self.presenter = ActionsPresenter(self, self.buttons, self.actions, shared_panels)
        self.stacked_widget.currentPageIdChanged.connect(self._on_page_changed)

        # Configure splitter with sidebar and listview (stretch factors set in those methods)
        self.splitter.set_sidebar(self.ui.sidebar)
        self.splitter.set_listview(self.list_view)

        for button in self.buttons:
            self.sidebar.layout().insertWidget(button.property("order"), button)
            self.splitter.add_button(button)
            button.toggled.connect(
                lambda checked, btn=button: checked
                and self._on_hardware_selected(btn.property("id"))
            )

        self.sidebar.layout().activate()
        self.sidebar.adjustSize()
        for button in self.buttons:
            button.setMinimumWidth(config.ui.sidebar_collapsed_width)
            button.updateGeometry()

        self.splitter.collapse_immediate()
        QApplication.processEvents()

    def toggle_max_restore(self) -> None:
        """Toggle between maximized and normal window states."""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _on_page_changed(self, page_id: str, widget: QWidget) -> None:
        """Show panels container when an action page is selected."""
        if not self.content_with_panels.isVisible():
            self.content_with_panels.setVisible(True)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle window drag start.

        Args:
            event (QMouseEvent): The mouse event.
        """
        if event.button() != Qt.MouseButton.LeftButton:
            return

        # Use system move if available
        if self.windowHandle().startSystemMove():
            return
        self.dragging = True
        self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle window drag.

        Args:
            event (QMouseEvent): The mouse event.
        """
        if event.buttons() == Qt.MouseButton.LeftButton and self.dragging:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle window drag end."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            event.accept()

    def _on_scope_status_changed(self, verified: bool) -> None:
        """Handle scope verification status changes.

        Args:
            verified (bool): Whether the scope is verified.
        """
        StatusBarService.instance().set_scope_connected(connected=verified)
        if verified:
            StatusBarService.instance().set_ready()

    def _on_hardware_selected(self, hardware_id: int) -> None:
        """Handle hardware selection changes.

        Args:
            hardware_id (int): The ID of the selected hardware.
        """
        self.setUpdatesEnabled(False)
        try:
            self._current_hardware_id = hardware_id
            StatusBarService.instance().set_active_hardware(hardware_id)

            # Disconnect from old panels
            if self._current_panels:
                with contextlib.suppress(TypeError, RuntimeError):
                    self._current_panels.artifacts_toggled.disconnect(
                        self._on_artifacts_panel_toggled
                    )
                with contextlib.suppress(TypeError, RuntimeError):
                    self._current_panels.console_toggled.disconnect(self._on_console_panel_toggled)

            # Get panels for this hardware
            new_panels = self.panels_service.switch_hardware(hardware_id)
            new_expanded = new_panels.is_artifacts_visible()

            # 1. Swap panels FIRST to prime constraints (sets QStackedWidget sizes)
            if hasattr(self, "content_with_panels"):
                self.content_with_panels.set_panels(new_panels)
                # Reconnect toggle signals to new panels
                new_panels.artifacts_toggled.connect(self._on_artifacts_panel_toggled)
                new_panels.console_toggled.connect(self._on_console_panel_toggled)

            # 2. Force layout update so constraints are settled
            self.centralWidget().layout().activate()

            # 3. Synchronize window size AFTER panels are swapped and constraints are set
            if new_expanded != self._artifacts_expanded:
                self._on_artifacts_panel_toggled(new_expanded)

            self._current_panels = new_panels

            # Update presenter's shared panels reference
            if self.presenter:
                self.presenter.shared_panels = new_panels

            # 4. Restore last selected action for this hardware
            if self.presenter:
                self.presenter.restore_last_action(hardware_id)
        finally:
            self.setUpdatesEnabled(True)
            self.update()  # Force final repaint

    def _on_artifacts_panel_toggled(self, expanded: bool) -> None:
        """Handle artifact panel toggle (state update only).

        Args:
            expanded (bool): Whether the panel is expanded.
        """
        if expanded == self._artifacts_expanded:
            return
        self._artifacts_expanded = expanded

    def _setup_menu_bar(self) -> None:
        """Create and configure the application menu bar."""
        menu_bar = QMenuBar(self)
        menu_bar.setStyleSheet(Styles.MENU_BAR)
        menu_bar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        menu_bar.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)

        # File menu
        file_menu = QMenu("File", self)
        settings_action = QAction("Settings...", self)
        settings_action.triggered.connect(self._on_settings)
        file_menu.addAction(settings_action)
        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        menu_bar.addMenu(file_menu)
        menu_bar.addMenu(QMenu("Edit", self))

        # View menu with panel toggles
        view_menu = QMenu("View", self)

        self.toggle_console_action = QAction("Toggle Terminal", self)
        self.toggle_console_action.setShortcut(QKeySequence("Ctrl+`"))
        self.toggle_console_action.setCheckable(True)
        self.toggle_console_action.setChecked(False)
        self.toggle_console_action.triggered.connect(self._on_toggle_console)
        view_menu.addAction(self.toggle_console_action)

        self.toggle_artifacts_action = QAction("Toggle Artifacts", self)
        self.toggle_artifacts_action.setShortcut(QKeySequence("Ctrl+1"))
        self.toggle_artifacts_action.setCheckable(True)
        self.toggle_artifacts_action.setChecked(False)
        self.toggle_artifacts_action.triggered.connect(self._on_toggle_artifacts)
        view_menu.addAction(self.toggle_artifacts_action)

        menu_bar.addMenu(view_menu)
        menu_bar.addMenu(QMenu("Help", self))

        self.ui.titleBar.insertWidget(0, menu_bar)

    def _on_settings(self) -> None:
        pass

    def _on_toggle_console(self, checked: bool) -> None:
        """Toggle console panel visibility.

        Args:
            checked (bool): New checked state.
        """
        if self._current_panels:
            self._current_panels.show_console(checked)

    def _on_toggle_artifacts(self, checked: bool) -> None:
        """Toggle artifacts panel visibility.

        Args:
            checked (bool): New checked state.
        """
        if self._current_panels:
            self._current_panels.show_artifacts(checked)

    def _on_console_panel_toggled(self, expanded: bool) -> None:
        """Sync menu action state when console panel button is clicked.

        Args:
            expanded (bool): New expanded state.
        """
        self.toggle_console_action.setChecked(expanded)

    def _style_title_bar(self) -> None:
        """Apply styling to title bar buttons."""
        self.ui.minimizePushButton.setStyleSheet(Styles.TITLE_BAR_BUTTON)
        self.ui.maximizePushButton.setStyleSheet(Styles.TITLE_BAR_BUTTON)
        self.ui.closePushButton.setStyleSheet(Styles.TITLE_BAR_BUTTON)
