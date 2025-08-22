# expanding_sidebar.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSplitter, QListView
from PySide6.QtCore import Qt, QTimer, QEvent, QSize
from PySide6.QtGui import QEnterEvent


class ExpandingSidebar(QSplitter):
    """
    An expanding sidebar that shows text on hover and controls splitter behavior
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._collapsed_width = 30
        self._expanded_width = 250
        self._animation_duration = 120
        self._is_expanded = False
        self.widget: QWidget = None
        self.listview: QListView = None

        self._collapse_timer = QTimer()
        self._collapse_timer.setSingleShot(True)
        self._collapse_timer.timeout.connect(self.collapse)

        self.setMinimumWidth(self._collapsed_width)
        self.setMaximumWidth(self._expanded_width)
        self._buttons = []

    def set_widget(self, widget: QWidget):
        self.widget = widget

    def set_listview(self, listview: QListView):
        self.listview = listview

    def addButton(self, button):
        """Add a button to the sidebar"""
        self._buttons.append(button)
        button.setCollapsed(True)
        # Install event filter on the button
        button.installEventFilter(self)

    def eventFilter(self, obj, event):
        """Handle hover events for the sidebar and its buttons"""
        if isinstance(event, QEnterEvent):
            if obj in self._buttons or obj == self:
                self._handle_hover_enter()
                return True
        elif event.type() == QEvent.Leave:
            if obj in self._buttons or obj == self:
                self._handle_hover_leave()
                return True

        return super().eventFilter(obj, event)

    def _handle_hover_enter(self):
        """Handle mouse entering the sidebar or buttons"""
        self._collapse_timer.stop()
        if not self._is_expanded:
            self.expand()

    def _handle_hover_leave(self):
        """Handle mouse leaving the sidebar or buttons"""
        self._collapse_timer.start(100)

    def expand(self):
        """Expand the sidebar and hide the list view"""
        if self._is_expanded:
            return
        self._is_expanded = True

        # Store the list view size before hiding it
        if hasattr(self, "_list_view_size"):
            self._list_view_size = self.sizes()[1]

        # Hide the list view by setting its size to 0
        self.setSizes([self._expanded_width, 0])

        # Update button states to show text
        for button in self._buttons:
            button.setCollapsed(False)

    def collapse(self):
        """Collapse the sidebar and show the list view"""
        if not self._is_expanded:
            return

        self._is_expanded = False

        # Restore the list view to its previous size or use a default
        list_view_size = getattr(self, "_list_view_size", 200)
        self.setSizes([self._collapsed_width, list_view_size])

        # Update button states to hide text
        for button in self._buttons:
            button.setCollapsed(True)

    def isExpanded(self):
        return self._is_expanded
