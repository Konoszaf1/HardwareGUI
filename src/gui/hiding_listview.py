"""Custom QListView Wrapper that hides when collapsed by returning a zero hint
size.
"""

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QSizePolicy, QListView


class HidingListView(QListView):
    """QListView variant that can shrink to zero width within a splitter."""

    def __init__(self, child, parent=None):
        """Initialize the list view with expanding policies.

        Args:
            child: Unused parameter kept for API parity with the UI loader.
            parent: Optional parent widget that owns the list view.
        """
        super().__init__(parent)
        self.setMinimumSize(0, 0)
        self.child = child
        size_policy = self.sizePolicy()
        size_policy.setHorizontalPolicy(QSizePolicy.Policy.Expanding)
        size_policy.setVerticalPolicy(QSizePolicy.Policy.Expanding)
        self.setSizePolicy(size_policy)

    def minimumSizeHint(self) -> QSize:
        """Override minimum SizeHint to Enable smooth animation while
        collapsing to 0 width.
        """
        return QSize(0, 0)
