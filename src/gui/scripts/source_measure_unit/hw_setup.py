"""Hardware setup page for Source Measure Unit initialization."""

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
from src.gui.shared_panels_widget import SharedPanelsWidget
from src.logic.services.smu_service import SourceMeasureUnitService

# Channel configuration presets
CHANNEL_PRESETS = {
    "SMU_DEFAULT": [
        {
            "id": "CH1",
            "type": "IV",
            "range": 10.0,
            "gain": 1.0,
            "offset": 0.0,
        },
        {
            "id": "CH2",
            "type": "IV",
            "range": 10.0,
            "gain": 1.0,
            "offset": 0.0,
        },
        {
            "id": "CH3",
            "type": "PA",
            "range": 1.0,
            "gain": 1.0,
            "offset": 0.0,
        },
        {
            "id": "CH4",
            "type": "PA",
            "range": 1.0,
            "gain": 1.0,
            "offset": 0.0,
        },
    ],
}


class SMUSetupPage(BaseHardwarePage):
    """Hardware setup page for SMU initialization.

    Provides controls for:
    - Unit EEPROM: Serial, Processor Type
    - Channel Configuration: Table with preset loading
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        service: SourceMeasureUnitService | None = None,
        shared_panels: SharedPanelsWidget | None = None,
    ):
        super().__init__(parent, service, shared_panels)

        # ==== Main Layout with Scroll Area ====
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll, content, main_layout = self._create_scroll_area(min_width=600)
        outer_layout.addWidget(scroll)

        # ==== Title ====
        title = QLabel("Source Measure Unit – Setup")
        title.setObjectName("title")
        main_layout.addWidget(title)

        # ==== Unit EEPROM Section ====
        eeprom_box = self._create_group_box("Unit EEPROM", min_height=120)
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
        self.channel_table.setColumnCount(5)
        self.channel_table.setHorizontalHeaderLabels(
            ["Channel ID", "Type", "Range", "Gain", "Offset"]
        )
        self.channel_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.channel_table.setMinimumHeight(180)
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

        # Load initial preset
        self._on_preset_changed(self.cb_preset.currentText())

        self._log("Setup page ready.")

    def _populate_table(self, channels: list[dict]) -> None:
        """Populate channel table with data."""
        self.channel_table.setRowCount(len(channels))
        for row, ch in enumerate(channels):
            self.channel_table.setItem(row, 0, QTableWidgetItem(ch.get("id", "")))
            self.channel_table.setItem(row, 1, QTableWidgetItem(ch.get("type", "")))
            self.channel_table.setItem(row, 2, QTableWidgetItem(str(ch.get("range", ""))))
            self.channel_table.setItem(row, 3, QTableWidgetItem(str(ch.get("gain", ""))))
            self.channel_table.setItem(row, 4, QTableWidgetItem(str(ch.get("offset", ""))))

    def _on_preset_changed(self, preset_name: str) -> None:
        """Load preset values into the table."""
        if preset_name in CHANNEL_PRESETS:
            self._populate_table(CHANNEL_PRESETS[preset_name])
            self._log(f"Loaded preset: {preset_name}")

    def _on_save(self) -> None:
        """Save current configuration."""
        self._log("Saving configuration... (not implemented)")

    def _on_load(self) -> None:
        """Load configuration from device EEPROM."""
        if not self.service:
            self._log("Service not available.")
            return
        self._log("Loading configuration from device...")
