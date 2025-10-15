"""
Model representing an action that is selectable from the list view of the main
window after a hardware device has been selected. Handles filtering and sorting
of the model via a proxy filter.
"""

from PySide6.QtCore import Qt, QAbstractListModel, QModelIndex, QSortFilterProxyModel
from src.logic.action_dataclass import ActionDescriptor


class ActionModel(QAbstractListModel):
    """
    Create the instance of an action model using its action descriptor
    dataclass. Assign roles and override model functions to tune functionality.
    """

    id_role = Qt.ItemDataRole.UserRole + 1
    hardware_id_role = Qt.ItemDataRole.UserRole + 2
    label_role = Qt.ItemDataRole.UserRole + 3
    order_role = Qt.ItemDataRole.UserRole + 4

    def __init__(self, actions: list[ActionDescriptor]):
        super().__init__()
        self.actions = actions

    def rowCount(self, parent=QModelIndex()) -> int:
        """Return the current available actions of the models"""
        return 0 if parent.isValid() else len(self.actions)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """Return the data tied to each item by index and by selected role"""
        if not index.isValid():
            return None
        a = self.actions[index.row()]
        if role in (Qt.ItemDataRole.DisplayRole, self.label_role):
            return a.label
        if role == self.id_role:
            return a.id
        if role == self.hardware_id_role:
            return a.hardware_id
        return None

    def roleNames(self):
        """Return a dictionary of all role names available"""
        return {
            self.id_role: b"id",
            self.hardware_id_role: b"hardware_id",
            self.label_role: b"label",
            self.order_role: b"order",
        }


class ActionsByHardwareProxy(QSortFilterProxyModel):
    """Proxy to enable filtering actions according to selected hardware id"""

    def __init__(self):
        super().__init__()
        self.hardware_id: int | None = None
        self.setFilterRole(ActionModel.hardware_id_role)

    def set_hardware_id(self, hardware_id: int | None):
        """
        Set the selected hardware ID to the one clicked by the sidebar
        buttons in order to filter actions only by that ID
        """
        print(f"set property as {hardware_id}")
        if self.hardware_id == hardware_id:
            return
        self.hardware_id = hardware_id
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        """Method override that is called to decide whether to include an
        action by the active filtering hardware ID"""
        if self.hardware_id is None:
            return False
        m = self.sourceModel()
        idx = m.index(source_row, 0, source_parent)
        return m.data(idx, ActionModel.hardware_id_role) == self.hardware_id
