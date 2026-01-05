"""Main Window of the application"""

import contextlib

from PySide6.QtCore import QEasingCurve, QPoint, Qt, QVariantAnimation
from PySide6.QtGui import QAction, QColor, QKeySequence
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QMainWindow,
    QMenu,
    QMenuBar,
    QWidget,
)

from src.config import config
from src.gui.button_factory import build_tool_buttons
from src.gui.expanding_splitter import ExpandingSplitter
from src.gui.hiding_listview import HidingListView
from src.gui.shared_panels_service import SharedPanelsService
from src.gui.sidebar_button import SidebarButton
from src.gui.status_bar_service import StatusBarService
from src.gui.styles import Styles
from src.logic.action_dataclass import ActionDescriptor
from src.logic.presenter import ActionsPresenter
from src.populate_items import ACTIONS, HARDWARE
from src.ui_main_window import Ui_MainWindow


class MainWindow(QMainWindow):
    """Frameless main window for hardware control.

    Layout:
        - Left: Sidebar with hardware buttons + action list
        - Right: Action pages (with persistent panels per hardware)
    """

    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.splitter: ExpandingSplitter | None = None
        self.sidebar: QWidget | None = None
        self.list_view: HidingListView | None = None
        self.actions: list[ActionDescriptor] | None = None
        self.presenter: ActionsPresenter | None = None
        self.buttons: list[SidebarButton] = build_tool_buttons(self, HARDWARE)
        self.stacked_widget = self.ui.stackedWidget

        # Initialize shared panels service (panels managed per hardware)
        self.panels_service = SharedPanelsService.init()
        self._current_panels: QWidget | None = None
        self._artifacts_expanded: bool = False
        self._artifacts_anim: QVariantAnimation | None = None

        self.setup_splitter()
        self.presenter.connect_actions_and_stacked_view(self.actions)

        # Status bar setup - with resize grip for bottom-right corner
        self.ui.statusbar.setStyleSheet(Styles.STATUS_BAR)
        self.ui.statusbar.setVisible(True)
        self.ui.statusbar.setSizeGripEnabled(True)  # Enable resize grip
        StatusBarService.init(self.ui.statusbar)

        # Connect scope verification to status bar
        self.presenter.service.scopeVerified.connect(self._on_scope_status_changed)

        # Menu bar setup
        self._setup_menu_bar()

        # Title bar styling
        self._style_title_bar()

        # Window setup - frameless with translucent background
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(config.ui.window_min_width, config.ui.window_min_height)
        self.ui.minimizePushButton.clicked.connect(self.showMinimized)
        self.ui.maximizePushButton.clicked.connect(self.toggle_max_restore)
        self.ui.closePushButton.clicked.connect(self.close)
        self.dragging = False
        self.drag_position = QPoint()
        self.ui.maximizePushButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.ui.minimizePushButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Enable mouse tracking for resize cursors
        self.setMouseTracking(True)
        self._resize_edge = None
        self._resize_margin = 10

        # Drop shadow
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

        # Set minimum sizes - sidebar needs space for buttons, list needs space for text
        self.sidebar.setMinimumWidth(70)  # Match button minimum width
        self.sidebar.layout().setContentsMargins(0, 0, 0, 0)
        self.sidebar.layout().setSpacing(0)
        self.list_view.setMinimumWidth(150)  # Enough for action names
        # Set minimum on entire splitter to prevent compression
        self.splitter.setMinimumWidth(70 + 150)

        # Get shared panels for first hardware (will update on selection)
        shared_panels = self.panels_service.get_panels(1)
        self._current_panels = shared_panels
        self._artifacts_expanded = shared_panels.is_artifacts_visible()

        # Connect panel toggle signals to resize window
        shared_panels.artifacts_toggled.connect(self._on_artifacts_panel_toggled)

        # Wrap the stacked widget with panels container for persistent panels
        from src.gui.action_stacked_widget import ContentWithPanels

        self.content_with_panels = ContentWithPanels(self.stacked_widget, shared_panels, self)

        # Hide panels container until an action is selected
        self.content_with_panels.setVisible(False)

        # Replace stacked widget in the grid layout with the wrapped version
        parent_widget = self.ui.centralwidget
        grid_layout = parent_widget.layout()
        # Remove stacked widget from grid (row 1, col 1)
        grid_layout.removeWidget(self.stacked_widget)
        # Add wrapped version
        grid_layout.addWidget(self.content_with_panels, 1, 1)

        # Set column stretch: Sidebar (0) is static, Content (1) expands
        grid_layout.setColumnStretch(0, 0)
        grid_layout.setColumnStretch(1, 1)

        # Create presenter with shared panels
        self.presenter = ActionsPresenter(self, self.buttons, self.actions, shared_panels)

        # Show panels when an action page is displayed
        self.stacked_widget.currentPageIdChanged.connect(self._on_page_changed)

        self.splitter.set_sidebar(self.ui.sidebar)
        self.splitter.set_listview(self.list_view)

        # Set splitter stretch to 0 for both to respect size hints (non-greedy)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 0)

        # Add buttons to sidebar
        for button in self.buttons:
            self.sidebar.layout().insertWidget(button.property("order"), button)
            self.splitter.add_button(button)
            button.toggled.connect(
                lambda checked, btn=button: checked
                and self._on_hardware_selected(btn.property("id"))
            )

        # Force immediate layout update on sidebar and buttons
        from PySide6.QtWidgets import QApplication

        self.sidebar.layout().activate()
        self.sidebar.adjustSize()
        for button in self.buttons:
            button.setMinimumWidth(config.ui.sidebar_collapsed_width)
            button.updateGeometry()

        # Ensure initial splitter state is applied
        self.splitter.collapse_immediate()
        QApplication.processEvents()

    def toggle_max_restore(self):
        """Toggle between maximized and normal window states."""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _on_page_changed(self, page_id: str, widget) -> None:
        """Show panels container when an action page is selected."""
        if not self.content_with_panels.isVisible():
            self.content_with_panels.setVisible(True)

    def _get_resize_edge(self, pos):
        """Determine which edge(s) the mouse is near for resizing."""
        rect = self.rect()
        m = self._resize_margin
        edges = []

        if pos.x() <= m:
            edges.append("left")
        elif pos.x() >= rect.width() - m:
            edges.append("right")

        if pos.y() <= m:
            edges.append("top")
        elif pos.y() >= rect.height() - m:
            edges.append("bottom")

        return tuple(edges) if edges else None

    def _update_cursor(self, edges):
        """Update cursor based on resize edges."""
        if not edges:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            return

        if edges == ("left",) or edges == ("right",):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif edges == ("top",) or edges == ("bottom",):
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif edges in [("left", "top"), ("right", "bottom")]:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif edges in [("right", "top"), ("left", "bottom")]:
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event):
        """Handle window drag or resize start."""
        if event.button() != Qt.MouseButton.LeftButton:
            return

        pos = event.position().toPoint()
        edges = self._get_resize_edge(pos)

        if edges:
            self._resize_edge = edges
            self._resize_start_pos = event.globalPosition().toPoint()
            self._resize_start_geo = self.geometry()
            event.accept()
        else:
            # Dragging
            if self.windowHandle().startSystemMove():
                return
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """Handle window drag or resize."""
        pos = event.position().toPoint()

        if event.buttons() == Qt.MouseButton.LeftButton:
            if self._resize_edge:
                # Resizing
                delta = event.globalPosition().toPoint() - self._resize_start_pos
                geo = self._resize_start_geo
                new_geo = geo

                if "left" in self._resize_edge:
                    new_geo = new_geo.adjusted(delta.x(), 0, 0, 0)
                if "right" in self._resize_edge:
                    new_geo = new_geo.adjusted(0, 0, delta.x(), 0)
                if "top" in self._resize_edge:
                    new_geo = new_geo.adjusted(0, delta.y(), 0, 0)
                if "bottom" in self._resize_edge:
                    new_geo = new_geo.adjusted(0, 0, 0, delta.y())

                # Enforce minimum size
                if (
                    new_geo.width() >= self.minimumWidth()
                    and new_geo.height() >= self.minimumHeight()
                ):
                    self.setGeometry(new_geo)
                event.accept()
            elif self.dragging:
                self.move(event.globalPosition().toPoint() - self.drag_position)
                event.accept()
        else:
            # Update cursor for resize edges
            edges = self._get_resize_edge(pos)
            self._update_cursor(edges)

    def mouseReleaseEvent(self, event):
        """Handle window drag or resize end."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self._resize_edge = None
            event.accept()

    def _on_scope_status_changed(self, verified: bool) -> None:
        """Handle scope verification status changes."""
        StatusBarService.instance().set_scope_connected(connected=verified)
        if verified:
            StatusBarService.instance().set_ready()

    def _on_hardware_selected(self, hardware_id: int) -> None:
        """Handle hardware selection changes."""
        self.setUpdatesEnabled(False)
        try:
            StatusBarService.instance().set_active_hardware(hardware_id)

            # Disconnect from old panels
            if self._current_panels:
                with contextlib.suppress(TypeError, RuntimeError):
                    self._current_panels.artifacts_toggled.disconnect(
                        self._on_artifacts_panel_toggled
                    )

            # Get panels for this hardware
            new_panels = self.panels_service.switch_hardware(hardware_id)
            new_expanded = new_panels.is_artifacts_visible()

            # 1. Swap panels FIRST to prime constraints (sets QStackedWidget sizes)
            if hasattr(self, "content_with_panels"):
                self.content_with_panels.set_panels(new_panels)
                # Reconnect toggle signal to new panels
                new_panels.artifacts_toggled.connect(self._on_artifacts_panel_toggled)

            # 2. Force layout update so constraints are settled
            self.centralWidget().layout().activate()

            # 3. Synchronize window size AFTER panels are swapped and constraints are set
            if new_expanded != self._artifacts_expanded:
                self._on_artifacts_panel_toggled(new_expanded)

            self._current_panels = new_panels

            # Update presenter's shared panels reference
            if self.presenter:
                self.presenter.shared_panels = new_panels
        finally:
            self.setUpdatesEnabled(True)
            self.update()  # Force final repaint

    def _on_artifacts_panel_toggled(self, expanded: bool) -> None:
        """Handle artifact panel toggle with a smooth animation."""
        if expanded == self._artifacts_expanded:
            return
        self._artifacts_expanded = expanded

        if self.isMaximized():
            return

        # Calculate dimensions
        total_width = self.content_with_panels.artifacts_expanded_total_width
        start_w = config.ui.panel_toggle_size if expanded else total_width
        end_w = total_width if expanded else config.ui.panel_toggle_size
        delta = total_width - config.ui.panel_toggle_size

        geo = self.geometry()
        start_win_w = geo.width()
        end_win_w = geo.width() + (delta if expanded else -delta)

        # Cleanup existing animation
        if self._artifacts_anim and self._artifacts_anim.state() == QVariantAnimation.State.Running:
            self._artifacts_anim.stop()

        # Create animation
        self._artifacts_anim = QVariantAnimation(self)
        self._artifacts_anim.setDuration(config.ui.panel_animation_duration_ms)

        # Resolve easing curve from config
        easing_type = getattr(
            QEasingCurve.Type, config.ui.panel_animation_easing, QEasingCurve.Type.InOutQuad
        )
        self._artifacts_anim.setEasingCurve(easing_type)

        self._artifacts_anim.setStartValue(0.0)
        self._artifacts_anim.setEndValue(1.0)

        def update_anim(value: float):
            self.setUpdatesEnabled(False)
            try:
                # 1. Update internal panel width first
                curr_panel_w = int(start_w + (end_w - start_w) * value)
                if hasattr(self, "content_with_panels"):
                    self.content_with_panels._artifacts_stack.setFixedWidth(curr_panel_w)

                # 2. Update window width
                curr_win_w = int(start_win_w + (end_win_w - start_win_w) * value)
                self.setFixedWidth(curr_win_w)
            finally:
                self.setUpdatesEnabled(True)

        self._artifacts_anim.valueChanged.connect(update_anim)

        def finalize():
            if hasattr(self, "content_with_panels") and self._current_panels:
                self._current_panels._artifacts_panel.set_expanded(expanded, immediate=True)
                final_w = total_width if expanded else config.ui.panel_toggle_size
                self.content_with_panels._artifacts_stack.setFixedWidth(final_w)

        self._artifacts_anim.finished.connect(finalize)
        self._artifacts_anim.start()

    def _setup_menu_bar(self) -> None:
        """Create and configure the application menu bar."""
        menu_bar = QMenuBar(self)
        menu_bar.setStyleSheet(Styles.MENU_BAR)
        menu_bar.setFocusPolicy(Qt.FocusPolicy.NoFocus)

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
        """Toggle console panel visibility."""
        self.panels_service.toggle_console(checked)

    def _on_toggle_artifacts(self, checked: bool) -> None:
        """Toggle artifacts panel visibility."""
        self.panels_service.toggle_artifacts(checked)

    def _style_title_bar(self) -> None:
        """Apply styling to title bar buttons."""
        button_style = """
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 8px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #4f5b62;
            }
            QPushButton:pressed {
                background-color: #448aff;
            }
        """
        self.ui.minimizePushButton.setStyleSheet(button_style)
        self.ui.maximizePushButton.setStyleSheet(button_style)
        self.ui.closePushButton.setStyleSheet(button_style)
