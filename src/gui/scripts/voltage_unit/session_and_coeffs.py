"""Session management and coefficient control page for voltage unit."""

from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QApplication,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from src.config import config
from src.gui.scripts.base_page import BaseHardwarePage
from src.gui.shared_panels_widget import SharedPanelsWidget
from src.gui.styles import Styles
from src.logging_config import get_logger
from src.logic.qt_workers import run_in_thread
from src.logic.services.vu_service import VoltageUnitService

logger = get_logger(__name__)


class SessionAndCoeffsPage(BaseHardwarePage):
    """Session management and coefficient control page.

    Provides controls for:
    - Scope connectivity testing
    - Hardware ID configuration (VU and MCU serial/interface numbers)
    - Coefficient reset (RAM only)
    - Coefficient write (to EEPROM)

    The page validates scope connectivity before enabling coefficient operations.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        service: VoltageUnitService | None = None,
        shared_panels: SharedPanelsWidget | None = None,
    ):
        """Initialize the SessionAndCoeffsPage.

        Args:
            parent (QWidget | None): Parent widget.
            service (VoltageUnitService | None): Service for voltage unit operations.
            shared_panels (SharedPanelsWidget | None): Shared panels for logs/artifacts.
        """
        super().__init__(parent, service, shared_panels)

        # ==== Main Layout ====
        main_layout = QVBoxLayout(self)

        # ==== Title ====
        title = QLabel("Voltage Unit – Session")
        title.setObjectName("title")
        main_layout.addWidget(title)

        # ==== Top: Compact Configuration ====
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)

        # Group 1: Connection
        conn_box = QGroupBox("Connection")
        conn_layout = QFormLayout(conn_box)
        conn_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.le_scope_ip = QLineEdit(config.hardware.default_scope_ip)
        self.le_scope_ip.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed
        )
        ip_re = QRegularExpression(
            r"^(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)$"
        )
        self.le_scope_ip.setValidator(QRegularExpressionValidator(ip_re, self))
        self.le_scope_ip.setPlaceholderText("e.g. 192.168.0.10")
        self.btn_test_scope = QPushButton("Test Scope")

        conn_layout.addRow("Scope IP:", self.le_scope_ip)
        conn_layout.addRow(self.btn_test_scope)

        top_layout.addWidget(conn_box)

        # Group 2: Hardware IDs
        id_box = QGroupBox("Hardware IDs")
        id_layout = QGridLayout(id_box)

        hw = config.hardware
        self.sp_vu_serial = QSpinBox()
        self.sp_vu_serial.setRange(0, hw.vu_serial_max)
        self.sp_vu_serial.setValue(0)
        self.sp_vu_interface = QSpinBox()
        self.sp_vu_interface.setRange(0, hw.vu_interface_max)
        self.sp_vu_interface.setValue(0)
        self.sp_mcu_serial = QSpinBox()
        self.sp_mcu_serial.setRange(0, hw.mcu_serial_max)
        self.sp_mcu_serial.setValue(0)
        self.sp_mcu_interface = QSpinBox()
        self.sp_mcu_interface.setRange(0, hw.mcu_interface_max)
        self.sp_mcu_interface.setValue(0)

        id_layout.addWidget(QLabel("VU Serial:"), 0, 0)
        id_layout.addWidget(self.sp_vu_serial, 0, 1)
        id_layout.addWidget(QLabel("VU Interf:"), 0, 2)
        id_layout.addWidget(self.sp_vu_interface, 0, 3)

        id_layout.addWidget(QLabel("MCU Serial:"), 1, 0)
        id_layout.addWidget(self.sp_mcu_serial, 1, 1)
        id_layout.addWidget(QLabel("MCU Interf:"), 1, 2)
        id_layout.addWidget(self.sp_mcu_interface, 1, 3)

        top_layout.addWidget(id_box)

        # Group 3: Coefficients Actions
        act_box = QGroupBox("Coefficients")
        act_layout = QVBoxLayout(act_box)

        self.btn_reset_coeffs = QPushButton("Reset (RAM)")
        self.btn_write_coeffs = QPushButton("Write (EEPROM)")

        act_layout.addWidget(self.btn_reset_coeffs)
        act_layout.addWidget(self.btn_write_coeffs)

        top_layout.addWidget(act_box)
        top_layout.addStretch()

        main_layout.addWidget(top_widget)

        # Stretch to fill remaining space
        main_layout.addStretch()

        # Register action buttons for busy state management
        self._action_buttons = [
            self.btn_reset_coeffs,
            self.btn_write_coeffs,
        ]

        # Wire backend actions
        self.btn_test_scope.clicked.connect(self._on_test_scope)
        self.btn_reset_coeffs.clicked.connect(self._on_reset_coeffs)
        self.btn_write_coeffs.clicked.connect(self._on_write_coeffs_eeprom)

        if self.service:
            self.service.scopeVerified.connect(self._on_scope_verified_changed)

        # Initial UI state
        self._update_ui_state()

        self._log("Session page ready. Please configure Scope IP and click 'Test Scope'.")

    # ---- Wiring helpers ----
    def _update_ui_state(self) -> None:
        """Enable/disable controls based on busy state and scope verification."""
        # Always allow testing scope if not busy
        self.btn_test_scope.setEnabled(not self._busy)

        # Only allow other actions if not busy AND scope is verified
        is_verified = self.service.is_scope_verified if self.service else False
        can_act = (not self._busy) and is_verified
        self.btn_reset_coeffs.setEnabled(can_act)
        self.btn_write_coeffs.setEnabled(can_act)

        # Inputs should be disabled while busy
        self.le_scope_ip.setEnabled(not self._busy)
        self.sp_vu_serial.setEnabled(not self._busy)
        self.sp_vu_interface.setEnabled(not self._busy)
        self.sp_mcu_serial.setEnabled(not self._busy)
        self.sp_mcu_interface.setEnabled(not self._busy)

    def _set_busy(self, busy: bool) -> None:
        """Set the busy state of the page.

        Args:
            busy (bool): True if busy, False otherwise.
        """
        self._busy = busy
        self._update_ui_state()

    def _apply_targets(self) -> None:
        """Apply current UI values to the service's target configuration."""
        if not self.service:
            return
        self.service.set_targets(
            self.le_scope_ip.text().strip(),
            self.sp_vu_serial.value(),
            self.sp_vu_interface.value(),
            self.sp_mcu_serial.value(),
            self.sp_mcu_interface.value(),
        )

    # ---- Button handlers ----
    def _on_test_scope(self) -> None:
        """Ping the oscilloscope using the service."""
        if not self.service:
            self._log("Service not available.")
            return

        ip = self.le_scope_ip.text().strip()
        if not ip:
            self._log("No scope IP configured.")
            return

        # Register IP with service (needed for ping and subsequent calls)
        self.service.set_scope_ip(ip)

        # Set loading icon
        style = QApplication.style()
        self.btn_test_scope.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.btn_test_scope.setText("Testing...")
        self.btn_test_scope.setStyleSheet("")

        try:
            self._set_busy(True)
            QApplication.processEvents()

            ok = self.service.ping_scope()
            if not ok:
                self._on_scope_verified_changed(False)
            else:
                self._on_scope_verified_changed(True)

        except Exception as exc:
            logger.error(f"Scope ping failed with exception: {exc}")
            self._log(f"Ping failed with exception: {exc}")
            self.service.set_scope_verified(False)
            self._on_scope_verified_changed(False)

        self._set_busy(False)

    def _on_scope_verified_changed(self, verified: bool) -> None:
        """Handle updates to scope verification state from service.

        Args:
            verified (bool): Whether the scope is verified.
        """
        style = QApplication.style()
        if verified:
            self._log("Scope verified.")
            self.btn_test_scope.setIcon(
                style.standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)
            )
            self.btn_test_scope.setStyleSheet(Styles.BUTTON_SUCCESS)
            self.btn_test_scope.setText("Connected")
        else:
            self._log("Scope verification failed or reset.")
            self.btn_test_scope.setIcon(
                style.standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton)
            )
            self.btn_test_scope.setStyleSheet(Styles.BUTTON_ERROR)
            self.btn_test_scope.setText("Failed")

        self._update_ui_state()

    def _on_reset_coeffs(self) -> None:
        """Reset calibration coefficients to default values in RAM."""
        if not self.service:
            self._log("Service not available.")
            return

        self._apply_targets()
        self._set_busy(True)

        task = self.service.reset_coefficients_ram()
        self._active_task = task
        signals = task.signals
        if not signals:
            self._log("reset_coefficients_ram() returned no signals.")
            self._set_busy(False)
            return

        signals.started.connect(lambda: self._log("Resetting coefficients (RAM)..."))
        signals.log.connect(lambda s: self._log(s))
        signals.error.connect(lambda e: self._log(f"Error: {e}"))

        def _finished(_result):
            self._log("Reset coefficients (RAM) finished.")
            self._set_busy(False)
            self._active_task = None

        signals.finished.connect(_finished)
        run_in_thread(task)

    def _on_write_coeffs_eeprom(self) -> None:
        """Write current coefficients to EEPROM for persistence."""
        if not self.service:
            self._log("Service not available.")
            return

        self._apply_targets()
        self._set_busy(True)

        task = self.service.write_coefficients_eeprom()
        self._active_task = task
        signals = task.signals
        if not signals:
            self._log("write_coefficients_eeprom() returned no signals.")
            self._set_busy(False)
            return

        signals.started.connect(lambda: self._log("Writing coefficients (EEPROM)..."))
        signals.log.connect(lambda s: self._log(s))
        signals.error.connect(lambda e: self._log(f"Error: {e}"))

        def _finished(_result):
            self._log("Write coefficients (EEPROM) finished.")
            self._set_busy(False)
            self._active_task = None

        signals.finished.connect(_finished)
        run_in_thread(task)
