# sidebar_button.py
from PySide6.QtWidgets import QToolButton
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve


class SidebarButton(QToolButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._full_text = ""
        self.setIconSize(QSize(24, 24))
        self.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.setCheckable(True)
        self._original_text = ""

        # Animation for smooth text appearance
        self._animation = QPropertyAnimation(self, b"minimumWidth")
        self._animation.setDuration(200)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)

    def setCollapsed(self, collapsed):
        if collapsed:
            self.setToolButtonStyle(Qt.ToolButtonIconOnly)
            super().setText("")
            self._animation.setStartValue(self.width())
            self._animation.setEndValue(50)
            self._animation.start()
        else:
            self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            super().setText(f" {self._original_text}")
            self._animation.setStartValue(self.width())
            self._animation.setEndValue(200)
            self._animation.start()

    def setText(self, text):
        self._original_text = text
        super().setText(text)
