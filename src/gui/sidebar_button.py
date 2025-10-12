"""Custom Button Type to handle expansion and collapse in the sidebar"""

from PySide6.QtWidgets import QToolButton, QSizePolicy
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve


class SidebarButton(QToolButton):
    """Custom implementation consists of expanding and collapsing animation"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._full_text = ""
        self.setIconSize(QSize(24, 24))
        self.size_policy = self.create_size_policy()
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.setCheckable(True)
        self.setChecked(False)
        self.setAutoExclusive(True)
        self.setAutoRaise(False)
        self.setSizePolicy(self.size_policy)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._original_text = None
        # Animation for smooth text appearance
        self.animation = QPropertyAnimation(self, b"minimumWidth")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)

    def set_collapsed(self, collapsed):
        """Start expansion and collapse animations"""
        if collapsed:
            super().setText("")
            self.animation.setStartValue(self.width())
            self.animation.setEndValue(50)
            self.animation.start()
            self.animation.finished.connect(self.finish_collapse_animation)
            self.animation.stateChanged.connect(self.finish_collapse_animation)
        else:
            self.animation.setStartValue(self.width())
            self.animation.start()
            self.animation.finished.connect(self.finish_expand_animation)

    def finish_collapse_animation(self):
        """Remove text from button to only show icon"""
        super().setText("")

    def finish_expand_animation(self):
        """After full expansion show button text"""
        super().setText(f" {self._original_text}")

    def create_size_policy(self):
        """Custom size policy that enables resizing"""
        size_policy = QSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )
        size_policy.setHorizontalStretch(0)
        size_policy.setVerticalStretch(0)
        size_policy.setHeightForWidth(self.parent().hasHeightForWidth())
        return size_policy

    def setText(self, text):
        """Handle setting and unsetting and storing button text"""
        if not self._original_text:
            self._original_text = text
        super().setText(text)
