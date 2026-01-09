"""Calibration measurement page for Sampling Unit."""

from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QCheckBox,
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
from src.logic.services.su_service import SamplingUnitService


class SUCalMeasurePage(BaseHardwarePage):
    """Calibration measurement page for SU.

    Provides controls for:
    - Configuring Keithley IP address
    - Running calibration measurements
    - Optionally verifying calibration after measurement
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        service: SamplingUnitService | None = None,
        shared_panels: SharedPanelsWidget | None = None,
    ):
        """Initialize the SUCalMeasurePage.

        Args:
            parent: Parent widget.
            service: SU service instance.
            shared_panels: Shared panels for logs/artifacts.
        """
        super().__init__(parent, service, shared_panels)

        # ==== Main Layout ====
        main_layout = QVBoxLayout(self)

        # ==== Title ====
        title = QLabel("Sampling Unit – Calibration Measure")
        title.setObjectName("title")
        main_layout.addWidget(title)

        # ==== Configuration Box ====
        config_box = QGroupBox("Measurement Configuration")
        config_layout = QFormLayout(config_box)
        config_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # Keithley IP
        self.le_keithley_ip = QLineEdit("192.168.68.206")
        self.le_keithley_ip.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed
        )
        ip_re = QRegularExpression(
            r"^(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)$"
        )
        self.le_keithley_ip.setValidator(QRegularExpressionValidator(ip_re, self))
        self.le_keithley_ip.setPlaceholderText("e.g. 192.168.68.206")
        config_layout.addRow("Keithley IP:", self.le_keithley_ip)

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
            "• Connect Keithley to the SU via SMU correctly\n"
            "• Ensure both SMU and SU are connected\n"
            "• Ensure the Keithley is powered on and reachable\n\n"
            "The measurement process may take several minutes per amplifier channel."
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

        verify = self.chk_verify.isChecked()

        self._log(f"Running calibration measurement: verify={verify}")
        self._start_task(self.service.run_calibration_measure(verify))
