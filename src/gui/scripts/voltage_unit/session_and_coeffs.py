# session_and_coeffs_page_min.py
from PySide6.QtCore import Qt, QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator, QIcon
from PySide6.QtWidgets import (
    QWidget,
    QGridLayout,
    QLabel,
    QGroupBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QPlainTextEdit,
    QWidget as QW,
    QApplication,
    QStyle,
)

from src.gui.utils.gui_helpers import append_log
from src.logic.qt_workers import run_in_thread
from src.logic.vu_service import VoltageUnitService


class SessionAndCoeffsPage(QWidget):
    """Session management and coefficient control page.
    
    Provides controls for:
    - Scope connectivity testing
    - Hardware ID configuration (VU and MCU serial/interface numbers)
    - Coefficient reset (RAM only)
    - Coefficient write (to EEPROM)
    
    The page validates scope connectivity before enabling coefficient operations.
    
    Attributes:
        service: VoltageUnitService instance for hardware communication
        console: QPlainTextEdit widget for operation logs
    """
    """
    Minimal session page.

    Keeps only the mandatory parameters and a console.

    Inside the "Required Parameters" group:
    - Scope IP field
    - Device IDs
    - Scope connectivity test button (with status icon)
    - Main action button for resetting coefficients in RAM
    """

    def __init__(self, parent=None, service: VoltageUnitService | None = None):
        super().__init__(parent)
        self.service = service
        self._busy = False

        # ==== Root grid ====
        self.grid = QGridLayout(self)
        self.grid.setObjectName("grid")

        # ==== Title ====
        title = QLabel("Voltage Unit – Session (Minimal)")
        title.setObjectName("title")
        self.grid.addWidget(title, 0, 0, 1, 1)

        # ==== Top: Compact Configuration ====
        # We'll use a horizontal layout for the main controls to save vertical space
        topWidget = QW()
        topLayout = QHBoxLayout(topWidget)
        topLayout.setContentsMargins(0, 0, 0, 0)
        
        # Group 1: Connection
        connBox = QGroupBox("Connection")
        connLayout = QFormLayout(connBox)
        connLayout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        self.le_scope_ip = QLineEdit("192.168.68.154")
        ip_re = QRegularExpression(r"^(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)$")
        self.le_scope_ip.setValidator(QRegularExpressionValidator(ip_re, self))
        self.le_scope_ip.setPlaceholderText("e.g. 192.168.0.10")
        self.btn_test_scope = QPushButton("Test Scope")
        
        connLayout.addRow("Scope IP:", self.le_scope_ip)
        connLayout.addRow(self.btn_test_scope)
        
        topLayout.addWidget(connBox)
        
        # Group 2: Hardware IDs
        idBox = QGroupBox("Hardware IDs")
        idLayout = QGridLayout(idBox)
        
        self.sp_vu_serial = QSpinBox()
        self.sp_vu_serial.setRange(0, 9999); self.sp_vu_serial.setValue(0)
        self.sp_vu_interface = QSpinBox()
        self.sp_vu_interface.setRange(0, 99); self.sp_vu_interface.setValue(0)
        self.sp_mcu_serial = QSpinBox()
        self.sp_mcu_serial.setRange(0, 9999); self.sp_mcu_serial.setValue(0)
        self.sp_mcu_interface = QSpinBox()
        self.sp_mcu_interface.setRange(0, 99); self.sp_mcu_interface.setValue(0)
        
        idLayout.addWidget(QLabel("VU Serial:"), 0, 0)
        idLayout.addWidget(self.sp_vu_serial, 0, 1)
        idLayout.addWidget(QLabel("VU Interf:"), 0, 2)
        idLayout.addWidget(self.sp_vu_interface, 0, 3)
        
        idLayout.addWidget(QLabel("MCU Serial:"), 1, 0)
        idLayout.addWidget(self.sp_mcu_serial, 1, 1)
        idLayout.addWidget(QLabel("MCU Interf:"), 1, 2)
        idLayout.addWidget(self.sp_mcu_interface, 1, 3)
        
        topLayout.addWidget(idBox)
        
        # Group 3: Coefficients Actions
        actBox = QGroupBox("Coefficients")
        actLayout = QVBoxLayout(actBox)
        
        self.btn_reset_coeffs = QPushButton("Reset (RAM)")
        self.btn_write_coeffs = QPushButton("Write (EEPROM)")
        
        actLayout.addWidget(self.btn_reset_coeffs)
        actLayout.addWidget(self.btn_write_coeffs)
        
        topLayout.addWidget(actBox)
        topLayout.addStretch()
        
        self.grid.addWidget(topWidget, 1, 0, 1, 1)

        # ==== Console ====
        self.console = QPlainTextEdit()
        self.console.setObjectName("console")
        self.console.setReadOnly(True)
        self.console.setUndoRedoEnabled(False)
        self.console.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )
        self.console.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.console.setMaximumBlockCount(10000)
        # Modern styling for console
        self.console.setStyleSheet("""
            QPlainTextEdit {
                background-color: #282a36;
                color: #f8f8f2;
                font-family: 'Consolas', 'Monospace';
                font-size: 10pt;
                border: 1px solid #44475a;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        self.grid.addWidget(self.console, 2, 0, 1, 1)

        self.grid.setRowStretch(2, 1)

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
        """Enable/disable controls based on busy state and scope verification.
        
        Controls are disabled when a task is running. Coefficient operations
        are only enabled when scope is verified and system is not busy.
        """
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
        self._busy = busy
        self._update_ui_state()

    def _apply_targets(self) -> None:
        """Apply current UI values to the service's target configuration.
        
        Reads scope IP, VU serial/interface, and MCU serial/interface from
        the UI widgets and updates the service's target configuration.
        """
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
        """
        Ping the oscilloscope using the service.
        """
        if not self.service:
            self._log("Service not available.")
            return

        ip = self.le_scope_ip.text().strip()
        if not ip:
            self._log("No scope IP configured.")
            return

        # Register IP with service (needed for ping and subsequent calls)
        # This will reset verification state to False if IP changed
        self.service.set_scope_ip(ip)

        # Set loading icon
        style = QApplication.style()
        self.btn_test_scope.setIcon(style.standardIcon(QStyle.SP_BrowserReload))
        self.btn_test_scope.setText("Testing...")
        self.btn_test_scope.setStyleSheet("") # Reset style

        try:
            self._set_busy(True)
            QApplication.processEvents() 
            
            # Service updates its own state, which triggers _on_scope_verified_changed
            ok = self.service.ping_scope()
            if not ok:
                # If ping failed, the state might not have changed (if it was already False),
                # so the signal might not have fired. Force UI update to show failure.
                self._on_scope_verified_changed(False)
            else:
                # If ping succeeded, the state might not have changed (if it was already True),
                # so the signal might not have fired. Force UI update to show success.
                self._on_scope_verified_changed(True)
            
        except Exception as exc:
            self._log(f"Ping failed with exception: {exc}")
            # Ensure we reflect failure if exception occurred
            self.service.set_scope_verified(False)
            self._on_scope_verified_changed(False)
        
        self._set_busy(False)

    def _on_scope_verified_changed(self, verified: bool) -> None:
        """Handle updates to scope verification state from service."""
        style = QApplication.style()
        if verified:
            self._log("Scope verified.")
            self.btn_test_scope.setIcon(style.standardIcon(QStyle.SP_DialogApplyButton))
            self.btn_test_scope.setStyleSheet("background-color: #50fa7b; color: #282a36; font-weight: bold;")
            self.btn_test_scope.setText("Connected")
        else:
            self._log("Scope verification failed or reset.")
            self.btn_test_scope.setIcon(style.standardIcon(QStyle.SP_DialogCancelButton))
            self.btn_test_scope.setStyleSheet("background-color: #ff5555; color: white; font-weight: bold;")
            self.btn_test_scope.setText("Failed")
        
        self._update_ui_state()

    def _on_reset_coeffs(self) -> None:
        """Reset calibration coefficients to default values in RAM.
        
        Sets all channel coefficients to (k=1.0, d=0.0) in the voltage unit's
        RAM only. Does NOT write to EEPROM, so changes are temporary until
        explicitly saved or power cycle.
        """
        """Trigger reset of coefficients in RAM via the service."""

        if not self.service:
            self._log("Service not available.")
            return

        self._apply_targets()
        self._set_busy(True)

        # Expect an async-style service similar to the previous design:
        task = self.service.reset_coefficients_ram()
        self._active_task = task # Keep alive
        signals = task.signals
        if not signals:
            self._log("reset_coefficients_ram() returned no signals.")
            self._set_busy(False)
            return

        signals.started.connect(lambda: self._log("Resetting coefficients (RAM)..."))
        signals.log.connect(lambda s: append_log(self.console, s))
        signals.error.connect(lambda e: self._log(f"Error: {e}"))

        def _finished(_result):
            self._log("Reset coefficients (RAM) finished.")
            self._set_busy(False)
            self._active_task = None

        signals.finished.connect(_finished)
        run_in_thread(task)

    def _on_write_coeffs_eeprom(self) -> None:
        """Write current coefficients to EEPROM for persistence.
        
        Saves the current calibration coefficients to the voltage unit's EEPROM,
        making them persistent across power cycles.
        """
        """Trigger write of coefficients to EEPROM via the service."""

        if not self.service:
            self._log("Service not available.")
            return

        self._apply_targets()
        self._set_busy(True)

        task = self.service.write_coefficients_eeprom()
        self._active_task = task  # Keep alive
        signals = task.signals
        if not signals:
            self._log("write_coefficients_eeprom() returned no signals.")
            self._set_busy(False)
            return

        signals.started.connect(lambda: self._log("Writing coefficients (EEPROM)..."))
        signals.log.connect(lambda s: append_log(self.console, s))
        signals.error.connect(lambda e: self._log(f"Error: {e}"))

        def _finished(_result):
            self._log("Write coefficients (EEPROM) finished.")
            self._set_busy(False)
            self._active_task = None
            self.le_input.setVisible(False)

        signals.finished.connect(_finished)
        run_in_thread(task)

    def _log(self, msg: str) -> None:
        append_log(self.console, msg)
