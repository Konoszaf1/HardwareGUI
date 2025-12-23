from collections.abc import Callable
from PySide6.QtCore import Qt, QModelIndex, Signal, Slot, QItemSelectionModel
from PySide6.QtWidgets import QWidget, QStackedWidget

from src.logging_config import get_logger

logger = get_logger(__name__)


class ActionStackedWidget(QStackedWidget):
    """A pragmatic subclass of QStackedWidget that routes by string IDs.

    Features
    --------
    - Map arbitrary string IDs to page *factories* (lazy creation)
    - Switch by ID: calls page.leave() on old page, page.enter() on new page
    - Signal currentPageChanged(id, widget)
    - Convenience: bind_to_selection(selectionModel, role) to route from a QListView/QTreeView
    - get_page(id) to access the live page instance (if created)
    - unregister/clear APIs for cleanup
    """

    currentPageIdChanged = Signal(str, QWidget)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.factories: dict[str, Callable[[], QWidget]] = {}
        self.ids_by_index: dict[int, str] = {}
        self.index_by_id: dict[str, int] = {}

    # ---- Registration ----
    def register_page(self, page_id: str, factory: Callable[[], QWidget]) -> None:
        """Register a page factory for an ID. Does not instantiate immediately."""
        self.factories[page_id] = factory

    def unregister_page(self, page_id: str) -> None:
        idx = self.index_by_id.get(page_id)
        if idx is not None:
            w = self.widget(idx)
            if w is not None:
                self.removeWidget(w)
                w.deleteLater()
            self.ids_by_index.pop(idx, None)
            self.index_by_id.pop(page_id, None)
        self.factories.pop(page_id, None)

    def clear(self) -> None:
        """Remove all pages and factories."""
        for i in reversed(range(self.count())):
            w = self.widget(i)
            if w is not None:
                self.removeWidget(w)
                w.deleteLater()
        self.factories.clear()
        self.ids_by_index.clear()
        self.index_by_id.clear()

    def bind_to_selection(
        self, selection_model: QItemSelectionModel, role: int = Qt.ItemDataRole.UserRole
    ) -> None:
        """Route QListView/QTreeView's currentChanged to show the corresponding page.

        The model is expected to store the router page_id at 'role'.
        """
        selection_model.currentChanged.connect(
            lambda cur, prev: self.on_current_changed(cur, prev, role)
        )

    def bind_to_listview(self, list_view, role: int = Qt.UserRole) -> None:
        """Bind after setting the model on a QListView/QTreeView."""
        sel = getattr(list_view, "selectionModel", None)
        sel = sel() if callable(sel) else sel
        if sel is not None:
            self.bind_to_selection(sel, role)

    @Slot(QModelIndex, QModelIndex)
    def on_current_changed(self, current: QModelIndex, previous: QModelIndex, role: int) -> None:
        """Change the shown page when the selection changes."""
        if not current.isValid():
            return

        page_id = current.data(role)
        if isinstance(page_id, str):
            self.show_page(page_id)

    def show_page(self, page_id: str) -> None:
        """Show (and lazily create) the page mapped to page_id."""
        if page_id not in self.factories and page_id not in self.index_by_id:
            return

        # Create page if not yet created, then show
        idx = self.index_by_id.get(page_id)
        if idx is None:
            factory = self.factories.get(page_id)
            if factory is None:
                return
            w = factory()
            idx = self.addWidget(w)
            self.ids_by_index[idx] = page_id
            self.index_by_id[page_id] = idx

        self.setCurrentIndex(idx)
        cur_w = self.currentWidget()
        logger.debug(f"Switched to page: {page_id} -> {cur_w}")
        if cur_w is not None and hasattr(cur_w, "enter"):
            cur_w.show()
        self.currentPageIdChanged.emit(page_id, cur_w)

    def get_page(self, page_id: str) -> QWidget | None:
        idx = self.index_by_id.get(page_id)
        if idx is None:
            return None
        return self.widget(idx)
