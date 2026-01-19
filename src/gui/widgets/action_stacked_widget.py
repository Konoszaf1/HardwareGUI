"""Action stacked widget with page routing and panel integration.

Provides lazy page creation and routing based on string IDs, with integrated
persistent panels (terminal/artifacts) that stay visible across page switches.
"""

import contextlib
from collections.abc import Callable

from PySide6.QtCore import (
    QItemSelectionModel,
    QModelIndex,
    Qt,
    QVariantAnimation,
    Signal,
    Slot,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QSplitter,
    QStackedWidget,
    QWidget,
)

from src.config import config
from src.gui.shared_panels_widget import SharedPanelsWidget
from src.gui.styles import Colors
from src.gui.utils.animation import animate_value
from src.logging_config import get_logger

logger = get_logger(__name__)


class ActionStackedWidget(QStackedWidget):
    """A pragmatic subclass of QStackedWidget that routes by string IDs.

    Features:
    - Map arbitrary string IDs to page *factories* (lazy creation)
    - Switch by ID: calls page.leave() on old page, page.enter() on new page
    - Signal currentPageChanged(id, widget)
    - Convenience: bind_to_selection(selectionModel, role) to route from a QListView
    - get_page(id) to access the live page instance (if created)
    - unregister/clear APIs for cleanup

    Attributes:
        currentPageIdChanged (Signal): Signal emitted when the current page changes (id, widget).
    """

    currentPageIdChanged = Signal(str, QWidget)

    def __init__(self, parent: QWidget | None = None):
        """Initialize the ActionStackedWidget.

        Args:
            parent (QWidget | None): Parent widget.
        """
        super().__init__(parent)
        self.factories: dict[str, Callable[[], QWidget]] = {}
        self.ids_by_index: dict[int, str] = {}
        self.index_by_id: dict[str, int] = {}
        self._shared_panels: SharedPanelsWidget | None = None

    def set_shared_panels(self, panels: SharedPanelsWidget) -> None:
        """Set the shared panels instance to use for all pages.

        Args:
            panels (SharedPanelsWidget): The shared panels instance.
        """
        self._shared_panels = panels

    # ---- Registration ----
    def register_page(self, page_id: str, factory: Callable[[], QWidget]) -> None:
        """Register a page factory for an ID. Does not instantiate immediately.

        Args:
            page_id (str): Unique ID for the page.
            factory (Callable[[], QWidget]): Function that returns the page widget.
        """
        self.factories[page_id] = factory

    def unregister_page(self, page_id: str) -> None:
        """Unregister a page and remove it if instantiated.

        Args:
            page_id (str): The ID of the page to unregister.
        """
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
        """Route QListView currentChanged to show the corresponding page.

        The model is expected to store the router page_id at 'role'.

        Args:
            selection_model (QItemSelectionModel): The selection model to monitor.
            role (int): The data role containing the page ID.
        """
        selection_model.currentChanged.connect(
            lambda cur, prev: self.on_current_changed(cur, prev, role)
        )

    def bind_to_listview(self, list_view, role: int = Qt.ItemDataRole.UserRole) -> None:
        """Bind after setting the model on a QListView/QTreeView.

        Args:
            list_view (QAbstractItemView): The view to bind to.
            role (int): The data role containing the page ID.
        """
        sel = getattr(list_view, "selectionModel", None)
        sel = sel() if callable(sel) else sel
        if sel is not None:
            self.bind_to_selection(sel, role)

    @Slot(QModelIndex, QModelIndex)
    def on_current_changed(self, current: QModelIndex, previous: QModelIndex, role: int) -> None:
        """Change the shown page when the selection changes.

        Args:
            current (QModelIndex): The new current index.
            previous (QModelIndex): The previous current index.
            role (int): The role to query for page ID.
        """
        if not current.isValid():
            return

        page_id = current.data(role)
        if isinstance(page_id, str):
            self.show_page(page_id)

    def show_page(self, page_id: str) -> None:
        """Show (and lazily create) the page mapped to page_id.

        Args:
            page_id (str): The ID of the page to show.
        """
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
        """Get the instantiated page widget for an ID.

        Args:
            page_id (str): The page ID.

        Returns:
            QWidget | None: The page widget if it exists, else None.
        """
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
        """Initialize the container.

        Args:
            stacked_widget (QStackedWidget): The main content stack.
            shared_panels (SharedPanelsWidget): The shared panels source.
            parent (QWidget | None): Parent widget.
        """
        super().__init__(parent)
        self._stacked = stacked_widget
        self._panels = shared_panels
        self._last_console_height = config.ui.terminal_expanded_height
        self._console_anim: QVariantAnimation | None = None
        self._artifacts_anim: QVariantAnimation | None = None

        # Use stacks as permanent layout residents to eliminate flicker during swaps
        self._console_stack = QStackedWidget()
        self._artifacts_stack = QStackedWidget()

        # Track panels in stacks
        self._console_map: dict[int, int] = {
            id(shared_panels): self._console_stack.addWidget(shared_panels._console_panel)
        }
        self._artifacts_map: dict[int, int] = {
            id(shared_panels): self._artifacts_stack.addWidget(shared_panels._artifacts_panel)
        }

        # Set initial stack indices
        self._console_stack.setCurrentIndex(0)
        self._artifacts_stack.setCurrentIndex(0)
        self._main_layout = QHBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        # Left: splitter for stacked widget + terminal (vertical)
        self._v_splitter = QSplitter(Qt.Orientation.Vertical)
        self._v_splitter.setHandleWidth(1)
        self._v_splitter.setStyleSheet(
            f"QSplitter::handle {{ background-color: {Colors.BORDER_SUBTLE}; }}"
        )

        self._v_splitter.addWidget(stacked_widget)
        self._v_splitter.addWidget(self._console_stack)

        # Set stretch factors: stacked widget is flexible, console is fixed-ish but resizable
        self._v_splitter.setStretchFactor(0, 1)
        self._v_splitter.setStretchFactor(1, 0)

        # Prevent terminal from being hidden completely by dragging the handle
        self._v_splitter.setCollapsible(1, False)

        # Right: artifacts
        self._main_layout.addWidget(self._v_splitter, stretch=1)
        self._main_layout.addWidget(self._artifacts_stack)

        # Connect signals
        shared_panels.console_toggled.connect(self._on_console_toggled)
        shared_panels.artifacts_toggled.connect(self._on_artifacts_toggled)
        self._v_splitter.splitterMoved.connect(self._on_splitter_moved)

        # Initial state: if console is already visible, try to apply height
        if shared_panels.is_console_visible():
            self._apply_console_height(True)

    def showEvent(self, event) -> None:
        """Apply initial sizes when the widget is first shown.

        Args:
            event (QShowEvent): The show event.
        """
        super().showEvent(event)
        # Force a small delay to ensure geometry is finalized
        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, lambda: self._apply_console_height(self._panels.is_console_visible()))

    def _on_splitter_moved(self, pos: int, index: int) -> None:
        """Store the console height when resized manually.

        Args:
            pos (int): New splitter handle position.
            index (int): Index of the handle.
        """
        if index == 1 and self._panels.is_console_visible():
            sizes = self._v_splitter.sizes()
            if len(sizes) > 1:
                self._last_console_height = sizes[1]

    def _on_console_toggled(self, expanded: bool) -> None:
        """Handle console toggle by beginning the height animation.

        Args:
            expanded (bool): Whether the console is expanded.
        """
        # During expansion, we need to allow the stack to be smaller than terminal_min_height
        # to ensure a smooth animation from the toggle button height.
        if expanded:
            self._console_stack.setMinimumHeight(config.ui.panel_toggle_size)
            self._console_stack.setMaximumHeight(config.ui.max_widget_size)
        else:
            # When collapsing, we can set the target constraints immediately
            self._console_stack.setMinimumHeight(config.ui.panel_toggle_size)
            self._console_stack.setMaximumHeight(config.ui.panel_toggle_size)

        self._apply_console_height(expanded)

    def _on_artifacts_toggled(self, expanded: bool) -> None:
        """Handle artifacts toggle by animating the stack width.

        Args:
            expanded (bool): New state.
        """
        start_w = self._artifacts_stack.width()
        end_w = (
            self._panels.artifacts_panel.expanded_width if expanded else config.ui.panel_toggle_size
        )

        # Cleanup existing animation
        if self._artifacts_anim and self._artifacts_anim.state() == QVariantAnimation.State.Running:
            self._artifacts_anim.stop()

        def update_width(value: float) -> None:
            w = int(value)
            self._artifacts_stack.setFixedWidth(w)

        def finalize() -> None:
            # After animation, ensure correct final width
            if expanded:
                self._artifacts_stack.setFixedWidth(end_w)
            else:
                self._artifacts_stack.setFixedWidth(end_w)

        self._artifacts_anim = animate_value(
            parent=self,
            start=float(start_w),
            end=float(end_w),
            callback=update_width,
            on_finished=finalize,
        )

    def _get_target_console_height(self, expanded: bool, total_height: int) -> int:
        """Calculate target height for console.

        Args:
            expanded (bool): Desired state.
            total_height (int): Total available height.

        Returns:
            int: Target height in pixels.
        """
        if expanded:
            target_h = min(self._last_console_height, total_height - config.ui.terminal_min_height)
            return max(target_h, config.ui.terminal_min_height)
        return config.ui.panel_toggle_size

    def _apply_console_height(self, expanded: bool) -> None:
        """Update splitter sizes based on expanded state with animation.

        Args:
            expanded (bool): Desired expansion state.
        """
        if not self.isVisible():
            return

        total_height = self._v_splitter.height()
        if total_height <= 0:
            return

        sizes = self._v_splitter.sizes()
        if not sizes or len(sizes) < 2:
            return

        start_h = sizes[1]
        target_h = self._get_target_console_height(expanded, total_height)

        # Cleanup existing animation
        if self._console_anim and self._console_anim.state() == QVariantAnimation.State.Running:
            self._console_anim.stop()

        def update_sizes(value: float) -> None:
            h = int(value)
            self._v_splitter.setSizes([total_height - h, h])

        self._console_anim = animate_value(
            parent=self,
            start=float(start_h),
            end=float(target_h),
            callback=update_sizes,
        )

        if expanded:
            self._v_splitter.handle(1).setEnabled(True)
            # Restore minimum usable height after animation finished
            self._console_anim.finished.connect(
                lambda: self._console_stack.setMinimumHeight(config.ui.terminal_min_height)
            )
        else:
            self._v_splitter.handle(1).setEnabled(False)

    def set_panels(self, new_panels: SharedPanelsWidget) -> None:
        """Swap panels when hardware is changed using QStackedWidget to avoid flicker.

        Args:
            new_panels (SharedPanelsWidget): The new panels to display.
        """
        if self._panels == new_panels:
            return

        # Disconnect old signals
        with contextlib.suppress(TypeError, RuntimeError):
            self._panels.console_toggled.disconnect(self._on_console_toggled)
            self._panels.artifacts_toggled.disconnect(self._on_artifacts_toggled)

        # Add to stacks if not already there
        panel_id = id(new_panels)
        if panel_id not in self._console_map:
            self._console_map[panel_id] = self._console_stack.addWidget(new_panels._console_panel)
        if panel_id not in self._artifacts_map:
            self._artifacts_map[panel_id] = self._artifacts_stack.addWidget(
                new_panels._artifacts_panel
            )

        # Switch stack indices
        self._console_stack.setCurrentIndex(self._console_map[panel_id])
        self._artifacts_stack.setCurrentIndex(self._artifacts_map[panel_id])

        # Synchronize stack sizes and constraints using state-driven values
        # This prevents "pollution" from hidden expanded panels without layout queries
        con_expanded = new_panels.is_console_visible()
        con_min_h = config.ui.terminal_min_height if con_expanded else config.ui.panel_toggle_size
        con_max_h = config.ui.max_widget_size if con_expanded else config.ui.panel_toggle_size
        self._console_stack.setMinimumHeight(con_min_h)
        self._console_stack.setMaximumHeight(con_max_h)

        # Connect new signals
        new_panels.console_toggled.connect(self._on_console_toggled)
        new_panels.artifacts_toggled.connect(self._on_artifacts_toggled)

        self._panels = new_panels

        # Apply current state with animation
        self._apply_console_height(new_panels.is_console_visible())
        self._on_artifacts_toggled(new_panels.is_artifacts_visible())

    @property
    def stacked_widget(self) -> QStackedWidget:
        """Return the internal stacked widget.

        Returns:
            QStackedWidget: The stacked widget.
        """
        return self._stacked

    @property
    def panels(self) -> SharedPanelsWidget:
        """Return the current shared panels.

        Returns:
            SharedPanelsWidget: The current panels.
        """
        return self._panels
