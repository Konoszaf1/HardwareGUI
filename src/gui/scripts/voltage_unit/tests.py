# tests_page_min.py
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QGridLayout, QLabel, QGroupBox, QFormLayout,
    QPushButton, QListView, QListWidget, QPlainTextEdit,
    QSizePolicy, QSpacerItem, QDoubleSpinBox, QSpinBox, QHBoxLayout, QMessageBox
)

from src.gui.utils.gui_helpers import append_log, add_thumbnail_item
from src.logic.vu_service import VoltageUnitService


class TestsPage(QWidget):
    """
    Minimal page for literal test actions:
    - test_outputs
    - test_ramp
    - test_transient
    Each control corresponds directly to hard-coded parameters in the script.
    No new tuning or abstractions added.
    """
    def __init__(self, parent=None, service: VoltageUnitService | None = None):
        super().__init__(parent)
        self.service = service

        # ==== Root grid ====
        self.grid = QGridLayout(self)
        self.grid.setObjectName("grid")

        # ==== Title ====
        title = QLabel("Voltage Unit – Tests (Minimal)")
        title.setObjectName("title")
        self.grid.addWidget(title, 0, 0, 1, 2)

        # ==== Top: constants used by tests ====
        constBox = QGroupBox("Script Constants (for reference)")
        constForm = QFormLayout(constBox)
        constForm.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Values as defined in test_outputs / test_ramp / test_transient
        constForm.addRow("Output voltages:", QLabel("−0.75, −0.5, −0.25, 0, 0.25, 0.5, 0.75"))
        constForm.addRow("Output CH scales:", QLabel("CH1=0.20 V/div, CH2=0.20 V/div, CH3=0.20 V/div"))
        constForm.addRow("Output time scale:", QLabel("1e−2 s/div"))
        constForm.addRow("Output points:", QLabel("5000"))
        constForm.addRow("Ramp scales:", QLabel("Derived from VU amplification (±20 V/s nominal)"))
        constForm.addRow("Ramp time range:", QLabel("500 ms"))
        constForm.addRow("Transient amplitude:", QLabel("1 V"))
        constForm.addRow("Transient timestep:", QLabel("auto (5e−6 s; 20e−6 s if 20-bit DAC)"))
        self.grid.addWidget(constBox, 1, 0, 1, 2)

        # ==== Left: literal test buttons ====
        self.btn_test_outputs = QPushButton("Test: Outputs")
        self.grid.addWidget(self.btn_test_outputs, 2, 0, 1, 1)

        self.btn_test_ramp = QPushButton("Test: Ramp")
        self.grid.addWidget(self.btn_test_ramp, 3, 0, 1, 1)

        self.btn_test_transient = QPushButton("Test: Transient")
        self.grid.addWidget(self.btn_test_transient, 4, 0, 1, 1)

        self.btn_test_all = QPushButton("Test: All")
        self.grid.addWidget(self.btn_test_all, 5, 0, 1, 1)

        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.grid.addItem(spacer, 6, 0, 1, 1)

        # ==== Right: artifact list + console ====
        self.listWidget = QListWidget()
        self.listWidget.setObjectName("artifacts")
        self.listWidget.setMovement(QListView.Movement.Static)
        self.listWidget.setProperty("isWrapping", False)
        self.listWidget.setResizeMode(QListView.ResizeMode.Adjust)
        self.listWidget.setViewMode(QListView.ViewMode.IconMode)
        self.grid.addWidget(self.listWidget, 2, 1, 2, 1)

        self.console = QPlainTextEdit()
        self.console.setObjectName("console")
        self.console.setReadOnly(True)
        self.console.setUndoRedoEnabled(False)
        self.console.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.console.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.console.setMaximumBlockCount(20000)
        self.grid.addWidget(self.console, 4, 1, 3, 1)

        self.grid.setColumnStretch(1, 1)
        self.grid.setRowStretch(4, 2)
        self.grid.setRowStretch(6, 2)

        # Wire backend actions
        self.btn_test_outputs.clicked.connect(self._on_test_outputs)
        self.btn_test_ramp.clicked.connect(self._on_test_ramp)
        self.btn_test_transient.clicked.connect(self._on_test_transient)
        self.btn_test_all.clicked.connect(self._on_test_all)

        self._log("Tests page ready. Actions map 1:1 to script.")

    # ---- Helpers ----
    def _set_busy(self, busy: bool) -> None:
        for w in (self.btn_test_outputs, self.btn_test_ramp, self.btn_test_transient, self.btn_test_all):
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
                arts = data.get("artifacts") or []
                for p in arts:
                    add_thumbnail_item(self.listWidget, p)
            self._log("Finished.")

        signals.finished.connect(_finished)

    # ---- Handlers ----
    def _on_test_outputs(self) -> None:
        if not self.service:
            self._log("Service not available.")
            return
        self._start_task(self.service.test_outputs())

    def _on_test_ramp(self) -> None:
        if not self.service:
            self._log("Service not available.")
            return
        self._start_task(self.service.test_ramp())

    def _on_test_transient(self) -> None:
        if not self.service:
            self._log("Service not available.")
            return
        self._start_task(self.service.test_transient())

    def _on_test_all(self) -> None:
        if not self.service:
            self._log("Service not available.")
            return
        self._start_task(self.service.test_all())

    def _log(self, msg: str):
        self.console.appendPlainText(msg)
