from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QListView, QPushButton

import icons_rc


HARDWARE = [
    ("KEYBOARD", ":/icons/keyboard.png"),
    ("SCANNER", ":/icons/scanner-image.png"),
    ("SCREEN", ":/icons/screen.png"),
]


class ActionsListView(QListWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        ACTIONS = ["flash", "initialize", "smoke"]
        for path in ACTIONS:
            self.addItem(QListWidgetItem(path))

        self.setResizeMode(QListView.Adjust)
        self.setUniformItemSizes(True)
        self.setCurrentRow(0)
        self.currentRowChanged.connect(self.sidebar_changed)
        self.setWrapping(False)
        # self.resizeEvent = update_grid

    def sidebar_changed(self, row: int):
        print("Selected hardware:", HARDWARE[row][0])
