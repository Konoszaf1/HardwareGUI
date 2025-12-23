"""
Presenter class that connects view events to model logic and acts as a bridge
between graphical user interface and actual data.
"""

from typing import Callable, Dict, List

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QWidget

from src.gui.scripts.voltage_unit.calibration import CalibrationPage
from src.gui.scripts.voltage_unit.guard import GuardPage
from src.gui.scripts.voltage_unit.session_and_coeffs import SessionAndCoeffsPage
from src.gui.scripts.voltage_unit.tests import TestsPage
from src.logic.vu_service import VoltageUnitService
from src.gui.sidebar_button import SidebarButton
from src.logic.action_dataclass import ActionDescriptor
from src.logic.model.actions_model import ActionModel, ActionsByHardwareProxy


# Page factory type: takes parent widget and service, returns page widget
PageFactory = Callable[[QWidget, VoltageUnitService], QWidget]

# Registry mapping page_id to factory function
# To add a new page, simply add an entry here - no if-elif changes needed (OCP)
PAGE_FACTORIES: Dict[str, PageFactory] = {
    "workbench": lambda parent, svc: SessionAndCoeffsPage(parent, svc),
    "calibration": lambda parent, svc: CalibrationPage(parent, svc),
    "test": lambda parent, svc: TestsPage(parent, svc),
    "guard": lambda parent, svc: GuardPage(parent, svc),
}


class ActionsPresenter(QObject):
    """Handles model and view connections and logic."""

    def __init__(
        self,
        widget,
        buttons: List[SidebarButton],
        actions: list[ActionDescriptor],
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
        """Register page factories for each action and bind to list view.

        Uses PAGE_FACTORIES registry instead of if-elif chain, making it easy
        to add new pages without modifying this method (Open/Closed Principle).
        """
        for action in actions:
            factory = PAGE_FACTORIES.get(action.page_id)
            if factory:
                # Capture factory in closure to avoid late binding issues
                self.widget.stacked_widget.register_page(
                    action.page_id,
                    lambda f=factory: f(self.widget.stacked_widget, self.service),
                )

        self.widget.stacked_widget.bind_to_listview(
            self.widget.list_view, role=ActionModel.page_id_role
        )
