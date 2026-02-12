"""Connection page for Sampling Unit hardware configuration."""

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.gui.scripts.base_page import BaseHardwarePage
from src.gui.widgets.shared_panels_widget import SharedPanelsWidget
from src.logic.services.su_service import SamplingUnitService


class SUConnectionPage(BaseHardwarePage):
    """Connection configuration page for Sampling Unit.

    Provides controls for:
    - SU connection mode (auto/manual with serial/interface)
    - SMU connection mode (auto/manual with serial/interface)
    - MCU connection mode (auto/manual with serial/interface)
    - Keithley IP address configuration and verification
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

        scroll, content, main_layout = self._create_scroll_area(min_width=500)
        outer_layout.addWidget(scroll)

        # ==== Title ====
        title = QLabel("Sampling Unit – Connection")
        title.setObjectName("title")
        main_layout.addWidget(title)

        # ==== Sampling Unit Configuration ====
        su_box = self._create_group_box("Sampling Unit", min_height=140)
        su_layout = QVBoxLayout(su_box)
        su_layout.setContentsMargins(12, 18, 12, 12)
        su_layout.setSpacing(10)

        su_mode_layout = QHBoxLayout()
        self.rb_su_auto = QRadioButton("Auto")
        self.rb_su_manual = QRadioButton("Manual")
        self.rb_su_auto.setChecked(True)
        self._configure_input(self.rb_su_auto)
        self._configure_input(self.rb_su_manual)
        su_mode_group = QButtonGroup(self)
        su_mode_group.addButton(self.rb_su_auto)
        su_mode_group.addButton(self.rb_su_manual)
        su_mode_layout.addWidget(self.rb_su_auto)
        su_mode_layout.addWidget(self.rb_su_manual)
        su_mode_layout.addStretch()
        su_layout.addLayout(su_mode_layout)

        su_form = self._create_form_layout()

        self.sp_su_serial = QSpinBox()
        self.sp_su_serial.setRange(0, 9999)
        self.sp_su_serial.setEnabled(False)
        self._configure_input(self.sp_su_serial)
        su_form.addRow("Serial:", self.sp_su_serial)

        self.cb_su_interface = QComboBox()
        self.cb_su_interface.addItems(["Select", "USB", "COM1", "COM2"])
        self.cb_su_interface.setEnabled(False)
        self._configure_input(self.cb_su_interface)
        su_form.addRow("Interface:", self.cb_su_interface)

        su_layout.addLayout(su_form)
        main_layout.addWidget(su_box)

        # ==== Source Measure Unit Configuration ====
        smu_box = self._create_group_box("Source Measure Unit", min_height=140)
        smu_layout = QVBoxLayout(smu_box)
        smu_layout.setContentsMargins(2, 2, 2, 2)
        smu_layout.setSpacing(10)

        smu_mode_layout = QHBoxLayout()
        self.rb_smu_auto = QRadioButton("Auto")
        self.rb_smu_manual = QRadioButton("Manual")
        self.rb_smu_auto.setChecked(True)
        self._configure_input(self.rb_smu_auto)
        self._configure_input(self.rb_smu_manual)
        smu_mode_group = QButtonGroup(self)
        smu_mode_group.addButton(self.rb_smu_auto)
        smu_mode_group.addButton(self.rb_smu_manual)
        smu_mode_layout.addWidget(self.rb_smu_auto)
        smu_mode_layout.addWidget(self.rb_smu_manual)
        smu_mode_layout.addStretch()
        smu_layout.addLayout(smu_mode_layout)

        smu_form = self._create_form_layout()

        self.sp_smu_serial = QSpinBox()
        self.sp_smu_serial.setRange(0, 9999)
        self.sp_smu_serial.setEnabled(False)
        self._configure_input(self.sp_smu_serial)
        smu_form.addRow("Serial:", self.sp_smu_serial)

        self.cb_smu_interface = QComboBox()
        self.cb_smu_interface.addItems(["Select", "USB", "COM1", "COM2"])
        self.cb_smu_interface.setEnabled(False)
        self._configure_input(self.cb_smu_interface)
        smu_form.addRow("Interface:", self.cb_smu_interface)

        smu_layout.addLayout(smu_form)
        main_layout.addWidget(smu_box)

        # ==== Microcontrol Unit Configuration ====
        mcu_box = self._create_group_box("Microcontrol Unit", min_height=140)
        mcu_layout = QVBoxLayout(mcu_box)
        mcu_layout.setContentsMargins(2, 2, 2, 2)
        mcu_layout.setSpacing(10)

        mcu_mode_layout = QHBoxLayout()
        self.rb_mcu_auto = QRadioButton("Auto")
        self.rb_mcu_manual = QRadioButton("Manual")
        self.rb_mcu_auto.setChecked(True)
        self._configure_input(self.rb_mcu_auto)
        self._configure_input(self.rb_mcu_manual)
        mcu_mode_group = QButtonGroup(self)
        mcu_mode_group.addButton(self.rb_mcu_auto)
        mcu_mode_group.addButton(self.rb_mcu_manual)
        mcu_mode_layout.addWidget(self.rb_mcu_auto)
        mcu_mode_layout.addWidget(self.rb_mcu_manual)
        mcu_mode_layout.addStretch()
        mcu_layout.addLayout(mcu_mode_layout)

        mcu_form = self._create_form_layout()

        self.sp_mcu_serial = QSpinBox()
        self.sp_mcu_serial.setRange(0, 9999)
        self.sp_mcu_serial.setEnabled(False)
        self._configure_input(self.sp_mcu_serial)
        mcu_form.addRow("Serial:", self.sp_mcu_serial)

        self.cb_mcu_interface = QComboBox()
        self.cb_mcu_interface.addItems(["Robot", "USB", "COM1", "COM2"])
        self.cb_mcu_interface.setEnabled(False)
        self._configure_input(self.cb_mcu_interface)
        mcu_form.addRow("Interface:", self.cb_mcu_interface)

        mcu_layout.addLayout(mcu_form)
        main_layout.addWidget(mcu_box)

        # ==== Keithley Configuration ====
        keithley_box = self._create_group_box("Keithley", min_height=110)
        keithley_form = self._create_form_layout(keithley_box)

        ip_layout = QHBoxLayout()
        self.le_keithley_ip = QLineEdit()
        self.le_keithley_ip.setPlaceholderText("192.168.0.0")
        self._configure_input(self.le_keithley_ip, min_width=150)
        ip_re = QRegularExpression(
            r"^(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)$"
        )
        self.le_keithley_ip.setValidator(QRegularExpressionValidator(ip_re, self))
        ip_layout.addWidget(self.le_keithley_ip)
        self.btn_ping = QPushButton("Ping")
        self._configure_input(self.btn_ping, min_width=80)
        ip_layout.addWidget(self.btn_ping)
        keithley_form.addRow("IP:", ip_layout)

        self.lbl_keithley_status = QLabel("⚪ Not verified")
        keithley_form.addRow("Status:", self.lbl_keithley_status)

        main_layout.addWidget(keithley_box)

        # ==== Connect Button ====
        self.btn_connect = QPushButton("Connect")
        self._configure_input(self.btn_connect, min_height=40)
        main_layout.addWidget(self.btn_connect)

        main_layout.addStretch()

        # Register action buttons
        self._action_buttons = [self.btn_connect, self.btn_ping]

        # ==== Signals ====
        self.rb_su_manual.toggled.connect(self._on_su_mode_changed)
        self.rb_smu_manual.toggled.connect(self._on_smu_mode_changed)
        self.rb_mcu_manual.toggled.connect(self._on_mcu_mode_changed)
        self.btn_ping.clicked.connect(self._on_ping)
        self.btn_connect.clicked.connect(self._on_connect)

        if self.service:
            self.service.instrumentVerified.connect(self._on_instrument_verified)

        self._log("Connection page ready.")

    def _on_su_mode_changed(self, is_manual: bool) -> None:
        """Enable/disable SU manual inputs based on mode."""
        self.sp_su_serial.setEnabled(is_manual)
        self.cb_su_interface.setEnabled(is_manual)

    def _on_smu_mode_changed(self, is_manual: bool) -> None:
        """Enable/disable SMU manual inputs based on mode."""
        self.sp_smu_serial.setEnabled(is_manual)
        self.cb_smu_interface.setEnabled(is_manual)

    def _on_mcu_mode_changed(self, is_manual: bool) -> None:
        """Enable/disable MCU manual inputs based on mode."""
        self.sp_mcu_serial.setEnabled(is_manual)
        self.cb_mcu_interface.setEnabled(is_manual)

    def _on_ping(self) -> None:
        """Ping Keithley to verify connectivity."""
        if not self.service:
            self._log("Service not available.")
            return

        ip = self.le_keithley_ip.text().strip()
        if not ip:
            self._log("Please enter a Keithley IP address.")
            return

        self.service.set_instrument_ip(ip)
        self._log(f"Pinging Keithley at {ip}...")
        result = self.service.ping_instrument()
        if result:
            self._log("✅ Keithley is reachable.")
        else:
            self._log("❌ Keithley ping failed.")

    def _on_instrument_verified(self, verified: bool) -> None:
        """Update Keithley status display."""
        if verified:
            self.lbl_keithley_status.setText("🟢 Verified")
        else:
            self.lbl_keithley_status.setText("🔴 Not reachable")

    def _on_connect(self) -> None:
        """Connect to SU hardware."""
        if not self.service:
            self._log("Service not available.")
            return

        su_serial = 0 if self.rb_su_auto.isChecked() else self.sp_su_serial.value()
        su_interface = 0 if self.rb_su_auto.isChecked() else self.cb_su_interface.currentIndex()
        smu_serial = 0 if self.rb_smu_auto.isChecked() else self.sp_smu_serial.value()
        smu_interface = 0 if self.rb_smu_auto.isChecked() else self.cb_smu_interface.currentIndex()
        keithley_ip = self.le_keithley_ip.text().strip()

        self.service.set_targets(
            keithley_ip=keithley_ip,
            su_serial=su_serial,
            su_interface=su_interface,
            smu_serial=smu_serial,
            smu_interface=smu_interface,
        )

        self._log("Connecting to SU hardware...")
        self._start_task(self.service.connect_only())
