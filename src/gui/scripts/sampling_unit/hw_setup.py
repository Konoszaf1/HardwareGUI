"""Hardware setup page for Sampling Unit initialization."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.gui.scripts.base_page import BaseHardwarePage
from src.gui.shared_panels_widget import SharedPanelsWidget
from src.logic.services.su_service import SamplingUnitService


class SUSetupPage(BaseHardwarePage):
    """Hardware setup page for SU initialization.

    Provides controls for:
    - Setting device serial number
    - Selecting processor type
    - Selecting connector type (BNC/TRIAX)
    - Initializing new hardware after first flash
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        service: SamplingUnitService | None = None,
        shared_panels: SharedPanelsWidget | None = None,
    ):
        """Initialize the SUSetupPage.

        Args:
            parent: Parent widget.
            service: SU service instance.
            shared_panels: Shared panels for logs/artifacts.
        """
        super().__init__(parent, service, shared_panels)

        # ==== Main Layout ====
        main_layout = QVBoxLayout(self)

        # ==== Title ====
        title = QLabel("Sampling Unit – Hardware Setup")
        title.setObjectName("title")
        main_layout.addWidget(title)

        # ==== Configuration Box ====
        config_box = QGroupBox("New Device Configuration")
        config_layout = QFormLayout(config_box)
        config_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.sp_serial = QSpinBox()
        self.sp_serial.setRange(1, 9999)
        self.sp_serial.setValue(4001)
        config_layout.addRow("Serial Number:", self.sp_serial)

        self.cb_processor = QComboBox()
        self.cb_processor.addItems(["746"])
        config_layout.addRow("Processor Type:", self.cb_processor)

        self.cb_connector = QComboBox()
        self.cb_connector.addItems(["BNC", "TRIAX"])
        config_layout.addRow("Connector Type:", self.cb_connector)

        main_layout.addWidget(config_box)

        # ==== Action Button ====
        self.btn_init_device = QPushButton("Initialize Device")
        main_layout.addWidget(self.btn_init_device)

        # Stretch to fill remaining space
        main_layout.addStretch()

        # ==== Info Box ====
        info_box = QGroupBox("Note")
        info_layout = QVBoxLayout(info_box)
        info_label = QLabel(
            "This action initializes a new Sampling Unit device after first flash.\n"
            "It configures the device identity and default settings.\n\n"
            "⚠️ Only run this on freshly flashed devices!"
        )
        info_label.setWordWrap(True)
        info_layout.addWidget(info_label)
        main_layout.addWidget(info_box)

        main_layout.addStretch()

        # Register action buttons for busy state management
        self._action_buttons = [self.btn_init_device]

        # Wire backend action
        self.btn_init_device.clicked.connect(self._on_init_device)

        self._log("Hardware Setup page ready. Configure and click 'Initialize Device'.")

    # ---- Handlers ----
    def _on_init_device(self) -> None:
        """Initialize a new SU device with the configured parameters."""
        if not self.service:
            self._log("Service not available.")
            return

        serial = self.sp_serial.value()
        processor = self.cb_processor.currentText()
        connector = self.cb_connector.currentText()

        self._log(
            f"Initializing device: serial={serial}, processor={processor}, connector={connector}"
        )
        self._start_task(self.service.run_hw_setup(serial, processor, connector))
