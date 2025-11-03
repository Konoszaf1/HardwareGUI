"""
Presenter class that connects view events to model logic and acts as a bridge
between graphical user interface and actual data
"""

from typing import List

from PySide6.QtCore import QObject

from src.gui.scripts.voltage_unit_cal import VoltageUnitCalPage
from src.gui.sidebar_button import SidebarButton
from src.gui.scripts.workbench_page import WorkbenchPage
from src.logic.action_dataclass import ActionDescriptor
from src.logic.model.actions_model import ActionModel, ActionsByHardwareProxy


class ActionsPresenter(QObject):
    """
    Handles model and view connections and logic
    """

    def __init__(
        self, widget, buttons: List[SidebarButton], actions: list[ActionDescriptor],
    ):
        super().__init__(widget)
        self.widget = widget
        self.model = ActionModel(actions)
        self.proxy = ActionsByHardwareProxy()
        self.proxy.setSourceModel(self.model)
        widget.list_view.setModel(self.proxy)
        for button in buttons:
            button.toggled.connect(
                lambda checked, btn=button: checked
                and self.proxy.set_hardware_id(btn.property("id"))
            )

    def connect_actions_and_stacked_view(self, actions: list[ActionDescriptor]) -> None:
        for action in actions:
            self.widget.stacked_widget.register_page(action.page_id, lambda: VoltageUnitCalPage(self.widget.stacked_widget))
        self.widget.stacked_widget.bind_to_listview(self.widget.list_view, role=ActionModel.page_id_role)

