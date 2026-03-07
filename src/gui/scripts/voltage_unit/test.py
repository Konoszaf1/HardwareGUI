"""Test page for voltage unit validation."""

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.gui.scripts.base_page import BaseHardwarePage
from src.gui.widgets.live_plot_widget import LivePlotWidget
from src.gui.widgets.shared_panels_widget import SharedPanelsWidget
from src.gui.styles import Styles
from src.gui.utils.widget_factories import create_test_card
from src.logic.services.vu_service import VoltageUnitService


class VUTestPage(BaseHardwarePage):
    """Test execution page for voltage unit validation.

    Provides controls to run individual tests (outputs, ramp, transient) or all tests
    together. Test results are logged to the shared console panel and generated plots
    appear in the shared artifacts panel.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        service: VoltageUnitService | None = None,
        shared_panels: SharedPanelsWidget | None = None,
    ):
        """Initialize the VUTestPage.

        Args:
            parent: Parent widget.
            service: Service for voltage unit operations.
            shared_panels: Shared panels for logs/artifacts.
        """
        super().__init__(parent, service, shared_panels)

        # ==== Main Layout (Vertical) ====
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll, content, main_layout = self._create_scroll_area()
        outer_layout.addWidget(scroll)

        main_layout.setSpacing(15)

        # ==== Title ====
        title = QLabel("Voltage Unit – Tests")
        title.setObjectName("title")
        main_layout.addWidget(title)

        # ==== Test Cards ====
        cards_widget = QWidget()
        cards_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        cards_layout = QHBoxLayout(cards_widget)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(15)

        # -- Card 1: Outputs --
        self.btn_test_outputs = QPushButton("Run Test")
        self._configure_input(self.btn_test_outputs)
        card_outputs = create_test_card(
            "Outputs Test",
            ["Points: 5000", "Scale: 0.2 V/div", "Time: 1e-2 s/div"],
            self.btn_test_outputs,
        )
        card_outputs.setMaximumWidth(280)
        cards_layout.addWidget(card_outputs)

        # -- Card 2: Ramp --
        self.btn_test_ramp = QPushButton("Run Test")
        self._configure_input(self.btn_test_ramp)
        card_ramp = create_test_card(
            "Ramp Test",
            ["Range: 500 ms", "Slope: 20*amp V/s", "Sync: 1 MHz"],
            self.btn_test_ramp,
        )
        card_ramp.setMaximumWidth(280)
        cards_layout.addWidget(card_ramp)

        # -- Card 3: Transient --
        self.btn_test_transient = QPushButton("Run Test")
        self._configure_input(self.btn_test_transient)
        card_transient = create_test_card(
            "Transient Test",
            ["Amp: 1 V", "Step: Auto (5-20µs)", "Rec: 5000 pts"],
            self.btn_test_transient,
        )
        card_transient.setMaximumWidth(280)
        cards_layout.addWidget(card_transient)

        # -- Card 4: All --
        self.btn_test_all = QPushButton("Run All")
        self._configure_input(self.btn_test_all)
        self.btn_test_all.setStyleSheet(Styles.BUTTON_ACCENT)
        card_all = create_test_card(
            "Full Suite",
            ["Runs all tests", "Generates all plots", "Verifies results"],
            self.btn_test_all,
        )
        card_all.setMaximumWidth(280)
        cards_layout.addWidget(card_all)

        cards_layout.addStretch()
        main_layout.addWidget(cards_widget)

        # ==== Live Plot ====
        plot_box = self._create_group_box("Test Results", min_height=250, expanding=True)
        plot_layout = QVBoxLayout(plot_box)
        plot_layout.setContentsMargins(12, 18, 12, 12)
        self.plot_widget = LivePlotWidget()
        self.plot_widget.set_labels("Output Error", "Voltage / V", "Error / mV")
        self.plot_widget.setMinimumHeight(200)
        plot_layout.addWidget(self.plot_widget)
        main_layout.addWidget(plot_box)

        # Stretch to fill remaining space
        main_layout.addStretch()

        # Register action buttons for busy state management
        self._action_buttons = [
            self.btn_test_outputs,
            self.btn_test_ramp,
            self.btn_test_transient,
            self.btn_test_all,
        ]

        # Wire backend actions
        self.btn_test_outputs.clicked.connect(self._on_test_outputs)
        self.btn_test_ramp.clicked.connect(self._on_test_ramp)
        self.btn_test_transient.clicked.connect(self._on_test_transient)
        self.btn_test_all.clicked.connect(self._on_test_all)

        # Connect service signals (from base class)
        self._connect_service_signals()

        self._log("Tests page ready.")

    # ---- Handlers ----
    def _on_test_outputs(self) -> None:
        """Run output voltage accuracy test."""
        if not self.service:
            self._log("Service not available.")
            return
        self.plot_widget.clear()
        self.plot_widget.set_labels("Output Error", "Voltage / V", "Error / mV")
        task = self.service.test_outputs()
        task.signals.data_chunk.connect(self._on_output_chunk)
        self._start_task(task)

    def _on_output_chunk(self, data) -> None:
        """Handle live data chunks during output test."""
        if isinstance(data, dict) and "x" in data:
            self.plot_widget.append_point("CH1", data["x"], 1000 * data["y_ch1"])
            self.plot_widget.append_point("CH2", data["x"], 1000 * data["y_ch2"])
            self.plot_widget.append_point("CH3", data["x"], 1000 * data["y_ch3"])

    def _on_test_ramp(self) -> None:
        """Run voltage ramp test."""
        if not self.service:
            self._log("Service not available.")
            return
        self.plot_widget.clear()
        self.plot_widget.set_labels("Ramp Signal", "Time / s", "Signal / V")
        task = self.service.test_ramp()
        task.signals.data_chunk.connect(self._on_waveform_chunk)
        self._start_task(task)

    def _on_test_transient(self) -> None:
        """Run transient response test."""
        if not self.service:
            self._log("Service not available.")
            return
        self.plot_widget.clear()
        self.plot_widget.set_labels("Transient Response", "Time / s", "Signal / V")
        task = self.service.test_transient()
        task.signals.data_chunk.connect(self._on_waveform_chunk)
        self._start_task(task)

    def _on_test_all(self) -> None:
        """Run all tests sequentially (outputs, ramp, transient)."""
        if not self.service:
            self._log("Service not available.")
            return
        self.plot_widget.clear()
        task = self.service.test_all()
        task.signals.data_chunk.connect(self._on_data_chunk)
        self._start_task(task)

    # ---- Live data handlers ----
    def _on_waveform_chunk(self, data) -> None:
        """Handle live waveform data from ramp/transient tests."""
        if not isinstance(data, dict) or "type" not in data:
            return
        series = data.get("series", "")
        if series == "CH1":
            title = "Ramp Signal" if data["type"] == "ramp" else "Transient Response"
            self.plot_widget.clear()
            self.plot_widget.set_labels(title, "Time / s", "Signal / V")
        self.plot_widget.plot_batch(
            data["x"], data["y"], series,
            linestyle=data.get("linestyle", "-"),
            alpha=data.get("alpha", 1.0),
            color=data.get("color"),
        )

    def _on_data_chunk(self, data) -> None:
        """Handle any live data chunk during test_all (outputs + waveforms)."""
        if not isinstance(data, dict):
            return
        if "y_ch1" in data:
            self._on_output_chunk(data)
        elif "type" in data:
            self._on_waveform_chunk(data)

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
                    for x, y in zip(voltages, errors[i]):
                        self.plot_widget.append_point(ch, x, 1000 * y)

            elif plot_type in ("ramp", "transient"):
                title = "Ramp Signal" if plot_type == "ramp" else "Transient Response"
                self.plot_widget.set_labels(title, "Time / s", "Signal / V")
                for wf in plot["waveforms"]:
                    self.plot_widget.plot_batch(
                        wf["x"], wf["y"], wf["series"],
                        linestyle=wf.get("linestyle", "-"),
                        alpha=wf.get("alpha", 1.0),
                        color=wf.get("color"),
                    )
        except Exception as e:
            self._log(f"Plot rendering failed: {e}")
