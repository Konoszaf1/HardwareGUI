# tests_page_min.py
"""Tests page for voltage unit validation."""

from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QWidget as QW,
)

from src.gui.styles import Styles
from src.gui.scripts.base_page import BaseHardwarePage
from src.gui.utils.widget_factories import create_test_card
from src.logic.vu_service import VoltageUnitService


class TestsPage(BaseHardwarePage):
    """Test execution page for voltage unit validation.

    Provides controls to run individual tests (outputs, ramp, transient) or all tests
    together. Displays test results in a console and shows generated plots as thumbnails
    that update in real-time during test execution.
    """

    def __init__(self, parent=None, service: VoltageUnitService | None = None):
        super().__init__(parent, service)

        # ==== Main Layout (Vertical) ====
        mainLayout = QVBoxLayout(self)
        mainLayout.setSpacing(15)

        # ==== Title ====
        title = QLabel("Voltage Unit – Tests")
        title.setObjectName("title")
        mainLayout.addWidget(title)

        # ==== Top Section: Test Cards ====
        cardsWidget = QW()
        cardsLayout = QHBoxLayout(cardsWidget)
        cardsLayout.setContentsMargins(0, 0, 0, 0)
        cardsLayout.setSpacing(15)

        # -- Card 1: Outputs --
        self.btn_test_outputs = QPushButton("Run Test")
        card_outputs = create_test_card(
            "Outputs Test",
            ["Points: 5000", "Scale: 0.2 V/div", "Time: 1e-2 s/div"],
            self.btn_test_outputs,
        )
        cardsLayout.addWidget(card_outputs)

        # -- Card 2: Ramp --
        self.btn_test_ramp = QPushButton("Run Test")
        card_ramp = create_test_card(
            "Ramp Test",
            ["Range: 500 ms", "Slope: ~20 V/s", "Sync: 1 MHz"],
            self.btn_test_ramp,
        )
        cardsLayout.addWidget(card_ramp)

        # -- Card 3: Transient --
        self.btn_test_transient = QPushButton("Run Test")
        card_transient = create_test_card(
            "Transient Test",
            ["Amp: 1 V", "Step: Auto (5-20µs)", "Rec: 5000 pts"],
            self.btn_test_transient,
        )
        cardsLayout.addWidget(card_transient)

        # -- Card 4: All --
        self.btn_test_all = QPushButton("Run All")
        self.btn_test_all.setStyleSheet(Styles.BUTTON_ACCENT)
        card_all = create_test_card(
            "Full Suite",
            ["Runs all tests", "Generates all plots", "Verifies results"],
            self.btn_test_all,
        )
        cardsLayout.addWidget(card_all)

        cardsLayout.addStretch()
        mainLayout.addWidget(cardsWidget)

        # ==== Middle Section: Console (from base class) ====
        mainLayout.addWidget(self._create_console(), 1)

        # Input field (from base class)
        mainLayout.addWidget(self._create_input_field())

        # ==== Bottom Section: Images (from base class) ====
        mainLayout.addWidget(self._create_artifact_list(), 1)

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
