"""Model representing an action that is selectable from the list view of the main
window after a hardware device has been selected. Handles filtering and sorting
of the model via a proxy filter.
"""

from PySide6.QtCore import QAbstractListModel, QModelIndex, QSortFilterProxyModel, Qt

from src.logging_config import get_logger
from src.logic.action_dataclass import ActionDescriptor

logger = get_logger(__name__)


class ActionModel(QAbstractListModel):
    """Model for selectable actions in the main window list view.

    Creates action items from ActionDescriptor dataclasses and provides
    role-based data access for Qt model/view architecture.

    Attributes:
        id_role: Custom role for action ID.
        hardware_id_role: Custom role for hardware ID filtering.
        label_role: Custom role for display label.
        order_role: Custom role for sort order.
        page_id_role: Custom role for page routing.
    """

    id_role = Qt.ItemDataRole.UserRole + 1
    hardware_id_role = Qt.ItemDataRole.UserRole + 2
    label_role = Qt.ItemDataRole.UserRole + 3
    order_role = Qt.ItemDataRole.UserRole + 4
    page_id_role = Qt.ItemDataRole.UserRole + 5

    def __init__(self, actions: list[ActionDescriptor]):
        super().__init__()
        self.actions = actions

    def rowCount(self, parent=None) -> int:
        """Return the number of available actions.

        Args:
            parent: Parent index (unused for flat list).

        Returns:
            Number of actions in the model.
        """
        if parent is None:
            parent = QModelIndex()
        return 0 if parent.isValid() else len(self.actions)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """Return data for the specified index and role.

        Args:
            index: Model index to retrieve data for.
            role: Data role (DisplayRole, id_role, hardware_id_role, etc).

        Returns:
            Requested data or None if invalid.
        """
        if not index.isValid():
            return None
        a = self.actions[index.row()]
        if role in (Qt.ItemDataRole.DisplayRole, self.label_role):
            return a.label
        if role == self.id_role:
            return a.id
        if role == self.hardware_id_role:
            return a.hardware_id
        if role == self.page_id_role:
            return a.page_id
        return None

    def roleNames(self):
        """Return dictionary mapping role IDs to role names.

        Returns:
            Dict mapping custom roles to their byte-string names.
        """
        return {
            self.id_role: b"id",
            self.hardware_id_role: b"hardware_id",
            self.label_role: b"label",
            self.order_role: b"order",
            self.page_id_role: b"page_id",
        }


class ActionsByHardwareProxy(QSortFilterProxyModel):
    """Proxy to enable filtering actions according to selected hardware id"""

    def __init__(self):
        super().__init__()
        self.hardware_id: int | None = None
        self.setFilterRole(ActionModel.hardware_id_role)

    def set_hardware_id(self, hardware_id: int | None):
        """Set the hardware ID filter for action display.

        Filters actions to only show those matching the selected hardware.

        Args:
            hardware_id: Hardware ID to filter by, or None to show all.
        """
        logger.debug(f"Hardware filter set to: {hardware_id}")
        if self.hardware_id == hardware_id:
            return
        self.hardware_id = hardware_id
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        """Method override that is called to decide whether to include an
        action by the active filtering hardware ID
        """
        if self.hardware_id is None:
            return False
        m = self.sourceModel()
        idx = m.index(source_row, 0, source_parent)
        return m.data(idx, ActionModel.hardware_id_role) == self.hardware_id
