"""Main Window of the application"""

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QAction, QColor
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
from src.gui.sidebar_button import SidebarButton
from src.gui.status_bar_service import StatusBarService
from src.gui.styles import Styles
from src.logic.action_dataclass import ActionDescriptor
from src.logic.presenter import ActionsPresenter
from src.populate_items import ACTIONS, HARDWARE
from src.ui_main_window import Ui_MainWindow


class MainWindow(QMainWindow):
    """Frameless main window that binds the Designer-generated Ui_MainWindow
    to a QMainWindow.

    This class provides custom chrome (frameless, translucent background),
    a title bar with window controls, mouse-driven window dragging,
    and a central ExpandingSplitter with a sidebar of exclusive
    SidebarButtons and a HidingListView. The list view’s model is created
    and populated on startup, and a drop shadow is applied to the central
    widget.

    Attributes: ui (Ui_MainWindow): Compiled UI exposing widgets from the
    .ui file. splitter (ExpandingSplitter | None): Splitter hosting the
    sidebar and list view. list_view (HidingListView | None): List view
    shown in the splitter; model is set up in code. dragging (bool):
    Window-drag state flag. drag_position (QPoint): Top-left offset used
    during window dragging.

    Methods: setup_splitter(): Connects sidebar buttons and list view to the
    splitter; seeds the model.
    toggleMaximizeRestore(): Toggles between maximized and normal window
    states.
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
        self.setup_splitter()
        self.presenter.connect_actions_and_stacked_view(self.actions)

        # Status bar setup - ensure visible with frameless window
        self.ui.statusbar.setStyleSheet(Styles.STATUS_BAR)
        self.ui.statusbar.setVisible(True)
        self.ui.statusbar.setSizeGripEnabled(False)  # No grip for frameless window
        StatusBarService.init(self.ui.statusbar)

        # Connect scope verification to status bar (global, not per-page)
        self.presenter.service.scopeVerified.connect(self._on_scope_status_changed)

        # Menu bar setup
        self._setup_menu_bar()

        # Title bar styling
        self._style_title_bar()

        # Window Specific Setup
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
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 0)
        self.centralWidget().setGraphicsEffect(shadow)

    def setup_splitter(self) -> None:
        """Populate the splitter with the required widgets"""
        self.splitter = self.ui.splitter
        # ListView
        self.list_view = self.ui.listView
        self.sidebar = self.ui.sidebar
        self.actions = ACTIONS
        self.presenter = ActionsPresenter(self, self.buttons, self.actions)
        self.splitter.set_sidebar(self.ui.sidebar)
        self.splitter.set_listview(self.list_view)
        # Add buttons to sidebar and track hardware selection
        for button in self.buttons:
            self.sidebar.layout().insertWidget(button.property("order"), button)
            self.splitter.add_button(button)
            # Track hardware selection for status bar
            button.toggled.connect(
                lambda checked, btn=button: checked
                and self._on_hardware_selected(btn.property("id"))
            )

    def toggle_max_restore(self):
        """Handles maximize button logic"""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def mousePressEvent(self, event):
        """Handle start of dragging behavior after clicking"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Dragging operation and fallback to old style dragging if first one fails
            if self.windowHandle().startSystemMove():
                return
            else:
                self.dragging = True
                self.drag_position = (
                    event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                )
            event.accept()

    def mouseMoveEvent(self, event):
        """Handle moving the window when clicking & dragging"""
        if event.buttons() == Qt.MouseButton.LeftButton and self.dragging:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        """Finalize dragging behavior logic"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            event.accept()

    def _on_scope_status_changed(self, verified: bool) -> None:
        """Handle global scope verification status changes."""
        StatusBarService.instance().set_scope_connected(connected=verified)
        if verified:
            StatusBarService.instance().set_ready()

    def _on_hardware_selected(self, hardware_id: int) -> None:
        """Handle hardware selection changes for status bar state."""
        StatusBarService.instance().set_active_hardware(hardware_id)

    def _setup_menu_bar(self) -> None:
        """Create and configure the application menu bar."""
        menu_bar = QMenuBar(self)
        menu_bar.setStyleSheet(Styles.MENU_BAR)
        menu_bar.setFocusPolicy(Qt.FocusPolicy.NoFocus)

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
        menu_bar.addMenu(QMenu("View", self))
        menu_bar.addMenu(QMenu("Help", self))

        self.ui.titleBar.insertWidget(0, menu_bar)

    def _on_settings(self) -> None:
        pass

    def _style_title_bar(self) -> None:
        """Apply consistent styling to title bar buttons (qt-material dark_blue theme)."""
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
