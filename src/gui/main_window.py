"""Main Window of the application"""

from typing import List

from PySide6.QtGui import QStandardItemModel, QStandardItem, QColor
from PySide6.QtWidgets import (
    QMainWindow,
    QGraphicsDropShadowEffect,
    QWidget,
)
from PySide6.QtCore import Qt, QPoint

from src.populate_items import ACTIONS, HARDWARE
from src.gui.button_factory import build_toolbuttons
from src.gui.expanding_splitter import ExpandingSplitter
from src.gui.hiding_listview import HidingListView
from src.gui.sidebar_button import SidebarButton
from src.logic.action_dataclass import ActionDescriptor
from src.logic.presenter import ActionsPresenter
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
        self.actions: List[ActionDescriptor] | None = None
        self.presenter: ActionsPresenter | None = None
        self.buttons: List[SidebarButton] = build_toolbuttons(self, HARDWARE)
        self.setup_splitter()

        # Window Specific Setup
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.ui.minimizePushButton.clicked.connect(self.showMinimized)
        self.ui.maximizePushButton.clicked.connect(self.toggle_max_restore)
        self.ui.closePushButton.clicked.connect(self.close)
        self.dragging = False
        self.drag_position = QPoint()
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
        # Add buttons to sidebar
        for button in self.buttons:
            self.sidebar.layout().insertWidget(button.property("order"), button)
            self.splitter.add_button(button)

    def toggle_max_restore(self):
        """Handles maximize button logic"""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def mousePressEvent(self, event):
        """Handle start of dragging behavior after clicking"""
        if event.button() == Qt.MouseButton.LeftButton:
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

    def populate_list_fast(self, model):
        """Quick population using batch processing"""
        items = []
        for i in range(100):  # Large number of items
            item = QStandardItem(f"Item {i}")
            model.appendRow(item)
            items.append(item)
        print("items ready")
