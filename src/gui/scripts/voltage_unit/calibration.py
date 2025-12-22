# calibration_page_min.py
import os

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QWidget, QGridLayout, QLabel, QGroupBox, QFormLayout,
    QPushButton, QListView, QListWidget, QPlainTextEdit,
    QSizePolicy, QSpacerItem, QVBoxLayout, QHBoxLayout,
    QWidget as QW, QLineEdit
)

import setup_cal
from src.gui.utils.gui_helpers import append_log
from src.gui.utils.artifact_watcher import ArtifactWatcher
from src.logic.qt_workers import run_in_thread
from src.logic.vu_service import VoltageUnitService


class CalibrationPage(QWidget):
    """
    Mandatory controls only, matching the script’s calibration entries and constants.
    No extra thresholds or plot/UI toggles beyond what’s literally used.
    """
    def __init__(self, parent=None, service: VoltageUnitService | None = None):
        super().__init__(parent)
        self.service = service
        self._artifact_watcher = None

        # ==== Main Layout (Vertical) ====
        # Top: Splitter (Controls | Console)
        # Bottom: Image List
        mainLayout = QVBoxLayout(self)
        
        # ==== Title ====
        title = QLabel("Voltage Unit – Calibration")
        title.setObjectName("title")
        mainLayout.addWidget(title)
        
        # ==== Top Section ====
        topWidget = QW()
        topLayout = QHBoxLayout(topWidget)
        topLayout.setContentsMargins(0, 0, 0, 0)
        
        # -- Left: Controls --
        controlsBox = QGroupBox("Calibration Actions")
        controlsLayout = QVBoxLayout(controlsBox)
        
        self.btn_run_autocal_python = QPushButton("Run Autocalibration (Python)")
        self.btn_run_autocal_onboard = QPushButton("Run Autocalibration (Onboard)")
        self.btn_test_all = QPushButton("Test: All")
        
        controlsLayout.addWidget(self.btn_run_autocal_python)
        controlsLayout.addWidget(self.btn_run_autocal_onboard)
        controlsLayout.addWidget(self.btn_test_all)
        controlsLayout.addStretch()
        
        # Info box (compact)
        infoBox = QGroupBox("Constants")
        infoForm = QFormLayout(infoBox)
        infoForm.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        infoForm.addRow("Max iter:", QLabel("10"))
        infoForm.addRow("Offset:", QLabel("2 mV"))
        infoForm.addRow("Slope err:", QLabel("0.1 %"))
        
        controlsLayout.addWidget(infoBox)
        
        topLayout.addWidget(controlsBox, 1) # Stretch factor 1
        
        # -- Right: Console --
        self.console = QPlainTextEdit()
        self.console.setObjectName("console")
        self.console.setReadOnly(True)
        self.console.setUndoRedoEnabled(False)
        self.console.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.console.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.console.setMaximumBlockCount(20000)
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
        
        topLayout.addWidget(self.console, 2)
        
        mainLayout.addWidget(topWidget, 2)
        
        # Input field (hidden by default)
        self.le_input = QLineEdit()
        self.le_input.setPlaceholderText("Type input here and press Enter...")
        self.le_input.setVisible(False)
        self.le_input.returnPressed.connect(self._on_input_return)
        mainLayout.addWidget(self.le_input)
        
        # ==== Bottom Section: Images ====
        self.listWidget = QListWidget()
        self.listWidget.setObjectName("artifacts")
        self.listWidget.setMovement(QListView.Movement.Static)
        self.listWidget.setProperty("isWrapping", False) # Horizontal scroll
        self.listWidget.setResizeMode(QListView.ResizeMode.Adjust)
        self.listWidget.setViewMode(QListView.ViewMode.IconMode)
        self.listWidget.setFlow(QListView.Flow.LeftToRight) # Horizontal flow
        self.listWidget.setIconSize(QSize(128, 128))
        self.listWidget.setGridSize(QSize(140, 160))
        self.listWidget.setSpacing(10)
        # Connect double click
        self.listWidget.itemDoubleClicked.connect(self._on_image_double_clicked)
        
        mainLayout.addWidget(self.listWidget, 1)

        # Wire backend actions
        self.btn_run_autocal_python.clicked.connect(self._on_autocal_python)
        self.btn_run_autocal_onboard.clicked.connect(self._on_autocal_onboard)
        self.btn_test_all.clicked.connect(self._on_test_all)
        
        if self.service:
            self.service.inputRequested.connect(self._on_input_requested)
            self.service.scopeVerified.connect(self._on_scope_verified)
            # Initial state: check service, default to False
            initial_state = self.service.is_scope_verified
            self._on_scope_verified(initial_state)

        self._log("Calibration page ready. Actions map 1:1 to script.")

    # ---- Helpers ----
    def _ensure_artifact_watcher(self) -> None:
        """Setup artifact watcher if VU_SERIAL is known and watcher not already created.
        
        The watcher monitors the calibration artifact directory and automatically updates
        thumbnails when plot files are created or modified.
        """
        if self._artifact_watcher or not setup_cal.VU_SERIAL:
            return
            
        artifact_dir = os.path.abspath(f"calibration_vu{setup_cal.VU_SERIAL}")
        self._artifact_watcher = ArtifactWatcher(self.listWidget, self)
        self._artifact_watcher.setup(artifact_dir)
    
    def _set_busy(self, busy: bool) -> None:
        """Enable or disable UI controls based on busy state.
        
        Args:
            busy: If True, disable buttons. If False, enable them.
        """
        for w in (self.btn_run_autocal_python, self.btn_run_autocal_onboard, self.btn_test_all):
            w.setEnabled(not busy)

    def _start_task(self, task):
        """Start a calibration task with proper signal handling and lifecycle management.
        
        This method:
        - Keeps the task alive to prevent premature garbage collection
        - Sets up artifact watcher for real-time thumbnail updates
        - Connects all task signals (started, log, error, finished)
        - Runs the task in a background thread
        
        Args:
            task: FunctionTask instance returned from VoltageUnitService
        """
        if not task:
            return
        
        # Keep task alive
        self._active_task = task
        
        # Setup watcher before task starts (if VU_SERIAL is known)
        self._ensure_artifact_watcher()
        
        signals = task.signals
        self._set_busy(True)
        signals.started.connect(lambda: self._log("Started."))
        signals.log.connect(lambda s: append_log(self.console, s))
        signals.error.connect(lambda e: self._log(f"Error: {e}"))

        def _finished(result):
            self._set_busy(False)
            self._active_task = None  # Release task
            
            # Setup watcher if not already done
            self._ensure_artifact_watcher()
            
            # Final refresh of thumbnails
            if self._artifact_watcher:
                self._artifact_watcher.refresh_thumbnails()
            
            data = getattr(result, "data", None)
            if isinstance(data, dict):
                coeffs = data.get("coeffs")
                if coeffs:
                    for ch, (k, d) in coeffs.items():
                        self._log(f"Coeff {ch}: k={k:.6f}, d={d:.6f}")
            self._log("Finished.")

        signals.finished.connect(_finished)
        run_in_thread(task)

    def _on_image_double_clicked(self, item):
        """Open the image viewer dialog."""
        path = item.data(Qt.UserRole)
        if path:
            from src.gui.utils.image_viewer import ImageViewerDialog
            dlg = ImageViewerDialog(path, self)
            dlg.exec()

    # ---- Handlers ----
    def _on_autocal_python(self) -> None:
        """Run Python-based autocalibration.
        
        Performs iterative calibration using the setup_cal.auto_calibrate function,
        which runs up to 10 iterations of ramp and output tests to converge on
        optimal coefficients.
        """
        if not self.service:
            self._log("Service not available.")
            return
        self._start_task(self.service.autocal_python())

    def _on_autocal_onboard(self) -> None:
        """Run onboard (firmware) autocalibration.
        
        Uses the hardware's built-in calibration routine, which is typically
        faster but may be less flexible than the Python implementation.
        """
        if not self.service:
            self._log("Service not available.")
            return
        self._start_task(self.service.autocal_onboard())

    def _on_test_all(self) -> None:
        """Run all calibration tests (outputs, ramp, transient).
        
        Executes a comprehensive test suite to verify voltage unit performance
        across different operating modes.
        """
        if not self.service:
            self._log("Service not available.")
            return
        self._start_task(self.service.test_all())

    def _on_input_requested(self, prompt: str):
        """Show input field when service requests input."""
        if not self.isVisible():
            return
        self._log(f"<b>Input requested:</b> {prompt}")
        self.le_input.setVisible(True)
        self.le_input.setPlaceholderText(prompt if prompt else "Type input here...")
        self.le_input.setFocus()

    def _on_input_return(self):
        """Send input back to the service."""
        text = self.le_input.text()
        self._log(f"> {text}")
        self.le_input.clear()
        self.le_input.setVisible(False)
        if self.service:
            self.service.provide_input(text)

    def _on_scope_verified(self, verified: bool):
        """Enable/disable actions based on scope connection."""
        self.btn_run_autocal_python.setEnabled(verified)
        self.btn_run_autocal_onboard.setEnabled(verified)
        self.btn_test_all.setEnabled(verified)
        if not verified:
            self._log("Actions disabled: Scope not verified.")
        else:
            self._log("Actions enabled: Scope verified.")

    def _log(self, msg: str):
        """Append a message to the console widget.
        
        Args:
            msg: Message to display in the console
        """
        append_log(self.console, msg)
