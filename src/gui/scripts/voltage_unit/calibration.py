"""Calibration page for voltage unit autocalibration and testing."""

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.gui.scripts.base_page import BaseHardwarePage
from src.gui.widgets.live_plot_widget import LivePlotWidget
from src.gui.widgets.shared_panels_widget import SharedPanelsWidget
from src.logic.services.vu_service import VoltageUnitService


class VUCalibrationPage(BaseHardwarePage):
    """Calibration page for voltage unit.

    Provides controls for Python-based autocalibration (iterative).
    Calibration results are logged to the shared console panel and
    generated plots appear in the shared artifacts panel.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        service: VoltageUnitService | None = None,
        shared_panels: SharedPanelsWidget | None = None,
    ):
        """Initialize the VUCalibrationPage.

        Args:
            parent (QWidget | None): Parent widget.
            service (VoltageUnitService | None): Service for voltage unit operations.
            shared_panels (SharedPanelsWidget | None): Shared panels for logs/artifacts.
        """
        super().__init__(parent, service, shared_panels)

        # ==== Main Layout (Vertical) ====
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll, content, main_layout = self._create_scroll_area(min_width=500)
        outer_layout.addWidget(scroll)

        # ==== Title ====
        title = QLabel("Voltage Unit – Calibration")
        title.setObjectName("title")
        main_layout.addWidget(title)

        # ==== Top Section ====
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)

        # -- Controls --
        controls_box = self._create_group_box(
            "Calibration Actions", min_height=160, expanding=False
        )
        controls_layout = QVBoxLayout(controls_box)

        self.btn_run_autocal_python = QPushButton("Run Autocalibration (Python)")
        self._configure_input(self.btn_run_autocal_python)

        controls_layout.addWidget(self.btn_run_autocal_python)
        controls_layout.addStretch()

        # Info box (compact)
        info_box = self._create_group_box("Constants", min_height=160, expanding=False)
        info_form = self._create_form_layout(info_box)

        self.spin_max_iter = QSpinBox()
        self.spin_max_iter.setRange(1, 50)
        self.spin_max_iter.setValue(10)
        self._configure_input(self.spin_max_iter)
        info_form.addRow("Max iter:", self.spin_max_iter)
        info_form.addRow("Offset:", QLabel("2 mV"))
        info_form.addRow("Slope err:", QLabel("0.1 %"))

        controls_layout.addWidget(info_box)

        top_layout.addWidget(controls_box)
        top_layout.addStretch()

        main_layout.addWidget(top_widget)

        # ==== Live Plot ====
        plot_box = self._create_group_box(
            "Calibration Progress",
            min_height=250,
            expanding=True,
        )
        plot_layout = QVBoxLayout(plot_box)
        plot_layout.setContentsMargins(12, 18, 12, 12)
        self.plot_widget = LivePlotWidget()
        self.plot_widget.set_labels("Output Error per Iteration", "Voltage / V", "Error / mV")
        self.plot_widget.setMinimumHeight(200)
        plot_layout.addWidget(self.plot_widget)
        main_layout.addWidget(plot_box)

        # Stretch to fill remaining space
        main_layout.addStretch()

        # Register action buttons for busy state management
        self._action_buttons = [
            self.btn_run_autocal_python,
        ]

        # Wire backend actions
        self.btn_run_autocal_python.clicked.connect(self._on_autocal_python)

        # Connect service signals (from base class)
        self._connect_service_signals()

    # ---- Handlers ----
    def _on_autocal_python(self) -> None:
        """Run Python-based autocalibration."""
        if not self.service:
            self._log("Service not available.")
            return
        self.plot_widget.clear()
        self.plot_widget.set_labels("Output Error per Iteration", "Voltage / V", "Error / mV")
        task = self.service.autocal_python(max_iterations=self.spin_max_iter.value())
        task.signals.data_chunk.connect(self._on_cal_chunk)
        self._start_task(task)

    # ---- Live data from autocalibration ----
    def _on_cal_chunk(self, data) -> None:
        """Handle live data chunks during autocalibration."""
        if not isinstance(data, dict):
            return
        if "iteration" in data:
            # Phase marker - clear plot and set labels for incoming data
            it = data["iteration"]
            self.plot_widget.clear()
            if it == "final_transient":
                self.plot_widget.set_labels("Final - Transient Response", "Time / s", "Signal / V")
            elif it == "final_outputs":
                self.plot_widget.set_labels("Final - Output Error", "Voltage / V", "Error / mV")
            elif it == "final_ramp":
                self.plot_widget.set_labels("Final - Ramp Signal", "Time / s", "Signal / V")
            else:
                self.plot_widget.set_labels(
                    f"Iteration {it + 1} - Output Error", "Voltage / V", "Error / mV"
                )
        elif "type" in data and data["type"] in ("ramp", "transient"):
            # Waveform data from test_ramp / test_transient
            title = "Ramp Signal" if data["type"] == "ramp" else "Transient Response"
            series = data.get("series", "")
            if series == "CH1":
                self.plot_widget.clear()
                self.plot_widget.set_labels(title, "Time / s", "Signal / V")
            self.plot_widget.plot_batch(
                data["x"],
                data["y"],
                series,
                linestyle=data.get("linestyle", "-"),
                alpha=data.get("alpha", 1.0),
                color=data.get("color"),
            )
        elif "x" in data:
            # Point measured - update scatter plot (convert V → mV)
            self.plot_widget.append_point("CH1", data["x"], 1000 * data["y_ch1"])
            self.plot_widget.append_point("CH2", data["x"], 1000 * data["y_ch2"])
            self.plot_widget.append_point("CH3", data["x"], 1000 * data["y_ch3"])

    # ---- Plot rendering from finished result ----
    def _on_task_finished(self, result) -> None:
        """Render plot data from task result, then call base handler."""
        data = getattr(result, "data", None)
        if isinstance(data, dict):
            plot = data.get("plot")
            plots = data.get("plots")
            if plot:
                self._render_plot(plot)
            elif plots:
                self._render_plot(plots[-1])
        super()._on_task_finished(result)

    def _render_plot(self, plot: dict) -> None:
        """Render a plot dict onto the LivePlotWidget."""
        self.plot_widget.clear()
        plot_type = plot.get("type")

        try:
            if plot_type == "outputs":
                self.plot_widget.set_labels("Output Error", "Voltage / V", "Error / mV")
                voltages = plot["voltages"]
                errors = plot["errors"]
                for i, ch in enumerate(("CH1", "CH2", "CH3")):
                    for x, y in zip(voltages, errors[i], strict=False):
                        self.plot_widget.append_point(ch, x, 1000 * y)

            elif plot_type in ("ramp", "transient"):
                title = "Ramp Signal" if plot_type == "ramp" else "Transient Response"
                self.plot_widget.set_labels(title, "Time / s", "Signal / V")
                for wf in plot["waveforms"]:
                    self.plot_widget.plot_batch(
                        wf["x"],
                        wf["y"],
                        wf["series"],
                        linestyle=wf.get("linestyle", "-"),
                        alpha=wf.get("alpha", 1.0),
                        color=wf.get("color"),
                    )
        except Exception as e:
            self._log(f"Plot rendering failed: {e}")
