"""Custom QListView subclass that hides when collapsed by returning a zero hint
size.
"""

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QListView, QSizePolicy, QWidget


class HidingListView(QListView):
    """QListView subclass that can shrink to zero width within a splitter."""

    def __init__(self, child: QWidget | None = None, parent: QWidget | None = None):
        """Initialize the list view with expanding policies.

        Args:
            child (QWidget | None): Unused parameter kept for API parity with the UI loader.
            parent (QWidget | None): Optional parent widget that owns the list view.
        """
        super().__init__(parent)
        self.setMinimumSize(0, 0)
        self.setMinimumWidth(150)  # Default minimum width for actions list
        self.child = child
        # Use Preferred so it sizes to content, not greedy expansion
        size_policy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.setSizePolicy(size_policy)

    def minimumSizeHint(self) -> QSize:
        """Override minimum SizeHint to Enable smooth animation while collapsing.

        Returns:
            QSize: Zero size hint.
        """
        return QSize(0, 0)

    def sizeHint(self) -> QSize:
        """Calculate size hint based on content width.

        Returns:
            QSize: Calculated optimal size.
        """
        if not self.model():
            return super().sizeHint()

        # Calculate width needed for longest item + padding
        max_width = 0
        fm = self.fontMetrics()
        for row in range(self.model().rowCount()):
            index = self.model().index(row, 0)
            text = index.data(Qt.ItemDataRole.DisplayRole)
            if text:
                width = fm.horizontalAdvance(text)
                max_width = max(max_width, width)

        # Add padding for margins
        padding = 30
        return QSize(max_width + padding, super().sizeHint().height())
