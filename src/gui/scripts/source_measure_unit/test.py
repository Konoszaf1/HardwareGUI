"""Test page for Source Measure Unit hardware verification."""

from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from src.gui.scripts.base_page import BaseHardwarePage
from src.gui.widgets.shared_panels_widget import SharedPanelsWidget
from src.logic.services.smu_service import SourceMeasureUnitService


class SMUTestPage(BaseHardwarePage):
    """Test page for Source Measure Unit hardware.

    Provides controls for:
    - Temperature measurement
    - Relais configuration (IV-Channel, PA-Channel, High-Pass, Input DUT, VGUARD)
    - Program Relais action
    - Measure Idle text field for additional instructions
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        service: SourceMeasureUnitService | None = None,
        shared_panels: SharedPanelsWidget | None = None,
    ):
        super().__init__(parent, service, shared_panels)

        # ==== Main Layout with Scroll Area ====
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll, content, main_layout = self._create_scroll_area(min_width=600)
        outer_layout.addWidget(scroll)

        # ==== Title ====
        title = QLabel("Source Measure Unit – Test")
        title.setObjectName("title")
        main_layout.addWidget(title)

        # ==== Temperature Section ====
        temp_box = self._create_group_box("Temperature")
        temp_form = self._create_form_layout(temp_box)

        temp_value_layout = QHBoxLayout()
        self.lbl_temp_value = QLabel("-- °C")
        self.lbl_temp_value.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.lbl_temp_value.setMinimumWidth(100)
        temp_value_layout.addWidget(self.lbl_temp_value)
        temp_value_layout.addStretch()
        self.btn_temp_measure = QPushButton("Measure")
        self._configure_input(self.btn_temp_measure)
        temp_value_layout.addWidget(self.btn_temp_measure)
        temp_form.addRow("Value:", temp_value_layout)

        main_layout.addWidget(temp_box)

        # ==== Relais Section (outer container) ====
        relais_box = self._create_group_box("Relais")
        relais_layout = QVBoxLayout(relais_box)
        relais_layout.setContentsMargins(*self._group_padding)
        relais_layout.setSpacing(self._layout_spacing)

        # -- IV-Channel (nested group box) --
        iv_box = self._create_group_box("IV-Channel")
        iv_form = self._create_form_layout(iv_box)

        self.cb_iv_channel = QComboBox()
        self.cb_iv_channel.addItems(["CH1", "CH2", "CH3", "CH4"])
        self._configure_input(self.cb_iv_channel)
        iv_form.addRow("Channel:", self.cb_iv_channel)

        iv_ref_layout = QHBoxLayout()
        self.rb_iv_gnd = QRadioButton("GND")
        self.rb_iv_vsmu = QRadioButton("VSMU")
        self.rb_iv_gnd.setChecked(True)
        self._configure_input(self.rb_iv_gnd)
        self._configure_input(self.rb_iv_vsmu)
        iv_ref_group = QButtonGroup(self)
        iv_ref_group.addButton(self.rb_iv_gnd)
        iv_ref_group.addButton(self.rb_iv_vsmu)
        iv_ref_layout.addWidget(self.rb_iv_gnd)
        iv_ref_layout.addWidget(self.rb_iv_vsmu)
        iv_ref_layout.addStretch()
        iv_form.addRow("Reference:", iv_ref_layout)

        relais_layout.addWidget(iv_box)

        # -- PA-Channel (nested group box) --
        pa_box = self._create_group_box("PA-Channel")
        pa_form = self._create_form_layout(pa_box)

        self.cb_pa_channel = QComboBox()
        self.cb_pa_channel.addItems(["PA1", "PA2", "PA3", "PA4"])
        self._configure_input(self.cb_pa_channel)
        pa_form.addRow("Channel:", self.cb_pa_channel)

        pa_ref_layout = QHBoxLayout()
        self.rb_pa_gnd = QRadioButton("GND")
        self.rb_pa_vsmu = QRadioButton("VSMU")
        self.rb_pa_gnd.setChecked(True)
        self._configure_input(self.rb_pa_gnd)
        self._configure_input(self.rb_pa_vsmu)
        pa_ref_group = QButtonGroup(self)
        pa_ref_group.addButton(self.rb_pa_gnd)
        pa_ref_group.addButton(self.rb_pa_vsmu)
        pa_ref_layout.addWidget(self.rb_pa_gnd)
        pa_ref_layout.addWidget(self.rb_pa_vsmu)
        pa_ref_layout.addStretch()
        pa_form.addRow("Reference:", pa_ref_layout)

        relais_layout.addWidget(pa_box)

        # -- High-Pass (nested group box) --
        hp_box = self._create_group_box("High-Pass")
        hp_form = self._create_form_layout(hp_box)

        hp_layout = QHBoxLayout()
        self.rb_hp_enable = QRadioButton("Enable")
        self.rb_hp_disable = QRadioButton("Disable")
        self.rb_hp_disable.setChecked(True)
        self._configure_input(self.rb_hp_enable)
        self._configure_input(self.rb_hp_disable)
        hp_group = QButtonGroup(self)
        hp_group.addButton(self.rb_hp_enable)
        hp_group.addButton(self.rb_hp_disable)
        hp_layout.addWidget(self.rb_hp_enable)
        hp_layout.addWidget(self.rb_hp_disable)
        hp_layout.addStretch()
        hp_form.addRow("State:", hp_layout)

        relais_layout.addWidget(hp_box)

        # -- Input (nested group box for DUT + VGUARD) --
        input_box = self._create_group_box("Input")
        input_form = self._create_form_layout(input_box)

        # DUT
        dut_layout = QHBoxLayout()
        self.rb_dut_none = QRadioButton("None")
        self.rb_dut_gnd = QRadioButton("GND")
        self.rb_dut_guard = QRadioButton("GUARD")
        self.rb_dut_vsmu = QRadioButton("VSMU")
        self.rb_dut_su = QRadioButton("SU")
        self.rb_dut_vsmu_su = QRadioButton("VSMU&SU")
        self.rb_dut_none.setChecked(True)
        dut_btn_group = QButtonGroup(self)
        for rb in [
            self.rb_dut_none,
            self.rb_dut_gnd,
            self.rb_dut_guard,
            self.rb_dut_vsmu,
            self.rb_dut_su,
            self.rb_dut_vsmu_su,
        ]:
            self._configure_input(rb)
            dut_btn_group.addButton(rb)
            dut_layout.addWidget(rb)
        dut_layout.addStretch()
        input_form.addRow("DUT:", dut_layout)

        # VGUARD
        vguard_layout = QHBoxLayout()
        self.rb_vguard_gnd = QRadioButton("GND")
        self.rb_vguard_vsmu = QRadioButton("VSMU")
        self.rb_vguard_gnd.setChecked(True)
        self._configure_input(self.rb_vguard_gnd)
        self._configure_input(self.rb_vguard_vsmu)
        vguard_group = QButtonGroup(self)
        vguard_group.addButton(self.rb_vguard_gnd)
        vguard_group.addButton(self.rb_vguard_vsmu)
        vguard_layout.addWidget(self.rb_vguard_gnd)
        vguard_layout.addWidget(self.rb_vguard_vsmu)
        vguard_layout.addStretch()
        input_form.addRow("VGUARD:", vguard_layout)

        relais_layout.addWidget(input_box)

        main_layout.addWidget(relais_box)

        # ==== Program Relais Button ====
        self.btn_program_relais = QPushButton("Program Relais")
        self._configure_input(self.btn_program_relais, min_height=40)
        main_layout.addWidget(self.btn_program_relais)

        # ==== Measure Idle Section ====
        idle_box = self._create_group_box("Measure Idle", expanding=True)
        idle_layout = QVBoxLayout(idle_box)
        idle_layout.setContentsMargins(*self._group_padding)

        idle_label = QLabel("TextField where additional instructions can be tested by user:")
        idle_layout.addWidget(idle_label)

        self.te_idle = QPlainTextEdit()
        self.te_idle.setPlaceholderText(
            "For Example:\n• Measure Powersupply\n• Verify Relay Connection with Multimeter"
        )
        self.te_idle.setMinimumHeight(100)
        idle_layout.addWidget(self.te_idle)

        main_layout.addWidget(idle_box)

        # Register action buttons
        self._action_buttons = [self.btn_temp_measure, self.btn_program_relais]

        # ==== Signals ====
        self.btn_temp_measure.clicked.connect(self._on_measure_temp)
        self.btn_program_relais.clicked.connect(self._on_program_relais)

        self._log("Test page ready.")

    def _on_measure_temp(self) -> None:
        """Measure temperature."""
        if not self.service:
            self._log("Service not available.")
            return

        def on_complete(result):
            if result and result.data:
                temp = result.data.get("temperature", "--")
                self.lbl_temp_value.setText(
                    f"{temp:.2f} °C" if isinstance(temp, (int, float)) else f"{temp}"
                )
                self._log(f"Temperature: {temp} °C")
            else:
                self._log("Temperature measurement failed.")

        self._log("Measuring temperature...")
        task = self.service.run_temperature_read()
        task.signals.finished.connect(on_complete)
        self._start_task(task)

    # Channel text to integer mapping for relay programming
    _IV_CHANNEL_MAP = {"CH1": 1, "CH2": 2, "CH3": 3, "CH4": 4}
    _PA_CHANNEL_MAP = {"PA1": 1, "PA2": 2, "PA3": 3, "PA4": 4}

    def _on_program_relais(self) -> None:
        """Program relais configuration via service."""
        if not self.service:
            self._log("Service not available.")
            return

        iv_channel_text = self.cb_iv_channel.currentText()
        iv_channel = self._IV_CHANNEL_MAP.get(iv_channel_text, 1)
        iv_ref = "GND" if self.rb_iv_gnd.isChecked() else "VSMU"

        pa_channel_text = self.cb_pa_channel.currentText()
        pa_channel = self._PA_CHANNEL_MAP.get(pa_channel_text, 1)

        high_pass = self.rb_hp_enable.isChecked()
        vguard = "GND" if self.rb_vguard_gnd.isChecked() else "VSMU"

        dut = "GND"  # default
        if self.rb_dut_none.isChecked():
            dut = "GND"
        elif self.rb_dut_gnd.isChecked():
            dut = "GND"
        elif self.rb_dut_guard.isChecked():
            dut = "GUARD"
        elif self.rb_dut_vsmu.isChecked():
            dut = "VSMU"
        elif self.rb_dut_su.isChecked():
            dut = "SU"
        elif self.rb_dut_vsmu_su.isChecked():
            dut = "VSMU_AND_SU"

        self._log(
            f"Programming relais: IV={iv_channel_text}/{iv_ref}, PA={pa_channel_text}, "
            f"HP={'ON' if high_pass else 'OFF'}, DUT={dut}, VGUARD={vguard}"
        )

        task = self.service.run_program_relais(
            iv_channel=iv_channel,
            iv_reference=iv_ref,
            pa_channel=pa_channel,
            highpass=high_pass,
            dut_routing=dut,
            vguard=vguard,
        )
        self._start_task(task)
