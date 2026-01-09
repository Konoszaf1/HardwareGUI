"""Calibration measurement page for Source Measure Unit."""

from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.gui.scripts.base_page import BaseHardwarePage
from src.gui.shared_panels_widget import SharedPanelsWidget
from src.logic.services.smu_service import SourceMeasureUnitService


class SMUCalMeasurePage(BaseHardwarePage):
    """Calibration measurement page for SMU.

    Provides controls for:
    - Configuring Keithley IP address
    - Selecting VSMU mode (Normal/VSMU/Both)
    - Running calibration measurements
    - Optionally verifying calibration after measurement
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        service: SourceMeasureUnitService | None = None,
        shared_panels: SharedPanelsWidget | None = None,
    ):
        """Initialize the SMUCalMeasurePage.

        Args:
            parent: Parent widget.
            service: SMU service instance.
            shared_panels: Shared panels for logs/artifacts.
        """
        super().__init__(parent, service, shared_panels)

        # ==== Main Layout ====
        main_layout = QVBoxLayout(self)

        # ==== Title ====
        title = QLabel("Source Measure Unit – Calibration Measure")
        title.setObjectName("title")
        main_layout.addWidget(title)

        # ==== Configuration Box ====
        config_box = QGroupBox("Measurement Configuration")
        config_layout = QFormLayout(config_box)
        config_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # Keithley IP
        self.le_keithley_ip = QLineEdit("192.168.68.203")
        self.le_keithley_ip.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed
        )
        ip_re = QRegularExpression(
            r"^(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)$"
        )
        self.le_keithley_ip.setValidator(QRegularExpressionValidator(ip_re, self))
        self.le_keithley_ip.setPlaceholderText("e.g. 192.168.68.203")
        config_layout.addRow("Keithley IP:", self.le_keithley_ip)

        # VSMU Mode
        self.cb_vsmu_mode = QComboBox()
        self.cb_vsmu_mode.addItems(["Normal (False)", "VSMU (True)", "Both (None)"])
        self.cb_vsmu_mode.setCurrentIndex(2)  # Default to Both
        config_layout.addRow("VSMU Mode:", self.cb_vsmu_mode)

        # Verify calibration option
        self.chk_verify = QCheckBox("Measure & Verify (runs twice)")
        self.chk_verify.setChecked(True)
        config_layout.addRow("", self.chk_verify)

        main_layout.addWidget(config_box)

        # ==== Action Button ====
        self.btn_measure = QPushButton("Run Measurement")
        main_layout.addWidget(self.btn_measure)

        # ==== Info Box ====
        info_box = QGroupBox("Prerequisites")
        info_layout = QVBoxLayout(info_box)
        info_label = QLabel(
            "Before running calibration measurements:\n\n"
            "• Connect Keithley to the SMU input correctly\n"
            "• Ensure the Keithley is powered on and reachable\n"
            "• Connect to the same network as the Keithley\n\n"
            "The measurement process may take several minutes per range."
        )
        info_label.setWordWrap(True)
        info_layout.addWidget(info_label)
        main_layout.addWidget(info_box)

        # Stretch to fill remaining space
        main_layout.addStretch()

        # Register action buttons for busy state management
        self._action_buttons = [self.btn_measure]

        # Wire backend action
        self.btn_measure.clicked.connect(self._on_measure)

        self._log("Calibration Measure page ready. Configure Keithley and run measurement.")

    # ---- Helpers ----
    def _get_vsmu_mode(self) -> bool | None:
        """Get VSMU mode value from combo box."""
        index = self.cb_vsmu_mode.currentIndex()
        if index == 0:
            return False  # Normal
        elif index == 1:
            return True  # VSMU
        else:
            return None  # Both

    # ---- Handlers ----
    def _on_measure(self) -> None:
        """Run calibration measurement."""
        if not self.service:
            self._log("Service not available.")
            return

        ip = self.le_keithley_ip.text().strip()
        if not ip:
            self._log("Keithley IP address required.")
            return

        # Configure service with Keithley IP
        self.service.set_keithley_ip(ip)

        vsmu_mode = self._get_vsmu_mode()
        verify = self.chk_verify.isChecked()

        mode_str = {None: "Both", True: "VSMU", False: "Normal"}[vsmu_mode]
        self._log(f"Running calibration measurement: mode={mode_str}, verify={verify}")
        self._start_task(self.service.run_calibration_measure(vsmu_mode, verify))
