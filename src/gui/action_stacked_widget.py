from typing import Callable, Dict, Optional
from PySide6.QtCore import Qt, QModelIndex, QObject, Signal, Slot
from PySide6.QtWidgets import QWidget, QStackedWidget


class ActionStackedWidget(QStackedWidget):
    """A pragmatic subclass of QStackedWidget that routes by string IDs.

    Features
    --------
    - Map arbitrary string IDs to page *factories* (lazy creation)
    - Switch by ID: calls page.leave() on the old page and page.enter() on the new page if they exist
    - Signal currentPageChanged(id, widget)
    - Convenience: bind_to_selection(selectionModel, role) to route from a QListView/QTreeView
    - get_page(id) to access the live page instance (if created)
    - unregister/clear APIs for cleanup
    """

    currentPageIdChanged = Signal(str, QWidget)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.factories: Dict[str, Callable[[], QWidget]] = {}
        self.ids_by_index: Dict[int, str] = {}
        self.index_by_id: Dict[str, int] = {}

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

    # ---- Selection binding ----
    def bind_to_selection(self, selection_model: QObject, role: int = Qt.UserRole) -> None:
        """Route QListView/QTreeView's currentChanged to show corresponding page.

        The model is expected to store the router page_id at `role`.
        """
        # selection_model is a QItemSelectionModel, but keep type loosely typed for import-lightness.
        selection_model.currentChanged.connect(lambda cur, prev: self.on_current_changed(cur, prev, role))

    def bind_to_listview(self, list_view, role: int = Qt.UserRole) -> None:
        """Convenience: bind after you've set the model on a QListView/QTreeView.
        Example:
            list_view.setModel(proxy)
            router.bind_to_listview(list_view, role=ActionModel.id_role)
        """
        print(f"Bound listview to role {role}")
        sel = getattr(list_view, "selectionModel", None)
        sel = sel() if callable(sel) else sel
        if sel is not None:
            self.bind_to_selection(sel, role)

    @Slot(QModelIndex, QModelIndex)
    def on_current_changed(self, current: QModelIndex, previous: QModelIndex, role: int) -> None:
        print("Invoked")
        if not current.isValid():
            return

        page_id = current.data(role)
        print(f"Requested for page id {page_id}")
        if isinstance(page_id, str):
            self.show_page(page_id)

    # ---- Page switching ----
    def show_page(self, page_id: str) -> None:
        """Show (and lazily create) the page mapped to page_id."""
        print(f"Called for page id {page_id}")
        if page_id not in self.factories and page_id not in self.index_by_id:
            # no factory and not already created -> nothing to show
            return

        # Ensure page exists
        idx = self.index_by_id.get(page_id)
        if idx is None:
            factory = self.factories.get(page_id)
            if factory is None:
                return
            w = factory()
            idx = self.addWidget(w)
            self.ids_by_index[idx] = page_id
            self.index_by_id[page_id] = idx

        # Switch
        self.setCurrentIndex(idx)
        cur_w = self.currentWidget()
        print(f"current widget {cur_w}")
        if cur_w is not None and hasattr(cur_w, "enter"):
            try:
                cur_w.show()  # type: ignore[attr-defined]
            except Exception:
                pass
        self.currentPageIdChanged.emit(page_id, cur_w)

    def get_page(self, page_id: str) -> Optional[QWidget]:
        idx = self.index_by_id.get(page_id)
        if idx is None:
            return None
        return self.widget(idx)