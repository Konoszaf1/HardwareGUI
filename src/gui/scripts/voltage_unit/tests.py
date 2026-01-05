"""Tests page for voltage unit validation."""

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.gui.scripts.base_page import BaseHardwarePage
from src.gui.shared_panels_widget import SharedPanelsWidget
from src.gui.styles import Styles
from src.gui.utils.widget_factories import create_test_card
from src.logic.vu_service import VoltageUnitService


class TestsPage(BaseHardwarePage):
    """Test execution page for voltage unit validation.

    Provides controls to run individual tests (outputs, ramp, transient) or all tests
    together. Test results are logged to the shared console panel and generated plots
    appear in the shared artifacts panel.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        service: VoltageUnitService | None = None,
        shared_panels: SharedPanelsWidget | None = None,
    ):
        """Initialize the TestsPage.

        Args:
            parent (QWidget | None): Parent widget.
            service (VoltageUnitService | None): Service for voltage unit operations.
            shared_panels (SharedPanelsWidget | None): Shared panels for logs/artifacts.
        """
        super().__init__(parent, service, shared_panels)

        # ==== Main Layout (Vertical) ====
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)

        # ==== Title ====
        title = QLabel("Voltage Unit – Tests")
        title.setObjectName("title")
        main_layout.addWidget(title)

        # ==== Test Cards ====
        cards_widget = QWidget()
        cards_layout = QHBoxLayout(cards_widget)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(15)

        # -- Card 1: Outputs --
        self.btn_test_outputs = QPushButton("Run Test")
        card_outputs = create_test_card(
            "Outputs Test",
            ["Points: 5000", "Scale: 0.2 V/div", "Time: 1e-2 s/div"],
            self.btn_test_outputs,
        )
        cards_layout.addWidget(card_outputs)

        # -- Card 2: Ramp --
        self.btn_test_ramp = QPushButton("Run Test")
        card_ramp = create_test_card(
            "Ramp Test",
            ["Range: 500 ms", "Slope: ~20 V/s", "Sync: 1 MHz"],
            self.btn_test_ramp,
        )
        cards_layout.addWidget(card_ramp)

        # -- Card 3: Transient --
        self.btn_test_transient = QPushButton("Run Test")
        card_transient = create_test_card(
            "Transient Test",
            ["Amp: 1 V", "Step: Auto (5-20µs)", "Rec: 5000 pts"],
            self.btn_test_transient,
        )
        cards_layout.addWidget(card_transient)

        # -- Card 4: All --
        self.btn_test_all = QPushButton("Run All")
        self.btn_test_all.setStyleSheet(Styles.BUTTON_ACCENT)
        card_all = create_test_card(
            "Full Suite",
            ["Runs all tests", "Generates all plots", "Verifies results"],
            self.btn_test_all,
        )
        cards_layout.addWidget(card_all)

        cards_layout.addStretch()
        main_layout.addWidget(cards_widget)

        # Stretch to fill remaining space
        main_layout.addStretch()

        # Register action buttons for busy state management
        self._action_buttons = [
            self.btn_test_outputs,
            self.btn_test_ramp,
            self.btn_test_transient,
            self.btn_test_all,
        ]

        # Wire backend actions
        self.btn_test_outputs.clicked.connect(self._on_test_outputs)
        self.btn_test_ramp.clicked.connect(self._on_test_ramp)
        self.btn_test_transient.clicked.connect(self._on_test_transient)
        self.btn_test_all.clicked.connect(self._on_test_all)

        # Connect service signals (from base class)
        self._connect_service_signals()

        self._log("Tests page ready. Actions map 1:1 to script.")

    # ---- Handlers ----
    def _on_test_outputs(self) -> None:
        """Run output voltage accuracy test."""
        if not self.service:
            self._log("Service not available.")
            return
        self._start_task(self.service.test_outputs())

    def _on_test_ramp(self) -> None:
        """Run voltage ramp test."""
        if not self.service:
            self._log("Service not available.")
            return
        self._start_task(self.service.test_ramp())

    def _on_test_transient(self) -> None:
        """Run transient response test."""
        if not self.service:
            self._log("Service not available.")
            return
        self._start_task(self.service.test_transient())

    def _on_test_all(self) -> None:
        """Run all tests sequentially (outputs, ramp, transient)."""
        if not self.service:
            self._log("Service not available.")
            return
        self._start_task(self.service.test_all())
