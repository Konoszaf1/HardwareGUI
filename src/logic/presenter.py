"""
Presenter class that connects view events to model logic and acts as a bridge
between graphical user interface and actual data
"""

from typing import List

from PySide6.QtCore import QObject

from src.gui.scripts.voltage_unit.calibration import CalibrationPage
from src.gui.scripts.voltage_unit.guard import GuardPage
from src.gui.scripts.voltage_unit.session_and_coeffs import SessionAndCoeffsPage
from src.gui.scripts.voltage_unit.tests import TestsPage
from src.logic.vu_service import VoltageUnitService
from src.gui.sidebar_button import SidebarButton
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
        self.service = VoltageUnitService()
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
            if action.page_id == "workbench":
                self.widget.stacked_widget.register_page(action.page_id, lambda: SessionAndCoeffsPage(self.widget.stacked_widget, self.service))
            elif action.page_id == "calibration":
                self.widget.stacked_widget.register_page(action.page_id,
                                                         lambda: CalibrationPage(self.widget.stacked_widget, self.service))
            elif action.page_id == "test":
                self.widget.stacked_widget.register_page(action.page_id,
                                                         lambda: TestsPage(self.widget.stacked_widget, self.service))
            elif action.page_id == "guard":
                self.widget.stacked_widget.register_page(action.page_id,
                                                         lambda: GuardPage(self.widget.stacked_widget, self.service))
        self.widget.stacked_widget.bind_to_listview(self.widget.list_view, role=ActionModel.page_id_role)

