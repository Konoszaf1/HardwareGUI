from typing import List

from PySide6.QtCore import QObject

from src.gui.sidebar_button import SidebarButton
from src.logic.action_dataclass import ActionDescriptor
from src.logic.model.actions_model import ActionModel, ActionsByHardwareProxy


class ActionsPresenter(QObject):
    def __init__(
        self, widget, buttons: List[SidebarButton], actions: list[ActionDescriptor]
    ):
        super().__init__(widget)
        self.model = ActionModel(actions)
        self.proxy = ActionsByHardwareProxy()
        self.proxy.setSourceModel(self.model)
        widget.list_view.setModel(self.proxy)
        for button in buttons:
            button.toggled.connect(
                lambda checked, btn=button: checked
                and self.proxy.setHardwareId(btn.property("id"))
            )
