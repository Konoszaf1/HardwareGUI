from PySide6.QtCore import Qt, QAbstractListModel, QModelIndex, QSortFilterProxyModel
from src.logic.action_dataclass import ActionDescriptor


class ActionModel(QAbstractListModel):
    id_role = Qt.ItemDataRole.UserRole + 1
    hardware_id_role = Qt.ItemDataRole.UserRole + 2
    label_role = Qt.ItemDataRole.UserRole + 3
    order_role = Qt.ItemDataRole.UserRole + 4

    def __init__(self, actions: list[ActionDescriptor]):
        super().__init__()
        self.data = actions

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.data)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        a = self.data[index.row()]
        if role in (Qt.DisplayRole, self.LabelRole):
            return a.label
        if role == self.IdRole:
            return a.id
        if role == self.HardwareIdRole:
            return a.hardware_id
        if role == self.IconPathRole:
            return a.icon_path
        return None

    def roleNames(self):
        return {
            self.IdRole: b"id",
            self.HardwareIdRole: b"hardware_id",
            self.LabelRole: b"label",
            self.IconPathRole: b"icon_path",
        }


class ActionsByHardwareProxy(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self.hardware_id: int | None = None
        self.setFilterRole(ActionModel.HardwareIdRole)

    def setHardwareId(self, hardware_id: int | None):
        if self.hardware_id == hardware_id:
            return
        self.hardware_id = hardware_id
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        if self.hardware_id is None:
            return False
        m = self.sourceModel()
        idx = m.index(source_row, 0, source_parent)
        return m.data(idx, ActionModel.HardwareIdRole) == self.hardware_id
