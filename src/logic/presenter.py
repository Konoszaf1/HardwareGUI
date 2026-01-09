"""Presenter class that connects view events to model logic.

This module acts as a bridge between the graphical user interface and the
underlying business logic/services, following the MVP pattern.
"""

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QWidget

from src.gui.scripts.sampling_unit.calibration_fit import SUCalFitPage
from src.gui.scripts.sampling_unit.calibration_measure import SUCalMeasurePage
from src.gui.scripts.sampling_unit.hw_setup import SUSetupPage
from src.gui.scripts.sampling_unit.verify import SUVerifyPage
from src.gui.scripts.source_measure_unit.calibration_fit import SMUCalFitPage
from src.gui.scripts.source_measure_unit.calibration_measure import SMUCalMeasurePage
from src.gui.scripts.source_measure_unit.hw_setup import SMUSetupPage
from src.gui.scripts.source_measure_unit.verify import SMUVerifyPage
from src.gui.scripts.voltage_unit.calibration import CalibrationPage
from src.gui.scripts.voltage_unit.guard import GuardPage
from src.gui.scripts.voltage_unit.session_and_coeffs import SessionAndCoeffsPage
from src.gui.scripts.voltage_unit.tests import TestsPage
from src.gui.shared_panels_widget import SharedPanelsWidget
from src.gui.widgets.sidebar_button import SidebarButton
from src.logging_config import get_logger
from src.logic.action_dataclass import ActionDescriptor
from src.logic.model.actions_model import ActionModel, ActionsByHardwareProxy
from src.logic.services.smu_service import SourceMeasureUnitService
from src.logic.services.su_service import SamplingUnitService
from src.logic.services.vu_service import VoltageUnitService

logger = get_logger(__name__)


# Page factory type: takes parent widget, service, and shared panels
PageFactory = Callable[[QWidget, Any, SharedPanelsWidget | None], QWidget]

# Registry mapping page_id to (factory, service_type) tuples
# To add a new page, simply add an entry here - no if-elif changes needed (OCP)
PAGE_FACTORIES: dict[str, tuple[PageFactory, str]] = {
    # Voltage Unit pages
    "workbench": (lambda parent, svc, panels: SessionAndCoeffsPage(parent, svc, panels), "vu"),
    "calibration": (lambda parent, svc, panels: CalibrationPage(parent, svc, panels), "vu"),
    "test": (lambda parent, svc, panels: TestsPage(parent, svc, panels), "vu"),
    "guard": (lambda parent, svc, panels: GuardPage(parent, svc, panels), "vu"),
    # SMU pages
    "smu_setup": (lambda parent, svc, panels: SMUSetupPage(parent, svc, panels), "smu"),
    "smu_verify": (lambda parent, svc, panels: SMUVerifyPage(parent, svc, panels), "smu"),
    "smu_cal_measure": (lambda parent, svc, panels: SMUCalMeasurePage(parent, svc, panels), "smu"),
    "smu_cal_fit": (lambda parent, svc, panels: SMUCalFitPage(parent, svc, panels), "smu"),
    # SU pages
    "su_setup": (lambda parent, svc, panels: SUSetupPage(parent, svc, panels), "su"),
    "su_verify": (lambda parent, svc, panels: SUVerifyPage(parent, svc, panels), "su"),
    "su_cal_measure": (lambda parent, svc, panels: SUCalMeasurePage(parent, svc, panels), "su"),
    "su_cal_fit": (lambda parent, svc, panels: SUCalFitPage(parent, svc, panels), "su"),
}


class ActionsPresenter(QObject):
    """Handles model and view connections and logic.

    Attributes:
        widget (QWidget): The main window widget.
        vu_service (VoltageUnitService): The Voltage Unit backend service.
        smu_service (SourceMeasureUnitService): The SMU backend service.
        su_service (SamplingUnitService): The SU backend service.
        shared_panels (SharedPanelsWidget | None): The shared panels instance.
        model (ActionModel): The model containing actions.
        proxy (ActionsByHardwareProxy): Proxy model for filtering actions.
    """

    def __init__(
        self,
        widget: QWidget,
        buttons: list[SidebarButton],
        actions: list[ActionDescriptor],
        shared_panels: SharedPanelsWidget | None = None,
    ):
        """Initialize the ActionsPresenter.

        Args:
            widget (QWidget): The view widget utilizing this presenter.
            buttons (list[SidebarButton]): List of sidebar buttons to connect.
            actions (list[ActionDescriptor]): List of available actions.
            shared_panels (SharedPanelsWidget | None): Shared panels widget.
        """
        super().__init__(widget)
        logger.debug("ActionsPresenter initializing")
        self.widget = widget
        self.vu_service = VoltageUnitService()
        self.smu_service = SourceMeasureUnitService()
        self.su_service = SamplingUnitService()
        # Keep 'service' as alias to vu_service for backward compatibility
        self.service = self.vu_service
        self.shared_panels = shared_panels
        self.model = ActionModel(actions)
        self.proxy = ActionsByHardwareProxy()
        self.proxy.setSourceModel(self.model)
        widget.list_view.setModel(self.proxy)
        for button in buttons:
            button.toggled.connect(
                lambda checked, btn=button: checked
                and self.proxy.set_hardware_id(btn.property("id"))
            )
        logger.info(f"ActionsPresenter initialized with {len(actions)} actions")

    def _get_service_for_page(self, service_type: str) -> Any:
        """Get the appropriate service instance for a page.

        Args:
            service_type: Either 'vu', 'smu', or 'su'.

        Returns:
            The corresponding service instance.
        """
        if service_type == "smu":
            return self.smu_service
        if service_type == "su":
            return self.su_service
        return self.vu_service

    def connect_actions_and_stacked_view(self, actions: list[ActionDescriptor]) -> None:
        """Register page factories for each action and bind to list view.

        Uses PAGE_FACTORIES registry instead of if-elif chain, making it easy
        to add new pages without modifying this method (Open/Closed Principle).

        Args:
            actions (list[ActionDescriptor]): Actions to register.
        """
        # Configure stacked widget with shared panels
        if self.shared_panels:
            self.widget.stacked_widget.set_shared_panels(self.shared_panels)

        for action in actions:
            factory_tuple = PAGE_FACTORIES.get(action.page_id)
            if factory_tuple:
                factory, service_type = factory_tuple
                service = self._get_service_for_page(service_type)
                # Capture factory, service, and shared_panels in closure
                self.widget.stacked_widget.register_page(
                    action.page_id,
                    lambda f=factory, s=service: f(
                        self.widget.stacked_widget, s, self.shared_panels
                    ),
                )
                logger.debug(f"Registered page factory: {action.page_id} (service={service_type})")
            else:
                logger.warning(f"No factory registered for page_id: {action.page_id}")

        self.widget.stacked_widget.bind_to_listview(
            self.widget.list_view, role=ActionModel.page_id_role
        )
