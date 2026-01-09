"""Calibration fit page for Sampling Unit."""

from PySide6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.gui.scripts.base_page import BaseHardwarePage
from src.gui.shared_panels_widget import SharedPanelsWidget
from src.gui.styles import Styles
from src.logic.services.su_service import SamplingUnitService


class SUCalFitPage(BaseHardwarePage):
    """Calibration fit page for SU.

    Provides controls for:
    - Running calibration fit (trains linear and GP models)
    - Generating calibration plots
    - Writing calibration to EEPROM via SMU
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        service: SamplingUnitService | None = None,
        shared_panels: SharedPanelsWidget | None = None,
    ):
        """Initialize the SUCalFitPage.

        Args:
            parent: Parent widget.
            service: SU service instance.
            shared_panels: Shared panels for logs/artifacts.
        """
        super().__init__(parent, service, shared_panels)

        # ==== Main Layout ====
        main_layout = QVBoxLayout(self)

        # ==== Title ====
        title = QLabel("Sampling Unit – Calibration Fit")
        title.setObjectName("title")
        main_layout.addWidget(title)

        # ==== Description ====
        desc_box = QGroupBox("Description")
        desc_layout = QVBoxLayout(desc_box)
        desc_label = QLabel(
            "This page fits calibration data and generates calibration files.\n\n"
            "The fit process:\n"
            "• Loads raw measurement data from calibration folder\n"
            "• Trains linear and Gaussian Process (GP) models\n"
            "• Generates overview and calibrated plots\n"
            "• Analyzes all amplifier channels\n"
            "• Optionally writes calibration to SMU EEPROM"
        )
        desc_label.setWordWrap(True)
        desc_layout.addWidget(desc_label)
        main_layout.addWidget(desc_box)

        # ==== Options ====
        options_box = QGroupBox("Options")
        options_layout = QVBoxLayout(options_box)

        self.chk_draw_plots = QCheckBox("Generate calibration plots")
        self.chk_draw_plots.setChecked(True)
        options_layout.addWidget(self.chk_draw_plots)

        self.chk_auto_calibrate = QCheckBox("Auto-write calibration to EEPROM")
        self.chk_auto_calibrate.setChecked(True)
        options_layout.addWidget(self.chk_auto_calibrate)

        main_layout.addWidget(options_box)

        # ==== Action Buttons ====
        buttons_widget = QWidget()
        buttons_layout = QHBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)

        self.btn_run_fit = QPushButton("Run Calibration Fit")
        self.btn_run_fit.setStyleSheet(Styles.BUTTON_ACCENT)
        buttons_layout.addWidget(self.btn_run_fit)

        buttons_layout.addStretch()
        main_layout.addWidget(buttons_widget)

        # ==== Warning ====
        warning_box = QGroupBox("Important")
        warning_layout = QVBoxLayout(warning_box)
        warning_label = QLabel(
            "⚠️ Ensure calibration measurements have been completed before running fit.\n\n"
            "The fit process looks for measurement data in the calibration folder.\n"
            "If 'Auto-write to EEPROM' is enabled, the calibration will be applied "
            "to the connected SMU device."
        )
        warning_label.setWordWrap(True)
        warning_layout.addWidget(warning_label)
        main_layout.addWidget(warning_box)

        # Stretch to fill remaining space
        main_layout.addStretch()

        # Register action buttons for busy state management
        self._action_buttons = [self.btn_run_fit]

        # Wire backend action
        self.btn_run_fit.clicked.connect(self._on_run_fit)

        self._log("Calibration Fit page ready. Run after completing measurements.")

    # ---- Handlers ----
    def _on_run_fit(self) -> None:
        """Run calibration fit and optionally write to EEPROM."""
        if not self.service:
            self._log("Service not available.")
            return

        draw_plots = self.chk_draw_plots.isChecked()
        auto_cal = self.chk_auto_calibrate.isChecked()

        self._log(f"Running calibration fit: plots={draw_plots}, auto_calibrate={auto_cal}")
        self._start_task(self.service.run_calibration_fit(draw_plots, auto_cal))
