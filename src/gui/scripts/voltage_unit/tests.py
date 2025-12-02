# tests_page_min.py
import os

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QWidget, QGridLayout, QLabel, QGroupBox, QFormLayout,
    QPushButton, QListView, QListWidget, QPlainTextEdit,
    QSizePolicy, QSpacerItem, QDoubleSpinBox, QSpinBox, QHBoxLayout, QMessageBox,
    QVBoxLayout, QWidget as QW, QLineEdit, QFrame
)

import setup_cal
from src.gui.utils.gui_helpers import append_log
from src.gui.utils.artifact_watcher import ArtifactWatcher
from src.logic.qt_workers import run_in_thread
from src.logic.vu_service import VoltageUnitService


class TestsPage(QWidget):
    """Test execution page for voltage unit validation.
    
    Provides controls to run individual tests (outputs, ramp, transient) or all tests
    together. Displays test results in a console and shows generated plots as thumbnails
    that update in real-time during test execution.
    
    Attributes:
        service: VoltageUnitService instance for hardware communication
        console: QPlainTextEdit widget for test output logs
        listWidget: QListWidget displaying plot thumbnails
    """
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
        self._artifact_watcher = None

        # ==== Main Layout (Vertical) ====
        mainLayout = QVBoxLayout(self)
        mainLayout.setSpacing(15)
        
        # ==== Top Section: Test Cards ====
        cardsWidget = QW()
        cardsLayout = QHBoxLayout(cardsWidget)
        cardsLayout.setContentsMargins(0, 0, 0, 0)
        cardsLayout.setSpacing(15)
        
        # -- Card 1: Outputs --
        self.btn_test_outputs = QPushButton("Run Test")
        card_outputs = self._create_test_card(
            "Outputs Test",
            ["Points: 5000", "Scale: 0.2 V/div", "Time: 1e-2 s/div"],
            self.btn_test_outputs
        )
        cardsLayout.addWidget(card_outputs)
        
        # -- Card 2: Ramp --
        self.btn_test_ramp = QPushButton("Run Test")
        card_ramp = self._create_test_card(
            "Ramp Test",
            ["Range: 500 ms", "Slope: ~20 V/s", "Sync: 1 MHz"],
            self.btn_test_ramp
        )
        cardsLayout.addWidget(card_ramp)
        
        # -- Card 3: Transient --
        self.btn_test_transient = QPushButton("Run Test")
        card_transient = self._create_test_card(
            "Transient Test",
            ["Amp: 1 V", "Step: Auto (5-20µs)", "Rec: 5000 pts"],
            self.btn_test_transient
        )
        cardsLayout.addWidget(card_transient)
        
        # -- Card 4: All --
        self.btn_test_all = QPushButton("Run All")
        # Make the "Run All" button stand out a bit
        self.btn_test_all.setStyleSheet("background-color: #6272a4; color: white; font-weight: bold;")
        card_all = self._create_test_card(
            "Full Suite",
            ["Runs all tests", "Generates all plots", "Verifies results"],
            self.btn_test_all
        )
        cardsLayout.addWidget(card_all)
        
        cardsLayout.addStretch()
        
        mainLayout.addWidget(cardsWidget)
        
        # ==== Middle Section: Console ====
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
        
        mainLayout.addWidget(self.console, 1) # Console takes available space
        
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
        self.listWidget.setProperty("isWrapping", False)
        self.listWidget.setResizeMode(QListView.ResizeMode.Adjust)
        self.listWidget.setViewMode(QListView.ViewMode.IconMode)
        self.listWidget.setFlow(QListView.Flow.LeftToRight)
        self.listWidget.setIconSize(QSize(128, 128))
        self.listWidget.setGridSize(QSize(140, 160))
        self.listWidget.setSpacing(10)
        self.listWidget.itemDoubleClicked.connect(self._on_image_double_clicked)
        
        mainLayout.addWidget(self.listWidget, 1)

        # Wire backend actions
        self.btn_test_outputs.clicked.connect(self._on_test_outputs)
        self.btn_test_ramp.clicked.connect(self._on_test_ramp)
        self.btn_test_transient.clicked.connect(self._on_test_transient)
        self.btn_test_all.clicked.connect(self._on_test_all)
        
        if self.service:
            self.service.inputRequested.connect(self._on_input_requested)
            self.service.scopeVerified.connect(self._on_scope_verified)
            # Initial state: check service, default to False
            initial_state = self.service.is_scope_verified
            self._on_scope_verified(initial_state)

        self._log("Tests page ready. Actions map 1:1 to script.")

    def _create_test_card(self, title: str, info_lines: list[str], button: QPushButton) -> QFrame:
        """Create a styled card for a test."""
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setFrameShadow(QFrame.Shadow.Raised)
        # Card styling
        card.setStyleSheet("""
            QFrame {
                background-color: #44475a;
                border-radius: 8px;
                border: 1px solid #6272a4;
            }
            QLabel {
                border: none;
                color: #f8f8f2;
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(5)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-weight: bold; font-size: 11pt; color: #8be9fd;")
        layout.addWidget(lbl_title)
        
        # Info
        for line in info_lines:
            lbl = QLabel(line)
            lbl.setStyleSheet("color: #bd93f9; font-size: 9pt;")
            layout.addWidget(lbl)
            
        layout.addStretch()
        
        # Button
        layout.addWidget(button)
        
        return card

    # ---- Helpers ----
    def _ensure_artifact_watcher(self) -> None:
        """Setup artifact watcher if VU_SERIAL is known."""
        if self._artifact_watcher or not setup_cal.VU_SERIAL:
            return
            
        artifact_dir = os.path.abspath(f"calibration_vu{setup_cal.VU_SERIAL}")
        self._artifact_watcher = ArtifactWatcher(self.listWidget, self)
    
    def _set_busy(self, busy: bool) -> None:
        """Enable or disable test control buttons based on busy state.
        
        Args:
            busy: If True, disable all test buttons. If False, enable them.
        """
        for w in (self.btn_test_outputs, self.btn_test_ramp, self.btn_test_transient, self.btn_test_all):
            w.setEnabled(not busy)

    def _start_task(self, task):
        """Start a test task with proper signal handling and lifecycle management.
        
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
            self._active_task = None
            
            # Setup watcher if not already done
            self._ensure_artifact_watcher()
            
            # Final refresh of thumbnails
            if self._artifact_watcher:
                self._artifact_watcher.refresh_thumbnails()
            
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
    def _on_test_outputs(self) -> None:
        """Run output voltage accuracy test.
        
        Tests DC output voltage accuracy at multiple setpoints (-0.75V to +0.75V)
        and measures offset errors. Generates output.png plot.
        """
        if not self.service:
            self._log("Service not available.")
            return
        self._start_task(self.service.test_outputs())

    def _on_test_ramp(self) -> None:
        """Run voltage ramp test.
        
        Tests dynamic voltage ramping capability and slope accuracy.
        Generates ramp.png plot showing measured vs. ideal ramp.
        """
        if not self.service:
            self._log("Service not available.")
            return
        self._start_task(self.service.test_ramp())

    def _on_test_transient(self) -> None:
        """Run transient response test.
        
        Tests voltage step response, settling time, and overshoot.
        Generates transient.png plot.
        """
        if not self.service:
            self._log("Service not available.")
            return
        self._start_task(self.service.test_transient())

    def _on_test_all(self) -> None:
        """Run all tests sequentially (outputs, ramp, transient).
        
        Executes the complete test suite and generates all diagnostic plots.
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
        """Send input back to service."""
        text = self.le_input.text()
        self._log(f"> {text}")
        self.le_input.clear()
        self.le_input.setVisible(False)
        if self.service:
            self.service.provide_input(text)

    def _on_scope_verified(self, verified: bool):
        """Enable/disable actions based on scope connection."""
        self.btn_test_outputs.setEnabled(verified)
        self.btn_test_ramp.setEnabled(verified)
        self.btn_test_transient.setEnabled(verified)
        self.btn_test_all.setEnabled(verified)
        if not verified:
            self._log("Actions disabled: Scope not verified.")
        else:
            self._log("Actions enabled: Scope verified.")

    def _log(self, msg: str):
        append_log(self.console, msg)
