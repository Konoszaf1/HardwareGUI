# sidebar_demo.py
import sys
from PySide6.QtCore import (
    QPropertyAnimation,
    QEasingCurve,
    QParallelAnimationGroup,
    QTimer,
    Qt,
    QSize,
    QAbstractAnimation,
)
from PySide6.QtGui import QCursor, QStandardItemModel, QStandardItem
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QMainWindow,
    QHBoxLayout,
    QVBoxLayout,
    QListView,
    QToolButton,
    QSizePolicy,
)


class Sidebar(QWidget):
    def __init__(
        self, collapsed_w=50, expanded_w=240, list_original_w=400, parent=None
    ):
        super().__init__(parent)
        self._collapsed_w = collapsed_w
        self._expanded_w = expanded_w
        self._list_original_w = list_original_w

        self._collapsed = True
        self._buttons = []

        # fixed size policy so parent layout does not stretch this column
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.setMaximumWidth(self._collapsed_w)
        self.setMinimumWidth(self._collapsed_w)

        self.vlay = QVBoxLayout(self)
        self.vlay.setContentsMargins(0, 0, 0, 0)
        self.vlay.setSpacing(0)

        # animation refs
        self.left_anim = None
        self.right_anim = None
        self.group = None

        self._listview = None

    def set_listview(self, lv: QListView):
        self._listview = lv
        # ensure sensible starting max width for list
        self._listview.setMaximumWidth(self._list_original_w)

    def add_button(self, btn: QToolButton):
        btn.setToolButtonStyle(Qt.ToolButtonIconOnly)
        btn.setFixedHeight(48)
        btn.setIconSize(QSize(20, 20))
        self.vlay.addWidget(btn)
        self._buttons.append(btn)
        btn.show()

    def enterEvent(self, event):
        if self._collapsed:
            self.expand()
        super().enterEvent(event)

    def leaveEvent(self, event):
        # short delay to avoid flicker when moving between children
        QTimer.singleShot(80, self._maybe_collapse)
        super().leaveEvent(event)

    def _maybe_collapse(self):
        # collapse only if cursor is outside this widget
        if self.rect().contains(self.mapFromGlobal(QCursor.pos())):
            return
        self.collapse()

    def expand(self):
        if not self._listview or not self._collapsed:
            return

        # stop any running animations
        if self.group and self.group.state() == QAbstractAnimation.Running:
            self.group.stop()

        left_start = self.width() or self._collapsed_w
        left_end = self._expanded_w

        right_start = self._listview.width() or self._list_original_w
        right_end = 0

        self.left_anim = QPropertyAnimation(self, b"maximumWidth", self)
        self.left_anim.setStartValue(left_start)
        self.left_anim.setEndValue(left_end)
        self.left_anim.setDuration(260)
        self.left_anim.setEasingCurve(QEasingCurve.InOutQuad)

        self.right_anim = QPropertyAnimation(self._listview, b"maximumWidth", self)
        self.right_anim.setStartValue(right_start)
        self.right_anim.setEndValue(right_end)
        self.right_anim.setDuration(260)
        self.right_anim.setEasingCurve(QEasingCurve.InOutQuad)

        # show text beside icon
        for b in self._buttons:
            b.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        self._collapsed = False

        self.group = QParallelAnimationGroup(self)
        self.group.addAnimation(self.left_anim)
        self.group.addAnimation(self.right_anim)
        self.group.start()

    def collapse(self):
        if self._collapsed:
            return

        # prevent collapse if cursor back inside
        if self.rect().contains(self.mapFromGlobal(QCursor.pos())):
            return

        if self.group and self.group.state() == QAbstractAnimation.Running:
            self.group.stop()

        left_start = self.width()
        left_end = self._collapsed_w

        right_start = self._listview.width() or 0
        right_end = self._list_original_w

        self.left_anim = QPropertyAnimation(self, b"maximumWidth", self)
        self.left_anim.setStartValue(left_start)
        self.left_anim.setEndValue(left_end)
        self.left_anim.setDuration(260)
        self.left_anim.setEasingCurve(QEasingCurve.InOutQuad)

        self.right_anim = QPropertyAnimation(self._listview, b"maximumWidth", self)
        self.right_anim.setStartValue(right_start)
        self.right_anim.setEndValue(right_end)
        self.right_anim.setDuration(260)
        self.right_anim.setEasingCurve(QEasingCurve.InOutQuad)

        self.group = QParallelAnimationGroup(self)
        self.group.addAnimation(self.left_anim)
        self.group.addAnimation(self.right_anim)
        self.group.finished.connect(self._reset_buttons)
        self.group.start()

    def _reset_buttons(self):
        for b in self._buttons:
            b.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self._collapsed = True


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sidebar demo")
        central = QWidget(self)
        self.setCentralWidget(central)

        h = QHBoxLayout(central)
        h.setContentsMargins(6, 6, 6, 6)
        h.setSpacing(6)

        # sidebar and list view
        self.sidebar = Sidebar(collapsed_w=50, expanded_w=220, list_original_w=360)
        h.addWidget(self.sidebar)

        self.listview = QListView()
        self.listview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.listview.setMaximumWidth(360)
        h.addWidget(self.listview, 1)

        # populate list quickly
        model = QStandardItemModel()
        for i in range(60):
            model.appendRow(QStandardItem(f"Item {i}"))
        self.listview.setModel(model)

        # add buttons
        for name in ("One", "Two", "Three"):
            btn = QToolButton()
            btn.setText(name)
            self.sidebar.add_button(btn)

        self.sidebar.set_listview(self.listview)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.resize(800, 600)
    w.show()
    sys.exit(app.exec())
