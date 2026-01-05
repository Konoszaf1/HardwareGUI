"""Action stacked widget with page routing and panel integration.

Provides lazy page creation and routing based on string IDs, with integrated
persistent panels (terminal/artifacts) that stay visible across page switches.
"""

import contextlib
from collections.abc import Callable

from PySide6.QtCore import QItemSelectionModel, QModelIndex, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QHBoxLayout,
    QSplitter,
    QStackedWidget,
    QWidget,
)

from src.config import config
from src.gui.shared_panels_widget import SharedPanelsWidget
from src.gui.styles import Colors
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
        self._shared_panels: SharedPanelsWidget | None = None

    def set_shared_panels(self, panels: SharedPanelsWidget) -> None:
        """Set the shared panels instance to use for all pages."""
        self._shared_panels = panels

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

            # Create the action page directly (no wrapper)
            page = factory()
            idx = self.addWidget(page)

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


class ContentWithPanels(QWidget):
    """Container that wraps the stacked widget with persistent panels.

    Layout:
        [Stacked Widget + Terminal (bottom)] | [Artifacts (right)]

    This widget should be used at the MainWindow level to wrap the stacked widget,
    ensuring panels are persistent and not recreated per page.
    """

    def __init__(
        self,
        stacked_widget: QStackedWidget,
        shared_panels: SharedPanelsWidget,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._stacked = stacked_widget
        self._panels = shared_panels
        self._last_console_height = config.ui.terminal_expanded_height

        # Main horizontal layout (for artifacts panel on the right)
        self._main_layout = QHBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        # Left: splitter for stacked widget + terminal (vertical)

        self._v_splitter = QSplitter(Qt.Vertical)
        self._v_splitter.setHandleWidth(1)
        self._v_splitter.setStyleSheet(
            f"QSplitter::handle {{ background-color: {Colors.BORDER_SUBTLE}; }}"
        )

        self._v_splitter.addWidget(stacked_widget)
        self._v_splitter.addWidget(shared_panels._console_panel)

        # Set stretch factors: stacked widget is flexible, console is fixed-ish but resizable
        self._v_splitter.setStretchFactor(0, 1)
        self._v_splitter.setStretchFactor(1, 0)

        # Prevent terminal from being hidden completely by dragging the handle
        self._v_splitter.setCollapsible(1, False)

        # Right: artifacts
        self._main_layout.addWidget(self._v_splitter, stretch=1)
        self._main_layout.addWidget(shared_panels._artifacts_panel)

        # Connect signals
        shared_panels.console_toggled.connect(self._on_console_toggled)
        self._v_splitter.splitterMoved.connect(self._on_splitter_moved)

        # Initial state: if console is already visible, try to apply height
        if shared_panels.is_console_visible():
            self._apply_console_height(True)

    def showEvent(self, event) -> None:
        """Apply initial sizes when the widget is first shown."""
        super().showEvent(event)
        # Force a small delay to ensure geometry is finalized
        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, lambda: self._apply_console_height(self._panels.is_console_visible()))

    def _on_splitter_moved(self, pos: int, index: int) -> None:
        """Store the console height when resized manually."""
        if index == 1 and self._panels.is_console_visible():
            sizes = self._v_splitter.sizes()
            if len(sizes) > 1:
                self._last_console_height = sizes[1]

    def _on_console_toggled(self, expanded: bool) -> None:
        """Handle console toggle by adjusting splitter sizes."""
        self._apply_console_height(expanded)

    def _apply_console_height(self, expanded: bool) -> None:
        """Update splitter sizes based on expanded state."""
        if not self.isVisible():
            return

        total_height = self._v_splitter.height()
        if total_height <= 0:
            return

        if expanded:
            # Restore last height, ensuring it doesn't take over the whole screen
            h = min(self._last_console_height, total_height - config.ui.terminal_min_height)
            h = max(h, config.ui.terminal_min_height)  # Minimum usable height
            self._v_splitter.setSizes([total_height - h, h])
        else:
            # Collapse to button height (24px)
            self._v_splitter.setSizes(
                [total_height - config.ui.panel_toggle_size, config.ui.panel_toggle_size]
            )

    def set_panels(self, new_panels: SharedPanelsWidget) -> None:
        """Swap panels when hardware is changed."""
        # Disconnect old signals
        with contextlib.suppress(TypeError, RuntimeError):
            self._panels.console_toggled.disconnect(self._on_console_toggled)

        # Remove old panels from layouts
        self._v_splitter.replaceWidget(1, new_panels._console_panel)
        self._main_layout.removeWidget(self._panels._artifacts_panel)
        self._panels._artifacts_panel.setParent(None)

        # Add new panels
        self._panels = new_panels
        self._main_layout.addWidget(new_panels._artifacts_panel)

        # Connect new signals
        new_panels.console_toggled.connect(self._on_console_toggled)

        # Apply current state
        self._apply_console_height(new_panels.is_console_visible())

    @property
    def stacked_widget(self) -> QStackedWidget:
        return self._stacked

    @property
    def panels(self) -> SharedPanelsWidget:
        return self._panels

    @property
    def artifacts_expanded_total_width(self) -> int:
        """Return the width of the artifacts panel including toggle button when expanded."""
        return config.ui.artifacts_expanded_width + config.ui.panel_toggle_size
