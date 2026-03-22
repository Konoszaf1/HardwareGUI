"""Connection page for Voltage Unit hardware configuration."""

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
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
        self.btn_search_scope = QPushButton("Search")
        self._configure_input(self.btn_search_scope, min_width=80)
        ip_layout.addWidget(self.btn_search_scope)
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

        # ==== Connect / Disconnect Buttons ====
        conn_layout = QHBoxLayout()
        self.btn_connect = QPushButton("Connect")
        self._configure_input(self.btn_connect, min_height=40)
        self.btn_disconnect = QPushButton("Disconnect")
        self._configure_input(self.btn_disconnect, min_height=40)
        self.btn_disconnect.setEnabled(False)
        self.lbl_connection_status = QLabel("Not connected")
        conn_layout.addWidget(self.btn_connect)
        conn_layout.addWidget(self.btn_disconnect)
        conn_layout.addWidget(self.lbl_connection_status)
        conn_layout.addStretch()
        main_layout.addLayout(conn_layout)

        main_layout.addStretch()

        # Register action buttons (disconnect NOT included — managed separately)
        self._action_buttons = [self.btn_connect, self.btn_ping, self.btn_search_scope]

        # ==== Signals ====
        self.rb_vu_manual.toggled.connect(self._on_vu_mode_changed)
        self.rb_mcu_manual.toggled.connect(self._on_mcu_mode_changed)
        self.btn_search_scope.clicked.connect(self._on_search_scope)
        self.btn_ping.clicked.connect(self._on_ping)
        self.btn_connect.clicked.connect(self._on_connect)
        self.btn_disconnect.clicked.connect(self._on_disconnect)

        if self.service:
            self.service.instrumentVerified.connect(self._on_instrument_verified)
            self.service.connectedChanged.connect(self._on_connected_changed)

    def _on_vu_mode_changed(self, is_manual: bool) -> None:
        """Enable/disable VU manual inputs based on mode."""
        self.sp_vu_serial.setEnabled(is_manual)
        self.sp_vu_interface.setEnabled(is_manual)

    def _on_mcu_mode_changed(self, is_manual: bool) -> None:
        """Enable/disable MCU manual inputs based on mode."""
        self.sp_mcu_serial.setEnabled(is_manual)
        self.sp_mcu_interface.setEnabled(is_manual)

    def _on_search_scope(self) -> None:
        """Search network for oscilloscopes (async)."""
        if not self.service:
            self._log("Service not available.")
            return

        self._log("Searching for oscilloscopes on local network...")
        task = self.service.search_instruments("scope")
        task.signals.finished.connect(self._on_search_finished)
        self._start_task(task)

    def _on_search_finished(self, result) -> None:
        """Handle search results — populate IP field or show menu."""
        if not result.ok or not result.data:
            return
        instruments = result.data.get("instruments", [])
        if not instruments:
            self._log("No oscilloscopes found on the network.")
            return

        if len(instruments) == 1:
            # Single result — auto-fill
            self.le_scope_ip.setText(instruments[0]["ip"])
            self._log(f"Found: {instruments[0]['display']}")
        else:
            # Multiple results — show popup menu
            menu = QMenu(self)
            for instr in instruments:
                action = menu.addAction(instr["display"])
                action.setData(instr["ip"])
            action = menu.exec(self.btn_search_scope.mapToGlobal(
                self.btn_search_scope.rect().bottomLeft()
            ))
            if action:
                self.le_scope_ip.setText(action.data())

    def _on_ping(self) -> None:
        """Ping scope to verify connectivity (async)."""
        if not self.service:
            self._log("Service not available.")
            return

        ip = self.le_scope_ip.text().strip()
        if not ip:
            self._log("Please enter a scope IP address.")
            return

        self.service.set_instrument_ip(ip)
        self._log(f"Pinging scope at {ip}...")
        self._start_task(self.service.ping_instrument())

    def _on_instrument_verified(self, verified: bool) -> None:
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

        scope_ip = self.le_scope_ip.text().strip()
        if not scope_ip:
            self._log("Please enter a scope IP address before connecting.")
            return

        vu_serial = 0 if self.rb_vu_auto.isChecked() else self.sp_vu_serial.value()
        vu_interface = 0 if self.rb_vu_auto.isChecked() else self.sp_vu_interface.value()
        mcu_serial = 0 if self.rb_mcu_auto.isChecked() else self.sp_mcu_serial.value()
        mcu_interface = 0 if self.rb_mcu_auto.isChecked() else self.sp_mcu_interface.value()

        self.service.set_targets(
            scope_ip=scope_ip,
            vu_serial=vu_serial,
            vu_interface=vu_interface,
            mcu_serial=mcu_serial,
            mcu_interface=mcu_interface,
        )

        self._log("Connecting to VU hardware...")
        self._start_task(self.service.connect_only())

    def _on_disconnect(self) -> None:
        """Disconnect from VU hardware."""
        if not self.service:
            return
        self._log("Disconnecting from VU hardware...")
        self._start_task(self.service.disconnect_hardware())

    def _update_action_buttons_state(self) -> None:
        """Connect/Ping are always available on connection pages."""
        for btn in self._action_buttons:
            btn.setEnabled(True)

    def _on_connected_changed(self, connected: bool) -> None:
        """Toggle button states based on connection.

        Does NOT call super() — Connect/Ping must stay enabled regardless
        of connection state so the user can always reconnect.
        """
        self.btn_disconnect.setEnabled(connected)
        self.btn_connect.setText("Reconnect" if connected else "Connect")
        self.lbl_connection_status.setText(
            "Connected" if connected else "Not connected"
        )
        self.lbl_connection_status.setStyleSheet(
            "color: #4ec9b0;" if connected else "color: #cccccc;"
        )
