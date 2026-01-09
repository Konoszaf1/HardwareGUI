"""Verification page for Sampling Unit hardware."""

from PySide6.QtWidgets import (
    QGroupBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.gui.scripts.base_page import BaseHardwarePage
from src.gui.shared_panels_widget import SharedPanelsWidget
from src.logic.services.su_service import SamplingUnitService


class SUVerifyPage(BaseHardwarePage):
    """Verification page for SU hardware.

    Provides controls for:
    - Running hardware verification (performautocalibration)
    - Checking that the device is functioning properly
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        service: SamplingUnitService | None = None,
        shared_panels: SharedPanelsWidget | None = None,
    ):
        """Initialize the SUVerifyPage.

        Args:
            parent: Parent widget.
            service: SU service instance.
            shared_panels: Shared panels for logs/artifacts.
        """
        super().__init__(parent, service, shared_panels)

        # ==== Main Layout ====
        main_layout = QVBoxLayout(self)

        # ==== Title ====
        title = QLabel("Sampling Unit – Verify")
        title.setObjectName("title")
        main_layout.addWidget(title)

        # ==== Description ====
        desc_box = QGroupBox("Description")
        desc_layout = QVBoxLayout(desc_box)
        desc_label = QLabel(
            "This page verifies that the Sampling Unit hardware is working properly.\n\n"
            "The verification process runs the autocalibration routine which:\n"
            "• Tests DAC output and ADC input paths\n"
            "• Verifies all amplifier channels\n"
            "• Checks transient sampling functionality\n"
            "• Confirms device communication"
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

        self._log("Running hardware verification (autocalibration)...")
        self._start_task(self.service.run_verify())
