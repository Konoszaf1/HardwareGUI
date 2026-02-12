"""Hardware setup page for Sampling Unit initialization."""

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.gui.scripts.base_page import BaseHardwarePage
from src.gui.widgets.shared_panels_widget import SharedPanelsWidget
from src.logic.services.su_service import SamplingUnitService

# Channel configuration presets
CHANNEL_PRESETS = {
    "VE": [
        {
            "id": "AMP1",
            "amp": "AMP",
            "ch": "INPUT",
            "opamp": "ADA4898",
            "gain": 0.3,
            "bw": 1.606,
            "range": 7.5,
            "unit": "V",
        },
        {
            "id": "AMP2",
            "amp": "AMP",
            "ch": "INPUT",
            "opamp": "ADA4898",
            "gain": 0.3,
            "bw": 1.606,
            "range": 7.5,
            "unit": "V",
        },
        {
            "id": "AMP3",
            "amp": "AMP",
            "ch": "INPUT",
            "opamp": "ADA4898",
            "gain": 0.3,
            "bw": 1.606,
            "range": 7.5,
            "unit": "V",
        },
    ],
}


class SUSetupPage(BaseHardwarePage):
    """Hardware setup page for SU initialization.

    Provides controls for:
    - Unit EEPROM: Serial, Processor Type, Connector Type
    - Channel Configuration: Table with preset loading
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        service: SamplingUnitService | None = None,
        shared_panels: SharedPanelsWidget | None = None,
    ):
        super().__init__(parent, service, shared_panels)

        # ==== Main Layout with Scroll Area ====
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll, content, main_layout = self._create_scroll_area(min_width=600)
        outer_layout.addWidget(scroll)

        # ==== Title ====
        title = QLabel("Sampling Unit – Setup")
        title.setObjectName("title")
        main_layout.addWidget(title)

        # ==== Unit EEPROM Section ====
        eeprom_box = self._create_group_box("Unit EEPROM", min_height=160)
        eeprom_form = self._create_form_layout(eeprom_box)

        self.sp_serial = QSpinBox()
        self.sp_serial.setRange(1, 9999)
        self.sp_serial.setValue(4001)
        self._configure_input(self.sp_serial)
        eeprom_form.addRow("New Serial:", self.sp_serial)

        self.cb_processor = QComboBox()
        self.cb_processor.addItems(["746"])
        self._configure_input(self.cb_processor)
        eeprom_form.addRow("Processor Type:", self.cb_processor)

        self.cb_connector = QComboBox()
        self.cb_connector.addItems(["BNC", "TRIAX"])
        self._configure_input(self.cb_connector)
        eeprom_form.addRow("Connector Type:", self.cb_connector)

        main_layout.addWidget(eeprom_box)

        # ==== Channel Configuration Section ====
        channel_box = self._create_group_box(
            "Channel Configuration", min_height=300, expanding=True
        )
        channel_layout = QVBoxLayout(channel_box)
        channel_layout.setContentsMargins(12, 18, 12, 12)
        channel_layout.setSpacing(10)

        # Preset dropdown
        preset_layout = QHBoxLayout()
        preset_label = QLabel("Preset:")
        preset_layout.addWidget(preset_label)
        self.cb_preset = QComboBox()
        self.cb_preset.addItems(list(CHANNEL_PRESETS.keys()))
        self.cb_preset.setToolTip("Dropdown menu loads predefined values")
        self._configure_input(self.cb_preset)
        preset_layout.addWidget(self.cb_preset)
        preset_layout.addStretch()
        channel_layout.addLayout(preset_layout)

        # Channel configuration table
        self.channel_table = QTableWidget()
        self.channel_table.setColumnCount(8)
        self.channel_table.setHorizontalHeaderLabels(
            [
                "Channel ID",
                "Amplifier Type",
                "Channel Type",
                "OpAmp Type",
                "Gain",
                "Bandwidth",
                "Range",
                "Unit",
            ]
        )
        self.channel_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.channel_table.setMinimumHeight(150)
        self.channel_table.verticalHeader().setDefaultSectionSize(28)
        channel_layout.addWidget(self.channel_table)

        # Save/Load buttons
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Save")
        self.btn_save.setToolTip("Save to config file")
        self._configure_input(self.btn_save, min_width=80)
        self.btn_load = QPushButton("Load")
        self.btn_load.setToolTip("Load the config from the device")
        self._configure_input(self.btn_load, min_width=80)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_load)
        btn_layout.addStretch()
        channel_layout.addLayout(btn_layout)

        main_layout.addWidget(channel_box)

        # Register action buttons
        self._action_buttons = [self.btn_save, self.btn_load]

        # ==== Signals ====
        self.cb_preset.currentTextChanged.connect(self._on_preset_changed)
        self.btn_save.clicked.connect(self._on_save)
        self.btn_load.clicked.connect(self._on_load)

        # Connect service signals (from base class)
        self._connect_service_signals()

        # Load initial preset
        self._on_preset_changed(self.cb_preset.currentText())

        self._log("Setup page ready.")

    def _populate_table(self, channels: list[dict]) -> None:
        """Populate channel table with data."""
        self.channel_table.setRowCount(len(channels))
        for row, ch in enumerate(channels):
            self.channel_table.setItem(row, 0, QTableWidgetItem(ch.get("id", "")))
            self.channel_table.setItem(row, 1, QTableWidgetItem(ch.get("amp", "")))
            self.channel_table.setItem(row, 2, QTableWidgetItem(ch.get("ch", "")))
            self.channel_table.setItem(row, 3, QTableWidgetItem(ch.get("opamp", "")))
            self.channel_table.setItem(row, 4, QTableWidgetItem(str(ch.get("gain", ""))))
            self.channel_table.setItem(row, 5, QTableWidgetItem(str(ch.get("bw", ""))))
            self.channel_table.setItem(row, 6, QTableWidgetItem(str(ch.get("range", ""))))
            self.channel_table.setItem(row, 7, QTableWidgetItem(ch.get("unit", "")))

    def _on_preset_changed(self, preset_name: str) -> None:
        """Load preset values into the table."""
        if preset_name in CHANNEL_PRESETS:
            self._populate_table(CHANNEL_PRESETS[preset_name])
            self._log(f"Loaded preset: {preset_name}")

    def _on_save(self) -> None:
        """Save current channel configuration to device EEPROM."""
        if not self.service:
            self._log("Service not available.")
            return
        serial = self.sp_serial.value()
        processor = self.cb_processor.currentText()
        connector = self.cb_connector.currentText()
        self._log(
            f"Saving configuration: serial={serial}, processor={processor}, "
            f"connector={connector}"
        )
        self._start_task(self.service.run_save_config())

    def _on_load(self) -> None:
        """Load channel configuration from device EEPROM."""
        if not self.service:
            self._log("Service not available.")
            return
        self._log("Loading configuration from device...")
        self._start_task(self.service.run_load_config())
