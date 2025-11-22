# tests_page_min.py
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QWidget, QGridLayout, QLabel, QGroupBox, QFormLayout,
    QPushButton, QListView, QListWidget, QPlainTextEdit,
    QSizePolicy, QSpacerItem, QDoubleSpinBox, QSpinBox, QHBoxLayout, QMessageBox,
    QVBoxLayout, QWidget as QW, QLineEdit
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

        # ==== Main Layout (Vertical) ====
        mainLayout = QVBoxLayout(self)
        
        # ==== Top Section ====
        topWidget = QW()
        topLayout = QHBoxLayout(topWidget)
        topLayout.setContentsMargins(0, 0, 0, 0)
        
        # -- Left: Controls --
        controlsBox = QGroupBox("Test Actions")
        controlsLayout = QVBoxLayout(controlsBox)
        
        self.btn_test_outputs = QPushButton("Test: Outputs")
        self.btn_test_ramp = QPushButton("Test: Ramp")
        self.btn_test_transient = QPushButton("Test: Transient")
        self.btn_test_all = QPushButton("Test: All")
        
        controlsLayout.addWidget(self.btn_test_outputs)
        controlsLayout.addWidget(self.btn_test_ramp)
        controlsLayout.addWidget(self.btn_test_transient)
        controlsLayout.addWidget(self.btn_test_all)
        controlsLayout.addStretch()
        
        # Info box (compact)
        infoBox = QGroupBox("Constants")
        infoForm = QFormLayout(infoBox)
        infoForm.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        infoForm.addRow("Out pts:", QLabel("5000"))
        infoForm.addRow("Ramp:", QLabel("500 ms"))
        infoForm.addRow("Trans amp:", QLabel("1 V"))
        
        controlsLayout.addWidget(infoBox)
        
        topLayout.addWidget(controlsBox, 1)
        
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

    def _on_image_double_clicked(self, item):
        """Open the image viewer dialog."""
        path = item.data(Qt.UserRole)
        if path:
            from src.gui.utils.image_viewer import ImageViewerDialog
            dlg = ImageViewerDialog(path, self)
            dlg.exec()

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
