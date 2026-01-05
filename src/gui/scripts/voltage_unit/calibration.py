# calibration_page_min.py
"""Calibration page for voltage unit autocalibration and testing."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)
from PySide6.QtWidgets import (
    QWidget as QW,
)

from src.gui.scripts.base_page import BaseHardwarePage
from src.gui.shared_panels_widget import SharedPanelsWidget
from src.logic.vu_service import VoltageUnitService


class CalibrationPage(BaseHardwarePage):
    """Calibration page for voltage unit.

    Provides controls for:
    - Python-based autocalibration (iterative)
    - Onboard autocalibration (firmware-based)
    - Running all tests

    Calibration results are logged to the shared console panel and
    generated plots appear in the shared artifacts panel.
    """

    def __init__(
        self,
        parent=None,
        service: VoltageUnitService | None = None,
        shared_panels: SharedPanelsWidget | None = None,
    ):
        super().__init__(parent, service, shared_panels)

        # ==== Main Layout (Vertical) ====
        mainLayout = QVBoxLayout(self)

        # ==== Title ====
        title = QLabel("Voltage Unit – Calibration")
        title.setObjectName("title")
        mainLayout.addWidget(title)

        # ==== Top Section ====
        topWidget = QW()
        topLayout = QHBoxLayout(topWidget)
        topLayout.setContentsMargins(0, 0, 0, 0)

        # -- Controls --
        controlsBox = QGroupBox("Calibration Actions")
        controlsLayout = QVBoxLayout(controlsBox)

        self.btn_run_autocal_python = QPushButton("Run Autocalibration (Python)")
        self.btn_run_autocal_onboard = QPushButton("Run Autocalibration (Onboard)")
        self.btn_test_all = QPushButton("Test: All")

        controlsLayout.addWidget(self.btn_run_autocal_python)
        controlsLayout.addWidget(self.btn_run_autocal_onboard)
        controlsLayout.addWidget(self.btn_test_all)
        controlsLayout.addStretch()

        # Info box (compact)
        infoBox = QGroupBox("Constants")
        infoForm = QFormLayout(infoBox)
        infoForm.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        infoForm.addRow("Max iter:", QLabel("10"))
        infoForm.addRow("Offset:", QLabel("2 mV"))
        infoForm.addRow("Slope err:", QLabel("0.1 %"))

        controlsLayout.addWidget(infoBox)

        topLayout.addWidget(controlsBox)
        topLayout.addStretch()

        mainLayout.addWidget(topWidget)

        # Stretch to fill remaining space
        mainLayout.addStretch()

        # Register action buttons for busy state management
        self._action_buttons = [
            self.btn_run_autocal_python,
            self.btn_run_autocal_onboard,
            self.btn_test_all,
        ]

        # Wire backend actions
        self.btn_run_autocal_python.clicked.connect(self._on_autocal_python)
        self.btn_run_autocal_onboard.clicked.connect(self._on_autocal_onboard)
        self.btn_test_all.clicked.connect(self._on_test_all)

        # Connect service signals (from base class)
        self._connect_service_signals()

        self._log("Calibration page ready. Actions map 1:1 to script.")

    # ---- Handlers ----
    def _on_autocal_python(self) -> None:
        """Run Python-based autocalibration."""
        if not self.service:
            self._log("Service not available.")
            return
        self._start_task(self.service.autocal_python())

    def _on_autocal_onboard(self) -> None:
        """Run onboard (firmware) autocalibration."""
        if not self.service:
            self._log("Service not available.")
            return
        self._start_task(self.service.autocal_onboard())

    def _on_test_all(self) -> None:
        """Run all calibration tests (outputs, ramp, transient)."""
        if not self.service:
            self._log("Service not available.")
            return
        self._start_task(self.service.test_all())
