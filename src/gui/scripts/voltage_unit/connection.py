"""Connection page for Voltage Unit hardware configuration."""

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.config import config
from src.gui.scripts.base_page import BaseHardwarePage
from src.gui.widgets.shared_panels_widget import SharedPanelsWidget
from src.logging_config import get_logger
from src.logic.services.vu_service import VoltageUnitService

logger = get_logger(__name__)


class VUConnectionPage(BaseHardwarePage):
    """Connection configuration page for Voltage Unit.

    Provides controls for:
    - Scope IP address and ping verification
    - VU connection mode (auto/manual with serial/interface)
    - MCU connection mode (auto/manual with serial/interface)
    - Connect button for hardware initialization
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        service: VoltageUnitService | None = None,
        shared_panels: SharedPanelsWidget | None = None,
    ):
        """Initialize the VUConnectionPage.

        Args:
            parent: Parent widget.
            service: Service for voltage unit operations.
            shared_panels: Shared panels for logs/artifacts.
        """
        super().__init__(parent, service, shared_panels)

        # ==== Main Layout with Scroll Area ====
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll, content, main_layout = self._create_scroll_area(min_width=500)
        outer_layout.addWidget(scroll)

        # ==== Title ====
        title = QLabel("Voltage Unit – Connection")
        title.setObjectName("title")
        main_layout.addWidget(title)

        # ==== Scope Configuration ====
        scope_box = self._create_group_box("Oscilloscope", min_height=110)
        scope_form = self._create_form_layout(scope_box)

        ip_layout = QHBoxLayout()
        self.le_scope_ip = QLineEdit(config.hardware.default_scope_ip)
        self._configure_input(self.le_scope_ip, min_width=150)
        ip_re = QRegularExpression(
            r"^(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)$"
        )
        self.le_scope_ip.setValidator(QRegularExpressionValidator(ip_re, self))
        self.le_scope_ip.setPlaceholderText("e.g. 192.168.0.10")
        ip_layout.addWidget(self.le_scope_ip)
        self.btn_ping = QPushButton("Ping")
        self._configure_input(self.btn_ping, min_width=80)
        ip_layout.addWidget(self.btn_ping)
        scope_form.addRow("IP:", ip_layout)

        self.lbl_scope_status = QLabel("⚪ Not verified")
        scope_form.addRow("Status:", self.lbl_scope_status)

        main_layout.addWidget(scope_box)

        # ==== Voltage Unit Configuration ====
        vu_box = self._create_group_box("Voltage Unit", min_height=140)
        vu_layout = QVBoxLayout(vu_box)
        vu_layout.setContentsMargins(12, 18, 12, 12)
        vu_layout.setSpacing(10)

        vu_mode_layout = QHBoxLayout()
        self.rb_vu_auto = QRadioButton("Auto")
        self.rb_vu_manual = QRadioButton("Manual")
        self.rb_vu_auto.setChecked(True)
        self._configure_input(self.rb_vu_auto)
        self._configure_input(self.rb_vu_manual)
        vu_mode_group = QButtonGroup(self)
        vu_mode_group.addButton(self.rb_vu_auto)
        vu_mode_group.addButton(self.rb_vu_manual)
        vu_mode_layout.addWidget(self.rb_vu_auto)
        vu_mode_layout.addWidget(self.rb_vu_manual)
        vu_mode_layout.addStretch()
        vu_layout.addLayout(vu_mode_layout)

        vu_form = self._create_form_layout()

        hw = config.hardware
        self.sp_vu_serial = QSpinBox()
        self.sp_vu_serial.setRange(0, hw.vu_serial_max)
        self.sp_vu_serial.setEnabled(False)
        self._configure_input(self.sp_vu_serial)
        vu_form.addRow("Serial:", self.sp_vu_serial)

        self.sp_vu_interface = QSpinBox()
        self.sp_vu_interface.setRange(0, hw.vu_interface_max)
        self.sp_vu_interface.setEnabled(False)
        self._configure_input(self.sp_vu_interface)
        vu_form.addRow("Interface:", self.sp_vu_interface)

        vu_layout.addLayout(vu_form)
        main_layout.addWidget(vu_box)

        # ==== Main Control Unit Configuration ====
        mcu_box = self._create_group_box("Main Control Unit", min_height=140)
        mcu_layout = QVBoxLayout(mcu_box)
        mcu_layout.setContentsMargins(12, 18, 12, 12)
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
        self.sp_mcu_serial.setRange(0, hw.mcu_serial_max)
        self.sp_mcu_serial.setEnabled(False)
        self._configure_input(self.sp_mcu_serial)
        mcu_form.addRow("Serial:", self.sp_mcu_serial)

        self.sp_mcu_interface = QSpinBox()
        self.sp_mcu_interface.setRange(0, hw.mcu_interface_max)
        self.sp_mcu_interface.setEnabled(False)
        self._configure_input(self.sp_mcu_interface)
        mcu_form.addRow("Interface:", self.sp_mcu_interface)

        mcu_layout.addLayout(mcu_form)
        main_layout.addWidget(mcu_box)

        # ==== Connect Button ====
        self.btn_connect = QPushButton("Connect")
        self._configure_input(self.btn_connect, min_height=40)
        main_layout.addWidget(self.btn_connect)

        main_layout.addStretch()

        # Register action buttons
        self._action_buttons = [self.btn_connect, self.btn_ping]

        # ==== Signals ====
        self.rb_vu_manual.toggled.connect(self._on_vu_mode_changed)
        self.rb_mcu_manual.toggled.connect(self._on_mcu_mode_changed)
        self.btn_ping.clicked.connect(self._on_ping)
        self.btn_connect.clicked.connect(self._on_connect)

        if self.service:
            self.service.scopeVerified.connect(self._on_scope_verified)

        self._log("Connection page ready.")

    def _on_vu_mode_changed(self, is_manual: bool) -> None:
        """Enable/disable VU manual inputs based on mode."""
        self.sp_vu_serial.setEnabled(is_manual)
        self.sp_vu_interface.setEnabled(is_manual)

    def _on_mcu_mode_changed(self, is_manual: bool) -> None:
        """Enable/disable MCU manual inputs based on mode."""
        self.sp_mcu_serial.setEnabled(is_manual)
        self.sp_mcu_interface.setEnabled(is_manual)

    def _on_ping(self) -> None:
        """Ping scope to verify connectivity."""
        if not self.service:
            self._log("Service not available.")
            return

        ip = self.le_scope_ip.text().strip()
        if not ip:
            self._log("Please enter a scope IP address.")
            return

        self.service.set_scope_ip(ip)
        self._log(f"Pinging scope at {ip}...")
        result = self.service.ping_scope()
        if result:
            self._log("✅ Scope is reachable.")
        else:
            self._log("❌ Scope ping failed.")

    def _on_scope_verified(self, verified: bool) -> None:
        """Update scope status display."""
        if verified:
            self.lbl_scope_status.setText("🟢 Verified")
        else:
            self.lbl_scope_status.setText("🔴 Not reachable")

    def _on_connect(self) -> None:
        """Connect to VU hardware."""
        if not self.service:
            self._log("Service not available.")
            return

        vu_serial = 0 if self.rb_vu_auto.isChecked() else self.sp_vu_serial.value()
        vu_interface = 0 if self.rb_vu_auto.isChecked() else self.sp_vu_interface.value()
        mcu_serial = 0 if self.rb_mcu_auto.isChecked() else self.sp_mcu_serial.value()
        mcu_interface = 0 if self.rb_mcu_auto.isChecked() else self.sp_mcu_interface.value()
        scope_ip = self.le_scope_ip.text().strip()

        self.service.set_targets(
            scope_ip=scope_ip,
            vu_serial=vu_serial,
            vu_interface=vu_interface,
            mcu_serial=mcu_serial,
            mcu_interface=mcu_interface,
        )

        self._log("Connecting to VU hardware...")
        self._start_task(self.service.connect_only())
