"""Calibration page for voltage unit autocalibration and testing."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.gui.scripts.base_page import BaseHardwarePage
from src.gui.shared_panels_widget import SharedPanelsWidget
from src.logic.services.vu_service import VoltageUnitService


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
        parent: QWidget | None = None,
        service: VoltageUnitService | None = None,
        shared_panels: SharedPanelsWidget | None = None,
    ):
        """Initialize the CalibrationPage.

        Args:
            parent (QWidget | None): Parent widget.
            service (VoltageUnitService | None): Service for voltage unit operations.
            shared_panels (SharedPanelsWidget | None): Shared panels for logs/artifacts.
        """
        super().__init__(parent, service, shared_panels)

        # ==== Main Layout (Vertical) ====
        main_layout = QVBoxLayout(self)

        # ==== Title ====
        title = QLabel("Voltage Unit – Calibration")
        title.setObjectName("title")
        main_layout.addWidget(title)

        # ==== Top Section ====
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)

        # -- Controls --
        controls_box = QGroupBox("Calibration Actions")
        controls_layout = QVBoxLayout(controls_box)

        self.btn_run_autocal_python = QPushButton("Run Autocalibration (Python)")
        self.btn_run_autocal_onboard = QPushButton("Run Autocalibration (Onboard)")
        self.btn_test_all = QPushButton("Test: All")

        controls_layout.addWidget(self.btn_run_autocal_python)
        controls_layout.addWidget(self.btn_run_autocal_onboard)
        controls_layout.addWidget(self.btn_test_all)
        controls_layout.addStretch()

        # Info box (compact)
        info_box = QGroupBox("Constants")
        info_form = QFormLayout(info_box)
        info_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        info_form.addRow("Max iter:", QLabel("10"))
        info_form.addRow("Offset:", QLabel("2 mV"))
        info_form.addRow("Slope err:", QLabel("0.1 %"))

        controls_layout.addWidget(info_box)

        top_layout.addWidget(controls_box)
        top_layout.addStretch()

        main_layout.addWidget(top_widget)

        # Stretch to fill remaining space
        main_layout.addStretch()

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
