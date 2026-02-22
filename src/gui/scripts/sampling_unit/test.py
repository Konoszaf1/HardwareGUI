"""Test page for Sampling Unit hardware verification and measurements."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from src.gui.scripts.base_page import BaseHardwarePage
from src.gui.widgets.live_plot_widget import LivePlotWidget
from src.gui.widgets.shared_panels_widget import SharedPanelsWidget
from src.logic.services.su_service import SamplingUnitService


class SUTestPage(BaseHardwarePage):
    """Test page for Sampling Unit hardware.

    Provides controls for:
    - Measurement configuration (DAC, Source, Amplification, AC/DC)
    - Single Shot measurement
    - Transient measurement with results table
    - Pulse measurement with results table
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

        scroll, content, main_layout = self._create_scroll_area(min_width=600)
        outer_layout.addWidget(scroll)

        # ==== Title ====
        title = QLabel("Sampling Unit – Test")
        title.setObjectName("title")
        main_layout.addWidget(title)

        # ==== Measurement Configuration ====
        config_box = self._create_group_box("Measurement", min_height=200)
        config_form = self._create_form_layout(config_box)

        # DAC Voltage
        dac_layout = QHBoxLayout()
        self.sp_dac = QDoubleSpinBox()
        self.sp_dac.setRange(-10.0, 10.0)
        self.sp_dac.setDecimals(3)
        self.sp_dac.setValue(0.0)
        self.sp_dac.setSuffix(" V")
        self._configure_input(self.sp_dac)
        dac_layout.addWidget(self.sp_dac)
        dac_label = QLabel("Voltage - Default: 0")
        dac_layout.addWidget(dac_label)
        dac_layout.addStretch()
        config_form.addRow("DAC:", dac_layout)

        # Source dropdown
        self.cb_source = QComboBox()
        self.cb_source.addItems(["IN", "CAL", "REF_GND"])
        self._configure_input(self.cb_source)
        config_form.addRow("Source:", self.cb_source)

        # Amplification checkbox
        self.chk_amplification = QCheckBox()
        self._configure_input(self.chk_amplification)
        config_form.addRow("Amplification:", self.chk_amplification)

        # AC/DC toggle
        acdc_layout = QHBoxLayout()
        self.rb_ac = QRadioButton("AC")
        self.rb_dc = QRadioButton("DC")
        self.rb_dc.setChecked(True)
        self._configure_input(self.rb_ac)
        self._configure_input(self.rb_dc)
        acdc_group = QButtonGroup(self)
        acdc_group.addButton(self.rb_ac)
        acdc_group.addButton(self.rb_dc)
        acdc_layout.addWidget(self.rb_ac)
        acdc_layout.addWidget(self.rb_dc)

        # Separator
        acdc_layout.addWidget(QLabel("|"))

        # None / Voltage Follower toggle
        self.rb_none = QRadioButton("None")
        self.rb_vf = QRadioButton("Voltage Follower")
        self.rb_none.setChecked(True)
        self._configure_input(self.rb_none)
        self._configure_input(self.rb_vf)
        vf_group = QButtonGroup(self)
        vf_group.addButton(self.rb_none)
        vf_group.addButton(self.rb_vf)
        acdc_layout.addWidget(self.rb_none)
        acdc_layout.addWidget(self.rb_vf)

        # Separator
        acdc_layout.addWidget(QLabel("|"))

        # Calibration status
        self.lbl_cal_status = QLabel("Not Calibrated")
        self.lbl_cal_status.setStyleSheet("color: orange;")
        acdc_layout.addWidget(self.lbl_cal_status)
        acdc_layout.addStretch()
        config_form.addRow("", acdc_layout)

        main_layout.addWidget(config_box)

        # ==== Single Shot Measurement ====
        single_box = self._create_group_box("Single Shot", min_height=80)
        single_layout = QHBoxLayout(single_box)
        single_layout.setContentsMargins(12, 18, 12, 12)

        single_layout.addWidget(QLabel("Value:"))
        self.lbl_single_value = QLabel("-- V")
        self.lbl_single_value.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.lbl_single_value.setMinimumWidth(100)
        single_layout.addWidget(self.lbl_single_value)
        single_layout.addStretch()

        self.btn_single_measure = QPushButton("Measure")
        self._configure_input(self.btn_single_measure)
        single_layout.addWidget(self.btn_single_measure)

        main_layout.addWidget(single_box)

        # ==== Transient Measurement ====
        transient_box = self._create_group_box(
            "Transient Measurement", min_height=280, expanding=True
        )
        transient_layout = QVBoxLayout(transient_box)
        transient_layout.setContentsMargins(12, 18, 12, 12)
        transient_layout.setSpacing(10)

        # Parameters row
        trans_params = QHBoxLayout()
        trans_params.addWidget(QLabel("Time:"))
        self.sp_trans_time = QDoubleSpinBox()
        self.sp_trans_time.setRange(0.001, 10.0)
        self.sp_trans_time.setDecimals(3)
        self.sp_trans_time.setValue(0.1)
        self.sp_trans_time.setSuffix(" s")
        self._configure_input(self.sp_trans_time)
        trans_params.addWidget(self.sp_trans_time)

        trans_params.addWidget(QLabel("Sampling Rate:"))
        self.sp_trans_rate = QDoubleSpinBox()
        self.sp_trans_rate.setRange(0.1, 1000.0)
        self.sp_trans_rate.setDecimals(1)
        self.sp_trans_rate.setValue(1.0)
        self.sp_trans_rate.setSuffix(" µs")
        self._configure_input(self.sp_trans_rate)
        trans_params.addWidget(self.sp_trans_rate)

        self.btn_trans_measure = QPushButton("Measure")
        self._configure_input(self.btn_trans_measure)
        trans_params.addWidget(self.btn_trans_measure)
        trans_params.addStretch()
        transient_layout.addLayout(trans_params)

        # Plot widget
        self.plot_transient = LivePlotWidget()
        self.plot_transient.set_labels("Transient", "Time / s", "Voltage / V")
        self.plot_transient.setMinimumHeight(100)
        transient_layout.addWidget(self.plot_transient)

        # Results table
        self.tbl_transient = QTableWidget()
        self.tbl_transient.setColumnCount(2)
        self.tbl_transient.setHorizontalHeaderLabels(["Time", "Value"])
        self.tbl_transient.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_transient.setMinimumHeight(80)
        self.tbl_transient.verticalHeader().setDefaultSectionSize(28)
        transient_layout.addWidget(self.tbl_transient)

        main_layout.addWidget(transient_box)

        # ==== Pulse Measurement ====
        pulse_box = self._create_group_box("Pulse Measurement", min_height=280, expanding=True)
        pulse_layout = QVBoxLayout(pulse_box)
        pulse_layout.setContentsMargins(12, 18, 12, 12)
        pulse_layout.setSpacing(10)

        # Parameters row
        pulse_params = QHBoxLayout()
        pulse_params.addWidget(QLabel("Samples:"))
        self.sp_pulse_samples = QSpinBox()
        self.sp_pulse_samples.setRange(100, 10000000)
        self.sp_pulse_samples.setValue(50000)
        self._configure_input(self.sp_pulse_samples)
        pulse_params.addWidget(self.sp_pulse_samples)

        pulse_params.addWidget(QLabel("Sampling Rate:"))
        self.sp_pulse_rate = QDoubleSpinBox()
        self.sp_pulse_rate.setRange(0.1, 10.0)
        self.sp_pulse_rate.setDecimals(1)
        self.sp_pulse_rate.setValue(1.0)
        self.sp_pulse_rate.setSuffix(" MHz")
        self._configure_input(self.sp_pulse_rate)
        pulse_params.addWidget(self.sp_pulse_rate)

        self.btn_pulse_measure = QPushButton("Measure")
        self._configure_input(self.btn_pulse_measure)
        pulse_params.addWidget(self.btn_pulse_measure)
        pulse_params.addStretch()
        pulse_layout.addLayout(pulse_params)

        # Plot widget
        self.plot_pulse = LivePlotWidget()
        self.plot_pulse.set_labels("Pulse", "Time / s", "Voltage / V")
        self.plot_pulse.setMinimumHeight(100)
        pulse_layout.addWidget(self.plot_pulse)

        # Results table
        self.tbl_pulse = QTableWidget()
        self.tbl_pulse.setColumnCount(2)
        self.tbl_pulse.setHorizontalHeaderLabels(["Time", "Value"])
        self.tbl_pulse.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_pulse.setMinimumHeight(80)
        self.tbl_pulse.verticalHeader().setDefaultSectionSize(28)
        pulse_layout.addWidget(self.tbl_pulse)

        main_layout.addWidget(pulse_box)

        # Register action buttons
        self._action_buttons = [
            self.btn_single_measure,
            self.btn_trans_measure,
            self.btn_pulse_measure,
        ]

        # ==== Signals ====
        self.btn_single_measure.clicked.connect(self._on_single_shot)
        self.btn_trans_measure.clicked.connect(self._on_transient)
        self.btn_pulse_measure.clicked.connect(self._on_pulse)

        # Connect service signals (from base class)
        self._connect_service_signals()

        self._log("Test page ready.")

    def _on_single_shot(self) -> None:
        """Run single-shot voltage measurement."""
        if not self.service:
            self._log("Service not available.")
            return

        dac = self.sp_dac.value()
        source = self.cb_source.currentText()

        def on_complete(result):
            if result and result.data and result.data.get("ok"):
                voltage = result.data.get("voltage", "--")
                self.lbl_single_value.setText(
                    f"{voltage:.6f} V" if isinstance(voltage, (int, float)) else f"{voltage}"
                )
                self._log(f"Measured voltage: {voltage} V")
            else:
                self._log("Single-shot measurement failed.")

        self._log(f"Running single-shot: DAC={dac}V, source={source}")
        task = self.service.run_single_shot(dac_voltage=dac, source=source)
        task.signals.finished.connect(on_complete)
        self._start_task(task)

    def _on_transient(self) -> None:
        """Run transient measurement."""
        if not self.service:
            self._log("Service not available.")
            return

        time_s = self.sp_trans_time.value()
        rate_us = self.sp_trans_rate.value()

        self.plot_transient.clear()
        self.plot_transient.set_labels("Transient", "Time / s", "Voltage / V")

        def on_complete(result):
            if result and result.data:
                t = result.data.get("time")
                v = result.data.get("values")
                if t is not None and v is not None:
                    self.plot_transient.plot_batch(t, v, "transient")

        self._log(f"Running transient: time={time_s}s, rate={rate_us}µs")
        task = self.service.run_transient_measure(
            measurement_time=time_s,
            sampling_rate=rate_us * 1e-6,
        )
        task.signals.finished.connect(on_complete)
        self._start_task(task)

    def _on_pulse(self) -> None:
        """Run pulse measurement."""
        if not self.service:
            self._log("Service not available.")
            return

        samples = self.sp_pulse_samples.value()
        rate_mhz = self.sp_pulse_rate.value()

        self.plot_pulse.clear()
        self.plot_pulse.set_labels("Pulse", "Time / s", "Voltage / V")

        def on_complete(result):
            if result and result.data:
                t = result.data.get("time")
                v = result.data.get("values")
                if t is not None and v is not None:
                    self.plot_pulse.plot_batch(t, v, "pulse")

        self._log(f"Running pulse: samples={samples}, rate={rate_mhz}MHz")
        task = self.service.run_pulse_measure(
            num_samples=samples,
            sampling_rate=rate_mhz * 1e6,
        )
        task.signals.finished.connect(on_complete)
        self._start_task(task)
