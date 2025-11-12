# calibration_page_min.py
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QGridLayout, QLabel, QGroupBox, QFormLayout,
    QPushButton, QListView, QListWidget, QPlainTextEdit,
    QSizePolicy, QSpacerItem
)

from src.gui.utils.gui_helpers import append_log, add_thumbnail_item
from src.logic.vu_service import VoltageUnitService


class CalibrationPage(QWidget):
    """
    Mandatory controls only, matching the script’s calibration entries and constants.
    No extra thresholds or plot/UI toggles beyond what’s literally used.
    """
    def __init__(self, parent=None, service: VoltageUnitService | None = None):
        super().__init__(parent)
        self.service = service

        # ==== Root grid ====
        self.grid = QGridLayout(self)
        self.grid.setObjectName("grid")

        # ==== Title ====
        title = QLabel("Voltage Unit – Calibration (Minimal)")
        title.setObjectName("title")
        self.grid.addWidget(title, 0, 0, 1, 2)

        # ==== Info: constants used by the script (read-only labels) ====
        infoBox = QGroupBox("Script Constants (for reference)")
        infoForm = QFormLayout(infoBox)
        infoForm.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Values are hard-coded in the script; shown for clarity only
        infoForm.addRow("Max iterations:", QLabel("10"))
        infoForm.addRow("Offset threshold:", QLabel("2 mV"))
        infoForm.addRow("Ramp slope error:", QLabel("0.1 %"))
        infoForm.addRow("Outputs time scale:", QLabel("1e-2 s/div"))
        infoForm.addRow("Outputs acq. points:", QLabel("5000"))
        infoForm.addRow("Ramp time range:", QLabel("500e-3 s"))
        self.grid.addWidget(infoBox, 1, 0, 1, 2)

        # ==== Left: literal calibration actions ====
        self.btn_run_autocal_python = QPushButton("Run Autocalibration (Python)")
        self.grid.addWidget(self.btn_run_autocal_python, 2, 0, 1, 1)

        self.btn_run_autocal_onboard = QPushButton("Run Autocalibration (Onboard)")
        self.grid.addWidget(self.btn_run_autocal_onboard, 3, 0, 1, 1)

        self.btn_test_all = QPushButton("Test: All")
        self.grid.addWidget(self.btn_test_all, 4, 0, 1, 1)

        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.grid.addItem(spacer, 5, 0, 1, 1)

        # ==== Right: artifacts + console ====
        self.listWidget = QListWidget()
        self.listWidget.setObjectName("artifacts")
        self.listWidget.setMovement(QListView.Movement.Static)
        self.listWidget.setProperty("isWrapping", False)
        self.listWidget.setResizeMode(QListView.ResizeMode.Adjust)
        self.listWidget.setViewMode(QListView.ViewMode.IconMode)
        self.grid.addWidget(self.listWidget, 2, 1, 1, 1)

        self.console = QPlainTextEdit()
        self.console.setObjectName("console")
        self.console.setReadOnly(True)
        self.console.setUndoRedoEnabled(False)
        self.console.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.console.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.console.setMaximumBlockCount(20000)
        self.grid.addWidget(self.console, 3, 1, 3, 1)

        self.grid.setColumnStretch(1, 1)
        self.grid.setRowStretch(3, 2)
        self.grid.setRowStretch(5, 2)

        # Wire backend actions
        self.btn_run_autocal_python.clicked.connect(self._on_autocal_python)
        self.btn_run_autocal_onboard.clicked.connect(self._on_autocal_onboard)
        self.btn_test_all.clicked.connect(self._on_test_all)

        self._log("Calibration page ready. Actions map 1:1 to script.")

    # ---- Helpers ----
    def _set_busy(self, busy: bool) -> None:
        for w in (self.btn_run_autocal_python, self.btn_run_autocal_onboard, self.btn_test_all):
            w.setEnabled(not busy)

    def _start_task(self, signals):
        if not signals:
            return
        self._set_busy(True)
        signals.started.connect(lambda: self._log("Started."))
        signals.log.connect(lambda s: append_log(self.console, s))
        signals.error.connect(lambda e: self._log(f"Error: {e}"))

        def _finished(result):
            self._set_busy(False)
            data = getattr(result, "data", None)
            if isinstance(data, dict):
                coeffs = data.get("coeffs")
                if coeffs:
                    for ch, (k, d) in coeffs.items():
                        self._log(f"Coeff {ch}: k={k:.6f}, d={d:.6f}")
                arts = data.get("artifacts") or []
                for p in arts:
                    add_thumbnail_item(self.listWidget, p)
            self._log("Finished.")

        signals.finished.connect(_finished)

    # ---- Handlers ----
    def _on_autocal_python(self) -> None:
        if not self.service:
            self._log("Service not available.")
            return
        self._start_task(self.service.autocal_python())

    def _on_autocal_onboard(self) -> None:
        if not self.service:
            self._log("Service not available.")
            return
        self._start_task(self.service.autocal_onboard())

    def _on_test_all(self) -> None:
        if not self.service:
            self._log("Service not available.")
            return
        self._start_task(self.service.test_all())

    def _log(self, msg: str):
        self.console.appendPlainText(msg)
