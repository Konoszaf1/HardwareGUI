from PySide6.QtCore import QSize
from PySide6.QtWidgets import QSizePolicy, QListView


class HidingListView(QListView):

    def __init__(self, child, parent=None):
        super().__init__(parent)
        self.setMinimumSize(0, 0)
        sp = self.sizePolicy()
        sp.setHorizontalPolicy(QSizePolicy.Expanding)
        sp.setVerticalPolicy(QSizePolicy.Expanding)
        self.setSizePolicy(sp)

    def minimumSizeHint(self) -> QSize:
        return QSize(0, 0)
