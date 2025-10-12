# split_anim_zero_floor.py
from PySide6.QtCore import QEasingCurve, QVariantAnimation, QTimer, QSize
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QSplitter,
    QPushButton,
    QVBoxLayout,
    QTextEdit,
    QSizePolicy,
)
import sys


class ZeroMin(QWidget):
    """Wrapper to guarantee zero minimum width/height regardless of child hints."""

    def __init__(self, child: QWidget, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(child)
        self.setMinimumSize(0, 0)
        sp = self.sizePolicy()
        sp.setHorizontalPolicy(QSizePolicy.Expanding)
        sp.setVerticalPolicy(QSizePolicy.Expanding)
        self.setSizePolicy(sp)

    def minimumSizeHint(self) -> QSize:
        return QSize(0, 0)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Splitter → 0 px (no 50px floor)")

        self.splitter = QSplitter()  # Horizontal
        self.splitter.setOpaqueResize(True)
        self.splitter.setChildrenCollapsible(True)
        self.splitter.setCollapsible(0, True)  # left pane collapsible
        self.splitter.setCollapsible(1, True)

        # Real content
        left_content = QTextEdit("Left content")
        right_content = QTextEdit("Right content")

        # Wrap left to kill minimums from inner widgets/layouts
        left = ZeroMin(left_content)
        right = ZeroMin(right_content)

        # Also explicitly zero mins on inner content (belt-and-suspenders)
        left_content.setMinimumSize(0, 0)
        right_content.setMinimumSize(0, 0)

        self.splitter.addWidget(left)
        self.splitter.addWidget(right)

        # Initial sizes
        self.splitter.setSizes([240, 560])

        # Controls
        btnCollapse = QPushButton("Collapse left → 0")
        btnExpand = QPushButton("Expand left → 240")
        btnCollapse.clicked.connect(lambda: self.animate_left_to(0, 700))
        btnExpand.clicked.connect(lambda: self.animate_left_to(240, 700))

        wrap = QWidget()
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)  # no outer floors
        lay.addWidget(self.splitter)
        lay.addWidget(btnCollapse)
        lay.addWidget(btnExpand)
        self.setCentralWidget(wrap)

        self._anim = None
        QTimer.singleShot(0, self._set_baseline)

    def _set_baseline(self):
        total = max(1, self.splitter.width())
        left = 240
        self.splitter.setSizes([left, max(1, total - left)])

    def animate_left_to(self, end_left_px: int, duration_ms: int):
        sizes = self.splitter.sizes()
        start_left = sizes[0]
        total = sum(sizes)
        end_left = max(0, min(end_left_px, total))

        if self._anim:
            self._anim.stop()
        self._anim = QVariantAnimation(self)
        self._anim.setStartValue(float(start_left))
        self._anim.setEndValue(float(end_left))
        self._anim.setDuration(duration_ms)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)

        # Handle index 1 = before second widget
        self._anim.valueChanged.connect(lambda v: self.splitter.moveSplitter(int(v), 1))
        self._anim.finished.connect(
            lambda: self.splitter.moveSplitter(int(end_left), 1)
        )
        self._anim.start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.resize(800, 500)
    w.show()
    sys.exit(app.exec())
