# guard_page_min.py
"""Guard signal control page for voltage unit."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from src.gui.scripts.base_page import BaseHardwarePage
from src.gui.shared_panels_widget import SharedPanelsWidget
from src.logic.vu_service import VoltageUnitService


class GuardPage(BaseHardwarePage):
    """Guard signal control page.

    Provides two literal actions matching the script's guard() function:
    - Set guard to signal
    - Set guard to ground

    WARNING: The scope must NOT be connected when setting guard to signal,
    as this can damage equipment.
    """

    def __init__(
        self,
        parent=None,
        service: VoltageUnitService | None = None,
        shared_panels: SharedPanelsWidget | None = None,
    ):
        super().__init__(parent, service, shared_panels)

        # ==== Main Layout ====
        mainLayout = QVBoxLayout(self)

        # ==== Title ====
        title = QLabel("Voltage Unit – Guard")
        title.setObjectName("title")
        mainLayout.addWidget(title)

        # ==== Info (from script) ====
        infoBox = QGroupBox("Script Note")
        infoForm = QFormLayout(infoBox)
        infoForm.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        infoForm.addRow(
            "Warning:",
            QLabel("Make sure the scope is not connected when setting a signal to the guard!"),
        )
        mainLayout.addWidget(infoBox)

        # ==== Action buttons ====
        self.btn_guard_signal = QPushButton("Set Guard → Signal")
        mainLayout.addWidget(self.btn_guard_signal)

        self.btn_guard_ground = QPushButton("Set Guard → Ground")
        mainLayout.addWidget(self.btn_guard_ground)

        # Stretch to fill remaining space
        mainLayout.addStretch()

        # Register action buttons for busy state management
        self._action_buttons = [
            self.btn_guard_signal,
            self.btn_guard_ground,
        ]

        # Wire backend actions with confirmation
        self.btn_guard_signal.clicked.connect(self._on_guard_signal)
        self.btn_guard_ground.clicked.connect(self._on_guard_ground)

        self._log("Guard page ready. Two literal actions only.")

    # ---- Handlers ----
    def _on_guard_signal(self) -> None:
        """Set output guard to signal mode.

        WARNING: Displays confirmation dialog reminding user to disconnect scope
        before proceeding, as connecting scope in signal mode can cause damage.
        """
        if not self.service:
            self._log("Service not available.")
            return
        if (
            QMessageBox.question(
                self,
                "Confirm Guard",
                "Make sure the scope is not connected when setting "
                "a signal to the guard!\n\nProceed?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            != QMessageBox.Yes
        ):
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
