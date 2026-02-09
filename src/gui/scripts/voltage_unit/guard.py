"""Guard signal control page for voltage unit."""

from PySide6.QtWidgets import (
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.gui.scripts.base_page import BaseHardwarePage
from src.gui.shared_panels_widget import SharedPanelsWidget
from src.logic.services.vu_service import VoltageUnitService


class VUGuardPage(BaseHardwarePage):
    """Guard signal control page.

    Provides two literal actions matching the script's guard() function:
    - Set guard to signal
    - Set guard to ground

    WARNING: The scope must NOT be connected when setting guard to signal,
    as this can damage equipment.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        service: VoltageUnitService | None = None,
        shared_panels: SharedPanelsWidget | None = None,
    ):
        """Initialize the VUGuardPage.

        Args:
            parent (QWidget | None): Parent widget.
            service (VoltageUnitService | None): Service for voltage unit operations.
            shared_panels (SharedPanelsWidget | None): Shared panels for logs/artifacts.
        """
        super().__init__(parent, service, shared_panels)

        # ==== Main Layout (Vertical) ====
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll, content, main_layout = self._create_scroll_area(min_width=400)
        outer_layout.addWidget(scroll)

        # ==== Title ====
        title = QLabel("Voltage Unit – Guard")
        title.setObjectName("title")
        main_layout.addWidget(title)

        # ==== Info (from script) ====
        info_box = self._create_group_box("Script Note", min_height=100, expanding=False)
        info_form = self._create_form_layout(info_box)

        info_form.addRow(
            "Warning:",
            QLabel("Make sure the scope is not connected when setting a signal to the guard!"),
        )
        main_layout.addWidget(info_box)

        # ==== Action buttons ====
        self.btn_guard_signal = QPushButton("Set Guard → Signal")
        self._configure_input(self.btn_guard_signal)
        main_layout.addWidget(self.btn_guard_signal)

        self.btn_guard_ground = QPushButton("Set Guard → Ground")
        self._configure_input(self.btn_guard_ground)
        main_layout.addWidget(self.btn_guard_ground)

        # Stretch to fill remaining space
        main_layout.addStretch()

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
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            != QMessageBox.StandardButton.Yes
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
