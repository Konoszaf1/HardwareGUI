# session_and_coeffs_page_min.py
from PySide6.QtCore import Qt, QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QWidget,
    QGridLayout,
    QLabel,
    QGroupBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QHBoxLayout,
    QPushButton,
    QPlainTextEdit,
    QWidget as QW,
)

from src.gui.utils.gui_helpers import append_log
from src.logic.vu_service import VoltageUnitService


class SessionAndCoeffsPage(QWidget):
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

        # ==== Top: constants / IDs ====
        topBox = QGroupBox("Required Parameters")
        topForm = QFormLayout(topBox)
        topForm.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Scope IP (constant in script)
        self.le_scope_ip = QLineEdit("192.168.68.154")
        ip_re = QRegularExpression(
            r"^(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)$"
        )
        self.le_scope_ip.setValidator(QRegularExpressionValidator(ip_re, self))
        self.le_scope_ip.setPlaceholderText("e.g. 192.168.0.10")
        topForm.addRow("Scope IP (SCOPE_IP):", self.le_scope_ip)

        # Device IDs (0 means autodetect in the script)
        idRow = QHBoxLayout()
        self.sp_vu_serial = QSpinBox()
        self.sp_vu_serial.setRange(0, 9999)
        self.sp_vu_serial.setValue(0)
        self.sp_vu_interface = QSpinBox()
        self.sp_vu_interface.setRange(0, 99)
        self.sp_vu_interface.setValue(0)
        self.sp_mcu_serial = QSpinBox()
        self.sp_mcu_serial.setRange(0, 9999)
        self.sp_mcu_serial.setValue(0)
        self.sp_mcu_interface = QSpinBox()
        self.sp_mcu_interface.setRange(0, 99)
        self.sp_mcu_interface.setValue(0)

        idRow.addWidget(QLabel("VU serial:"))
        idRow.addWidget(self.sp_vu_serial)
        idRow.addWidget(QLabel("VU interf:"))
        idRow.addWidget(self.sp_vu_interface)
        idRow.addSpacing(12)
        idRow.addWidget(QLabel("MCU serial:"))
        idRow.addWidget(self.sp_mcu_serial)
        idRow.addWidget(QLabel("MCU interf:"))
        idRow.addWidget(self.sp_mcu_interface)
        idRow.addStretch()
        idRowWidget = QW()
        idRowWidget.setLayout(idRow)
        topForm.addRow("Device IDs (0 = auto):", idRowWidget)

        # Scope status indicator (uses ✔ / ✖)
        self.lbl_scope_status = QLabel("—")
        self.lbl_scope_status.setAlignment(Qt.AlignCenter)
        self._set_scope_status(None)
        topForm.addRow("Scope status:", self.lbl_scope_status)

        # Actions row: test scope + reset coefficients
        actionsRow = QHBoxLayout()
        self.btn_test_scope = QPushButton("Test Scope")
        self.btn_reset_coeffs = QPushButton("Reset Coefficients (RAM)")
        actionsRow.addWidget(self.btn_test_scope)
        actionsRow.addWidget(self.btn_reset_coeffs)
        actionsRow.addStretch()
        actionsWidget = QW()
        actionsWidget.setLayout(actionsRow)
        topForm.addRow("Actions:", actionsWidget)

        self.grid.addWidget(topBox, 1, 0, 1, 1)

        # ==== Console only ====
        self.console = QPlainTextEdit()
        self.console.setObjectName("console")
        self.console.setReadOnly(True)
        self.console.setUndoRedoEnabled(False)
        self.console.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )
        self.console.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.console.setMaximumBlockCount(10000)
        self.grid.addWidget(self.console, 2, 0, 1, 1)

        self.grid.setRowStretch(2, 1)

        # Wire backend actions
        self.btn_test_scope.clicked.connect(self._on_test_scope)
        self.btn_reset_coeffs.clicked.connect(self._on_reset_coeffs)

        self._log("Session page ready. Configure targets and use the actions above.")

    # ---- Wiring helpers ----
    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        for w in (self.btn_test_scope, self.btn_reset_coeffs):
            w.setEnabled(not busy)

    def _set_scope_status(self, ok: bool | None) -> None:
        """
        Update scope status label.

        ok=True   -> green check
        ok=False  -> red cross
        ok=None   -> neutral / unknown
        """
        if ok is True:
            self.lbl_scope_status.setText("✔ Connected")
            self.lbl_scope_status.setStyleSheet("color: green; font-weight: bold;")
        elif ok is False:
            self.lbl_scope_status.setText("✖ Not reachable")
            self.lbl_scope_status.setStyleSheet("color: red; font-weight: bold;")
        else:
            self.lbl_scope_status.setText("—")
            self.lbl_scope_status.setStyleSheet("color: gray;")

    def _apply_targets(self) -> None:
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

        Expects: service.ping_scope(ip: str) -> bool
        """

        if not self.service:
            self._log("Service not available.")
            return

        ip = self.le_scope_ip.text().strip()
        if not ip:
            self._log("No scope IP configured.")
            self._set_scope_status(False)
            return

        try:
            self._set_busy(True)
            ok = self.service.ping_scope(ip)
        except Exception as exc:
            self._log(f"Ping failed with exception: {exc}")
            self._set_scope_status(False)
            self._set_busy(False)
            return

        self._set_scope_status(bool(ok))
        self._log("Scope reachable." if ok else "Scope not reachable.")
        self._set_busy(False)

    def _on_reset_coeffs(self) -> None:
        """Trigger reset of coefficients in RAM via the service."""

        if not self.service:
            self._log("Service not available.")
            return

        self._apply_targets()
        self._set_busy(True)

        # Expect an async-style service similar to the previous design:
        signals = self.service.reset_coefficients_ram()
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

        signals.finished.connect(_finished)

    def _log(self, msg: str) -> None:
        self.console.appendPlainText(msg)
