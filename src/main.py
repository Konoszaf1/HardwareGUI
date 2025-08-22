# main.py
import sys

from PySide6.QtGui import QStandardItemModel, QStandardItem, QColor
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QGraphicsDropShadowEffect,
    QSplitter,
    QWidget,
    QListView,
)
from PySide6.QtCore import Qt, QPoint

# Import your generated UI file
from ui_main_window import Ui_MainWindow
import qt_material


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.splitter: QSplitter = None
        self.widget: QWidget = None
        self.list_view: QListView = None
        self.setupSidebar()

        # Window Specific Setup
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.ui.minimizePushButton.clicked.connect(self.showMinimized)
        self.ui.maximizePushButton.clicked.connect(self.toggleMaximizeRestore)
        self.ui.closePushButton.clicked.connect(self.close)
        self.dragging = False
        self.drag_position = QPoint()
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 0)
        self.centralWidget().setGraphicsEffect(shadow)

    def setupSidebar(self) -> QSplitter:
        self.splitter = self.ui.splitter
        # ListView
        self.list_view = self.ui.listView
        model = QStandardItemModel()
        self.list_view.setModel(model)
        self.populate_list_fast(model)

        self.splitter.set_widget(self.ui.widget)
        self.splitter.set_listview(self.list_view)
        # Add buttons to sidebar
        self.splitter.addButton(self.ui.toolButton)
        self.splitter.addButton(self.ui.toolButton_3)
        self.splitter.addButton(self.ui.toolButton_2)

    def toggleMaximizeRestore(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_position = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.dragging:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    qt_material.apply_stylesheet(app, "dark_amber.xml")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
