"""Calibration page for Sampling Unit voltage channel calibration."""

from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from src.gui.scripts.base_page import BaseHardwarePage
from src.gui.widgets.live_plot_widget import LivePlotWidget
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

        # ==== Measure Section ====
        measure_box = self._create_group_box("Measure", min_height=80)
        measure_layout = QHBoxLayout(measure_box)
        measure_layout.setContentsMargins(12, 18, 12, 12)
        measure_layout.addStretch()

        self.btn_measure = QPushButton("Measure")
        self._configure_input(self.btn_measure)
        measure_layout.addWidget(self.btn_measure)

        main_layout.addWidget(measure_box)

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

        self.plot_widget = LivePlotWidget()
        self.plot_widget.set_labels("Calibration", "V_ref / V", "V_meas / V")
        self.plot_widget.setMinimumHeight(200)
        plot_layout.addWidget(self.plot_widget)

        main_layout.addWidget(plot_box)

        # Register action buttons
        self._action_buttons = [self.btn_measure, self.btn_run_cal, self.btn_verify]

        # ==== Signals ====
        self.btn_measure.clicked.connect(self._on_measure)
        self.btn_run_cal.clicked.connect(self._on_run_calibration)
        self.btn_verify.clicked.connect(self._on_verify)

        # Connect service signals (from base class)
        self._connect_service_signals()

    def _on_measure(self) -> None:
        """Run calibration measurement (all ranges)."""
        if not self.service:
            self._log("Service not available.")
            return

        self._log("Starting calibration measurement...")
        self.plot_widget.clear()
        self.plot_widget.set_labels("Calibration Measure", "V_ref / V", "V_meas / V")
        task = self.service.run_calibration_measure()
        if not task:
            self._log("Keithley IP not configured. Set it on the Connection page first.")
            return
        task.signals.data_chunk.connect(self._on_measure_chunk)
        self._start_task(task)

    def _on_measure_chunk(self, data) -> None:
        """Handle live measurement data points."""
        if isinstance(data, dict) and "x" in data:
            series = data.get("series", "measure")
            self.plot_widget.append_point(series, data["x"], data["y"])

    def _on_run_calibration(self) -> None:
        """Run voltage calibration."""
        if not self.service:
            self._log("Service not available.")
            return

        model = "linear" if self.rb_linear.isChecked() else "gp"
        self._log(f"Running {model} calibration...")
        self.plot_widget.clear()
        task = self.service.run_calibrate(model=model)
        if not task:
            self._log("Service unavailable.")
            return
        self._start_task(task)

    def _on_verify(self) -> None:
        """Verify calibration by re-measuring."""
        if not self.service:
            self._log("Service not available.")
            return

        self._log("Verifying calibration (re-measuring all ranges)...")
        self.plot_widget.clear()
        self.plot_widget.set_labels("Calibration Verify", "V_ref / V", "V_meas / V")
        task = self.service.run_calibration_measure(verify_calibration=True)
        if not task:
            self._log("Keithley IP not configured. Set it on the Connection page first.")
            return
        task.signals.data_chunk.connect(self._on_measure_chunk)
        self._start_task(task)

    # ---- Plot rendering from finished result ----
    def _on_task_finished(self, result) -> None:
        """Handle results from calibration tasks."""
        data = getattr(result, "data", None)
        if isinstance(data, dict):
            coeffs = data.get("coeffs", {})
            if coeffs:
                self._update_coeff_display(coeffs)

            plot = data.get("plot")
            if plot:
                self._render_plot(plot)
        super()._on_task_finished(result)

    def _update_coeff_display(self, coeffs: dict) -> None:
        """Update the k, d, sigma display fields from a coeffs dict."""
        k = coeffs.get("k")
        d = coeffs.get("d")
        sigma = coeffs.get("sigma")
        if k is not None:
            self.le_k.setText(f"{k:.8f}" if isinstance(k, float) else str(k))
        if d is not None:
            self.le_d.setText(f"{d:.8f}" if isinstance(d, float) else str(d))
        if sigma is not None:
            self.le_sigma.setText(f"{sigma:.8f}" if isinstance(sigma, float) else str(sigma))

    def _render_plot(self, plot: dict) -> None:
        """Render a plot dict onto the LivePlotWidget."""
        self.plot_widget.clear()
        plot_type = plot.get("type")

        try:
            if plot_type == "calibration_overview":
                self.plot_widget.set_labels("Calibration Overview", "V_ref / V", "V_meas / V")
                for wf in plot.get("waveforms", []):
                    self.plot_widget.plot_batch(wf["x"], wf["y"], wf["series"])

            elif plot_type == "calibration_error":
                self.plot_widget.set_labels("Calibration Error", "V_ref / V", "Error / V")
                for wf in plot.get("waveforms", []):
                    self.plot_widget.plot_batch(wf["x"], wf["y"], wf["series"])
        except Exception as e:
            self._log(f"Plot rendering failed: {e}")
