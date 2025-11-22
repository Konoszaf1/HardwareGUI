# calibration_page_min.py
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QWidget, QGridLayout, QLabel, QGroupBox, QFormLayout,
    QPushButton, QListView, QListWidget, QPlainTextEdit,
    QSizePolicy, QSpacerItem, QVBoxLayout, QHBoxLayout,
    QWidget as QW, QLineEdit
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

        # ==== Main Layout (Vertical) ====
        # Top: Splitter (Controls | Console)
        # Bottom: Image List
        mainLayout = QVBoxLayout(self)
        
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
        
        topLayout.addWidget(self.console, 2) # Stretch factor 2 (wider console)
        
        mainLayout.addWidget(topWidget, 2) # Top section takes 2/3 height
        
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
        
        mainLayout.addWidget(self.listWidget, 1) # Bottom section takes 1/3 height

        # Wire backend actions
        self.btn_run_autocal_python.clicked.connect(self._on_autocal_python)
        self.btn_run_autocal_onboard.clicked.connect(self._on_autocal_onboard)
        self.btn_test_all.clicked.connect(self._on_test_all)
        
        if self.service:
            self.service.inputRequested.connect(self._on_input_requested)

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

    def _on_image_double_clicked(self, item):
        """Open the image viewer dialog."""
        path = item.data(Qt.UserRole)
        if path:
            from src.gui.utils.image_viewer import ImageViewerDialog
            dlg = ImageViewerDialog(path, self)
            dlg.exec()

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

    def _log(self, msg: str):
        append_log(self.console, msg)
