"""Verification page for Source Measure Unit hardware."""

from PySide6.QtWidgets import (
    QGroupBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.gui.scripts.base_page import BaseHardwarePage
from src.gui.shared_panels_widget import SharedPanelsWidget
from src.logic.services.smu_service import SourceMeasureUnitService


class SMUVerifyPage(BaseHardwarePage):
    """Verification page for SMU hardware.

    Provides controls for:
    - Running hardware verification (calibrate_eeprom)
    - Checking that the device is functioning properly
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        service: SourceMeasureUnitService | None = None,
        shared_panels: SharedPanelsWidget | None = None,
    ):
        """Initialize the SMUVerifyPage.

        Args:
            parent: Parent widget.
            service: SMU service instance.
            shared_panels: Shared panels for logs/artifacts.
        """
        super().__init__(parent, service, shared_panels)

        # ==== Main Layout ====
        main_layout = QVBoxLayout(self)

        # ==== Title ====
        title = QLabel("Source Measure Unit – Verify")
        title.setObjectName("title")
        main_layout.addWidget(title)

        # ==== Description ====
        desc_box = QGroupBox("Description")
        desc_layout = QVBoxLayout(desc_box)
        desc_label = QLabel(
            "This page verifies that the SMU hardware is working properly.\n\n"
            "The verification process runs the EEPROM calibration routine which:\n"
            "• Checks all power supplies (digital: 5V, 3.3V; analog: ±8V, ±7V, ±5V)\n"
            "• Verifies hardware configuration\n"
            "• Confirms device identity"
        )
        desc_label.setWordWrap(True)
        desc_layout.addWidget(desc_label)
        main_layout.addWidget(desc_box)

        # ==== Action Button ====
        self.btn_verify = QPushButton("Run Verification")
        main_layout.addWidget(self.btn_verify)

        # Stretch to fill remaining space
        main_layout.addStretch()

        # Register action buttons for busy state management
        self._action_buttons = [self.btn_verify]

        # Wire backend action
        self.btn_verify.clicked.connect(self._on_verify)

        self._log("Verification page ready. Click 'Run Verification' to check hardware.")

    # ---- Handlers ----
    def _on_verify(self) -> None:
        """Run hardware verification."""
        if not self.service:
            self._log("Service not available.")
            return

        self._log("Running hardware verification...")
        self._start_task(self.service.run_verify())
