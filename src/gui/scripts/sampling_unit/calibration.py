"""Calibration page for Sampling Unit voltage channel calibration."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from src.gui.scripts.base_page import BaseHardwarePage
from src.gui.widgets.shared_panels_widget import SharedPanelsWidget
from src.logic.services.su_service import SamplingUnitService


class SUCalibrationPage(BaseHardwarePage):
    """Calibration page for Sampling Unit.

    Provides controls for:
    - Fitting: Select Linear/GP model and run calibration
    - Verify: Verify calibration points
    - Calibration Parameters: Display k, d, sigma values
    - Plot Area: Visualization placeholder
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        service: SamplingUnitService | None = None,
        shared_panels: SharedPanelsWidget | None = None,
    ):
        super().__init__(parent, service, shared_panels)

        # ==== Main Layout with Scroll Area ====
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll, content, main_layout = self._create_scroll_area(min_width=550)
        outer_layout.addWidget(scroll)

        # ==== Title ====
        title = QLabel("Sampling Unit – Calibration")
        title.setObjectName("title")
        main_layout.addWidget(title)

        # ==== Fitting Section ====
        fitting_box = self._create_group_box("Fitting", min_height=120)
        fitting_layout = QVBoxLayout(fitting_box)
        fitting_layout.setContentsMargins(12, 18, 12, 12)
        fitting_layout.setSpacing(10)

        model_layout = QHBoxLayout()
        model_label = QLabel("Model:")
        model_layout.addWidget(model_label)
        self.rb_linear = QRadioButton("Linear")
        self.rb_gp = QRadioButton("GP")
        self.rb_linear.setChecked(True)
        self._configure_input(self.rb_linear)
        self._configure_input(self.rb_gp)
        model_group = QButtonGroup(self)
        model_group.addButton(self.rb_linear)
        model_group.addButton(self.rb_gp)
        model_layout.addWidget(self.rb_linear)
        model_layout.addWidget(self.rb_gp)
        model_layout.addStretch()

        self.btn_run_cal = QPushButton("Run Calibration")
        self._configure_input(self.btn_run_cal, min_width=120)
        model_layout.addWidget(self.btn_run_cal)

        fitting_layout.addLayout(model_layout)
        main_layout.addWidget(fitting_box)

        # ==== Verify Section ====
        verify_box = self._create_group_box("Verify", min_height=80)
        verify_layout = QHBoxLayout(verify_box)
        verify_layout.setContentsMargins(12, 18, 12, 12)

        self.sp_verify_points = QDoubleSpinBox()
        self.sp_verify_points.setRange(1, 100)
        self.sp_verify_points.setValue(10)
        self._configure_input(self.sp_verify_points)
        verify_layout.addWidget(QLabel("Points:"))
        verify_layout.addWidget(self.sp_verify_points)
        verify_layout.addStretch()

        self.btn_verify = QPushButton("Verify")
        self._configure_input(self.btn_verify)
        verify_layout.addWidget(self.btn_verify)

        main_layout.addWidget(verify_box)

        # ==== Calibration Parameters ====
        params_box = self._create_group_box("Calibration Parameters", min_height=120)
        params_form = self._create_form_layout(params_box)

        self.le_k = QLineEdit()
        self.le_k.setReadOnly(True)
        self.le_k.setPlaceholderText("--")
        self._configure_input(self.le_k)
        params_form.addRow("k (slope):", self.le_k)

        self.le_d = QLineEdit()
        self.le_d.setReadOnly(True)
        self.le_d.setPlaceholderText("--")
        self._configure_input(self.le_d)
        params_form.addRow("d (offset):", self.le_d)

        self.le_sigma = QLineEdit()
        self.le_sigma.setReadOnly(True)
        self.le_sigma.setPlaceholderText("--")
        self._configure_input(self.le_sigma)
        params_form.addRow("σ (sigma):", self.le_sigma)

        main_layout.addWidget(params_box)

        # ==== Plot Area ====
        plot_box = self._create_group_box("Plot", min_height=300, expanding=True)
        plot_layout = QVBoxLayout(plot_box)
        plot_layout.setContentsMargins(12, 18, 12, 12)

        self.lbl_plot = QLabel("Calibration plot will appear here")
        self.lbl_plot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_plot.setMinimumHeight(200)
        self.lbl_plot.setStyleSheet("background-color: #2a2a2a; border: 1px solid #444;")
        plot_layout.addWidget(self.lbl_plot)

        main_layout.addWidget(plot_box)

        # Register action buttons
        self._action_buttons = [self.btn_run_cal, self.btn_verify]

        # ==== Signals ====
        self.btn_run_cal.clicked.connect(self._on_run_calibration)
        self.btn_verify.clicked.connect(self._on_verify)

        self._log("Calibration page ready.")

    def _on_run_calibration(self) -> None:
        """Run voltage calibration."""
        if not self.service:
            self._log("Service not available.")
            return

        model = "linear" if self.rb_linear.isChecked() else "gp"

        def on_complete(result):
            if result and result.data and result.data.get("ok"):
                coeffs = result.data.get("coeffs", {})
                k = coeffs.get("k", "--")
                d = coeffs.get("d", "--")
                sigma = coeffs.get("sigma", "--")
                self.le_k.setText(f"{k:.8f}" if isinstance(k, float) else str(k))
                self.le_d.setText(f"{d:.8f}" if isinstance(d, float) else str(d))
                self.le_sigma.setText(f"{sigma:.8f}" if isinstance(sigma, float) else str(sigma))
                self._log("Calibration complete.")
            else:
                self._log("Calibration failed.")

        self._log(f"Running {model} calibration...")
        task = self.service.run_calibrate(model=model)
        task.signals.finished.connect(on_complete)
        self._start_task(task)

    def _on_verify(self) -> None:
        """Verify calibration."""
        if not self.service:
            self._log("Service not available.")
            return

        points = int(self.sp_verify_points.value())
        self._log(f"Verifying calibration with {points} points...")
        task = self.service.run_calibration_verify(num_points=points)
        self._start_task(task)
