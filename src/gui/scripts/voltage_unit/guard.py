# guard_page_min.py
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QGridLayout, QLabel, QGroupBox, QFormLayout,
    QPushButton, QPlainTextEdit, QSizePolicy, QSpacerItem, QMessageBox
)

from src.gui.utils.gui_helpers import append_log
from src.logic.qt_workers import run_in_thread
from src.logic.vu_service import VoltageUnitService


class GuardPage(QWidget):
    """Guard signal control page.
    
    Provides two literal actions matching the script's guard() function:
    - Set guard to signal  
    - Set guard to ground
    
    WARNING: The scope must NOT be connected when setting guard to signal,
    as this can damage equipment.
    
    Attributes:
        service: VoltageUnitService instance for hardware communication
        console: QPlainTextEdit widget for operation logs
    """
    """
    Minimal guard control matching the script's `guard(vu, scope)` choices.
    No extra options; two literal actions only.
    """
    def __init__(self, parent=None, service: VoltageUnitService | None = None):
        super().__init__(parent)
        self.service = service

        # ==== Root grid ====
        self.grid = QGridLayout(self)
        self.grid.setObjectName("grid")

        # ==== Title ====
        title = QLabel("Voltage Unit – Guard (Minimal)")
        title.setObjectName("title")
        self.grid.addWidget(title, 0, 0, 1, 2)

        # ==== Info (from script) ====
        infoBox = QGroupBox("Script Note")
        infoForm = QFormLayout(infoBox)
        infoForm.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        infoForm.addRow("Warning:", QLabel("Make sure the scope is not connected when setting a signal to the guard!"))
        self.grid.addWidget(infoBox, 1, 0, 1, 2)

        # ==== Left: literal actions ====
        self.btn_guard_signal = QPushButton("Set Guard → Signal")
        self.grid.addWidget(self.btn_guard_signal, 2, 0, 1, 1)

        self.btn_guard_ground = QPushButton("Set Guard → Ground")
        self.grid.addWidget(self.btn_guard_ground, 3, 0, 1, 1)

        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.grid.addItem(spacer, 4, 0, 1, 1)

        # ==== Right: console ====
        self.console = QPlainTextEdit()
        self.console.setObjectName("console")
        self.console.setReadOnly(True)
        self.console.setUndoRedoEnabled(False)
        self.console.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.console.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.console.setMaximumBlockCount(10000)
        self.grid.addWidget(self.console, 2, 1, 3, 1)

        self.grid.setColumnStretch(1, 1)
        self.grid.setRowStretch(3, 2)
        self.grid.setRowStretch(4, 2)

        # Wire backend actions with confirmation
        self.btn_guard_signal.clicked.connect(self._on_guard_signal)
        self.btn_guard_ground.clicked.connect(self._on_guard_ground)

        self._log("Guard page ready. Two literal actions only.")

    def _set_busy(self, busy: bool) -> None:
        self.btn_guard_signal.setEnabled(not busy)
        self.btn_guard_ground.setEnabled(not busy)

    def _start_task(self, task):
        """Start a guard configuration task with signal handling.
        
        Args:
            task: FunctionTask instance returned from VoltageUnitService
        """
        if not task:
            return

        self._active_task = task
        signals = task.signals
        self._set_busy(True)
        signals.started.connect(lambda: self._log("Started."))
        signals.log.connect(lambda s: append_log(self.console, s))
        signals.error.connect(lambda e: self._log(f"Error: {e}"))
        signals.finished.connect(lambda _: (self._set_busy(False), setattr(self, "_active_task", None), self._log("Finished.")))
        run_in_thread(task)

    def _on_guard_signal(self) -> None:
        """Set output guard to signal mode.
        
        WARNING: Displays confirmation dialog reminding user to disconnect scope
        before proceeding, as connecting scope in signal mode can cause damage.
        """
        if not self.service:
            self._log("Service not available.")
            return
        if QMessageBox.question(self, "Confirm Guard",
                                "Make sure the scope is not connected when setting a signal to the guard!\n\nProceed?",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        self._start_task(self.service.set_guard_signal())

    def _on_guard_ground(self) -> None:
        """Set output guard to ground mode.
        
        This is the safe default mode for normal operation.
        """
        if not self.service:
            self._log("Service not available.")
            return
        self._start_task(self.service.set_guard_ground())

    def _log(self, msg: str):
        self.console.appendPlainText(msg)
