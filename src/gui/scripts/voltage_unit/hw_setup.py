"""Hardware setup page for Voltage Unit initialization and coefficient management."""

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
from src.logic.services.vu_service import VoltageUnitService


class VUSetupPage(BaseHardwarePage):
    """Hardware setup page for VU initialization.

    Provides controls for:
    - Unit EEPROM: Serial, Processor Type
    - Coefficient management: Read, Reset (RAM), Write (EEPROM)
    - Coefficient display table (CH1-CH3 slope/offset)
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        service: VoltageUnitService | None = None,
        shared_panels: SharedPanelsWidget | None = None,
    ):
        """Initialize the VUSetupPage.

        Args:
            parent: Parent widget.
            service: Service for voltage unit operations.
            shared_panels: Shared panels for logs/artifacts.
        """
        super().__init__(parent, service, shared_panels)

        # ==== Main Layout with Scroll Area ====
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll, content, main_layout = self._create_scroll_area(min_width=600)
        outer_layout.addWidget(scroll)

        # ==== Title ====
        title = QLabel("Voltage Unit – Setup")
        title.setObjectName("title")
        main_layout.addWidget(title)

        # ==== Unit EEPROM Section ====
        eeprom_box = self._create_group_box("Unit EEPROM", min_height=120)
        eeprom_form = self._create_form_layout(eeprom_box)

        self.sp_serial = QSpinBox()
        self.sp_serial.setRange(1, 9999)
        self.sp_serial.setValue(5001)
        self._configure_input(self.sp_serial)
        eeprom_form.addRow("New Serial:", self.sp_serial)

        self.cb_processor = QComboBox()
        self.cb_processor.addItems(["746"])
        self._configure_input(self.cb_processor)
        eeprom_form.addRow("Processor Type:", self.cb_processor)

        main_layout.addWidget(eeprom_box)

        # ==== Coefficients Section ====
        coeffs_box = self._create_group_box(
            "Calibration Coefficients", min_height=250, expanding=True
        )
        coeffs_layout = QVBoxLayout(coeffs_box)
        coeffs_layout.setContentsMargins(12, 18, 12, 12)
        coeffs_layout.setSpacing(10)

        # Coefficients display table (CH1-CH3: slope, offset)
        self.coeffs_table = QTableWidget()
        self.coeffs_table.setColumnCount(3)
        self.coeffs_table.setHorizontalHeaderLabels(["Channel", "Slope (k)", "Offset (d)"])
        self.coeffs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.coeffs_table.setMinimumHeight(130)
        self.coeffs_table.verticalHeader().setDefaultSectionSize(28)
        self.coeffs_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._populate_coeffs({"CH1": [1.0, 0.0], "CH2": [1.0, 0.0], "CH3": [1.0, 0.0]})
        coeffs_layout.addWidget(self.coeffs_table)

        # Coefficient action buttons
        btn_layout = QHBoxLayout()
        self.btn_read_coeffs = QPushButton("Read from Device")
        self.btn_read_coeffs.setToolTip("Read current coefficients from hardware")
        self._configure_input(self.btn_read_coeffs, min_width=120)
        self.btn_reset_coeffs = QPushButton("Reset (RAM)")
        self.btn_reset_coeffs.setToolTip("Reset coefficients to k=1.0, d=0.0 in RAM")
        self._configure_input(self.btn_reset_coeffs, min_width=100)
        self.btn_write_coeffs = QPushButton("Write (EEPROM)")
        self.btn_write_coeffs.setToolTip("Write current coefficients to EEPROM")
        self._configure_input(self.btn_write_coeffs, min_width=120)
        btn_layout.addWidget(self.btn_read_coeffs)
        btn_layout.addWidget(self.btn_reset_coeffs)
        btn_layout.addWidget(self.btn_write_coeffs)
        btn_layout.addStretch()
        coeffs_layout.addLayout(btn_layout)

        main_layout.addWidget(coeffs_box)
        main_layout.addStretch()

        # Register action buttons
        self._action_buttons = [
            self.btn_read_coeffs,
            self.btn_reset_coeffs,
            self.btn_write_coeffs,
        ]

        # ==== Signals ====
        self.btn_read_coeffs.clicked.connect(self._on_read_coeffs)
        self.btn_reset_coeffs.clicked.connect(self._on_reset_coeffs)
        self.btn_write_coeffs.clicked.connect(self._on_write_coeffs)

        self._log("Setup page ready.")

    def _populate_coeffs(self, coeffs: dict[str, list[float]]) -> None:
        """Populate coefficient table with data.

        Args:
            coeffs: Dictionary mapping channel names to [slope, offset] lists.
        """
        channels = sorted(coeffs.keys())
        self.coeffs_table.setRowCount(len(channels))
        for row, ch in enumerate(channels):
            k, d = coeffs[ch]
            self.coeffs_table.setItem(row, 0, QTableWidgetItem(ch))
            self.coeffs_table.setItem(row, 1, QTableWidgetItem(f"{k:.6f}"))
            self.coeffs_table.setItem(row, 2, QTableWidgetItem(f"{d:.6f}"))

    def _on_read_coeffs(self) -> None:
        """Read coefficients from device hardware."""
        if not self.service:
            self._log("Service not available.")
            return
        task = self.service.read_coefficients()
        if task is None:
            return

        signals = task.signals
        if signals:
            # After task finishes, update the table
            def _on_finished(result):
                if isinstance(result, dict) and "coeffs" in result:
                    self._populate_coeffs(result["coeffs"])

            signals.finished.connect(_on_finished)

        self._start_task(task)

    def _on_reset_coeffs(self) -> None:
        """Reset coefficients to defaults in RAM."""
        if not self.service:
            self._log("Service not available.")
            return
        task = self.service.reset_coefficients_ram()
        if task is None:
            return

        signals = task.signals
        if signals:

            def _on_finished(result):
                if isinstance(result, dict) and "coeffs" in result:
                    self._populate_coeffs(result["coeffs"])

            signals.finished.connect(_on_finished)

        self._start_task(task)

    def _on_write_coeffs(self) -> None:
        """Write current coefficients to EEPROM."""
        if not self.service:
            self._log("Service not available.")
            return
        task = self.service.write_coefficients_eeprom()
        if task is None:
            return
        self._start_task(task)
