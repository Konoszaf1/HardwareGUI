"""Custom QSplitter Widget to handle the sidebar expansion and collapse"""

from PySide6.QtWidgets import QWidget, QSplitter, QListView
from PySide6.QtCore import (
    QTimer,
    QEvent,
    QEasingCurve,
    QVariantAnimation,
    QAbstractAnimation, QPropertyAnimation,
)


class ExpandingSplitter(QSplitter):
    """
    An expanding sidebar that shows button text over the side list on hover
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._collapsed_width = 30
        self._expanded_width = 250
        self.setMinimumWidth(self._collapsed_width)
        self.setMaximumWidth(self._expanded_width)
        self.buttons = []
        self._is_expanded = False
        self.widget: QWidget | None = None
        self.listview: QListView | None = None
        self.sidebar: QWidget | None = None
        self.parent().installEventFilter(self)
        self.setHandleWidth(0)
        self.setContentsMargins(0, 0, 0, 0)
        # Button's description will expand after timer timeout
        self.expand_timer = QTimer(self)
        self.expand_timer.setSingleShot(True)
        self.expand_timer.setInterval(350)
        self.expand_timer.timeout.connect(self.expand)
        # Button's description will collapse after timer timeout
        self.collapse_timer = QTimer()
        self.collapse_timer.setSingleShot(True)
        self.collapse_timer.timeout.connect(self.collapse)
        # Animation for expanding
        self._animation = QVariantAnimation(self)
        self._animation.setDuration(500)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)

    def set_sidebar(self, sidebar: QWidget):
        """
        Sidebar attribute setter
        :param sidebar: The sidebar Widget that contains all SidebarButtons
        """
        self.sidebar = sidebar
        self.setCollapsible(0, False)

    def set_listview(self, listview: QListView):
        """
        ListView attribute setter
        :param listview: The QListView Widget that contains all actions
        """
        self.listview = listview

    def add_button(self, button):
        """Add a button to the sidebar"""
        self.buttons.append(button)
        button.set_collapsed(True)
        # Install event filter on the button
        button.installEventFilter(self)

    def eventFilter(self, obj, event):
        """Handle hover events for the sidebar and its buttons"""
        if event.type() == QEvent.Type.HoverEnter:
            if obj in self.buttons or obj == self:
                self.handle_hover_enter()
                return False
        elif event.type() in (QEvent.Type.HoverLeave, QEvent.Type.MouseButtonPress):
            if obj in self.buttons or obj == self:
                self.handle_hover_leave()
                return False
        elif obj == self.parent() and event.type() == QEvent.Type.Resize:
            # Collapse buttons when resizing top application
            self.collapse()

        return super().eventFilter(obj, event)

    def handle_hover_enter(self):
        """Stops collapse timer if running and starts expand timer"""
        self.collapse_timer.stop()
        if not self._is_expanded:
            self.expand_timer.start()

    def handle_hover_leave(self):
        """Stops expand timer if running and starts collapse timer"""
        self.expand_timer.stop()
        if self._animation.state() == QAbstractAnimation.State.Running:
            self._animation.stop()
        self.collapse_timer.start(200)

    def expand(self):
        """Expand the sidebar and hide the list view"""
        if self._is_expanded:
            return
        self._animation.setStartValue(self.sizes()[1])
        self._animation.setEndValue(0)
        self._animation.valueChanged.connect(lambda v: self.expand_sidebar(v))
        self._animation.start()
        # Update button states to show text
        for button in self.buttons:
            button.set_collapsed(False)

    def expand_sidebar(self, value):
        """Handle resizing of the splitter for expansion animation"""
        self.setSizes([int(self.width() - value), int(value)])
        if value == 0:
            self._is_expanded = True

    def collapse_sidebar(self, value):
        """Handle resizing of the splitter for expansion animation"""
        self.setSizes([int(self.width() - value), int(value)])


    def collapse(self):
        """Collapse the sidebar and show the list view"""
        self._animation.setStartValue(self.sizes()[1])
        self._animation.setEndValue(self.width()-self._collapsed_width)
        self._animation.valueChanged.connect(lambda v: self.expand_sidebar(v))
        self._animation.start()
        self._is_expanded = False

        # Update button states to hide text
        for button in self.buttons:
            button.set_collapsed(True)
