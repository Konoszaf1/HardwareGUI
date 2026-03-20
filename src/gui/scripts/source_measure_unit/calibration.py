"""Calibration page for Source Measure Unit calibration."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.gui.scripts.base_page import BaseHardwarePage
from src.gui.widgets.analysis_plot_widget import AnalysisPlotWidget
from src.gui.widgets.live_plot_widget import LivePlotWidget
from src.gui.widgets.shared_panels_widget import SharedPanelsWidget
from src.logic.services.smu_service import SourceMeasureUnitService

# VSMU mode mapping: display text -> value passed to service
_VSMU_MAP = {"Both": None, "Normal Only": False, "VSMU Only": True}

# Speed preset mapping
_SPEED_MAP = {"Fast": "fast", "Normal": "normal", "Precise": "precise"}


class SMUCalibrationPage(BaseHardwarePage):
    """Calibration page for Source Measure Unit.

    Provides controls for:
    - Measurement config: speed, VSMU mode, PA channels, scope (all/single)
    - Fitting config: model type, auto-calibrate EEPROM
    - Live progress table showing per-range status
    - Live scatter plot (I_ref vs I_meas) updated via data_chunk
    - Analysis plot display after fitting completes
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
        title = QLabel("Source Measure Unit – Calibration")
        title.setObjectName("title")
        main_layout.addWidget(title)

        # ==== Measurement Configuration ====
        meas_box = self._create_group_box("Measurement Configuration")
        meas_form = self._create_form_layout(meas_box)

        # Speed preset
        self.cb_speed = QComboBox()
        self.cb_speed.addItems(list(_SPEED_MAP.keys()))
        self.cb_speed.setCurrentText("Normal")
        self._configure_input(self.cb_speed)
        meas_form.addRow("Speed:", self.cb_speed)

        # VSMU mode
        self.cb_vsmu = QComboBox()
        self.cb_vsmu.addItems(list(_VSMU_MAP.keys()))
        self._configure_input(self.cb_vsmu)
        meas_form.addRow("VSMU Mode:", self.cb_vsmu)

        # PA Channels checkboxes
        pa_layout = QHBoxLayout()
        self.chk_pa = {}
        for pa in ["pach0", "pach1", "pach2", "pach3"]:
            chk = QCheckBox(pa)
            self._configure_input(chk)
            chk.setChecked(pa in ("pach0", "pach2", "pach3"))
            pa_layout.addWidget(chk)
            self.chk_pa[pa] = chk
        pa_layout.addStretch()
        meas_form.addRow("PA Channels:", pa_layout)

        # Scope: All ranges vs Single range
        self.cb_scope = QComboBox()
        self.cb_scope.addItems(["All Ranges", "Single Range"])
        self._configure_input(self.cb_scope)
        self.cb_scope.currentTextChanged.connect(self._on_scope_changed)
        meas_form.addRow("Scope:", self.cb_scope)

        # Single range selectors (hidden by default)
        self._single_range_widget = QWidget()
        sr_layout = QHBoxLayout(self._single_range_widget)
        sr_layout.setContentsMargins(0, 0, 0, 0)
        sr_layout.addWidget(QLabel("PA:"))
        self.cb_single_pa = QComboBox()
        self.cb_single_pa.addItems(["pach0", "pach1", "pach2", "pach3"])
        self._configure_input(self.cb_single_pa)
        sr_layout.addWidget(self.cb_single_pa)
        sr_layout.addWidget(QLabel("IV:"))
        self.cb_single_iv = QComboBox()
        self.cb_single_iv.addItems(
            [f"ivch{i}" for i in range(1, 10)]
        )
        self._configure_input(self.cb_single_iv)
        sr_layout.addWidget(self.cb_single_iv)
        sr_layout.addStretch()
        meas_form.addRow("", self._single_range_widget)
        self._single_range_widget.hide()

        # Measure / Verify / Cancel buttons
        btn_layout = QHBoxLayout()
        self.btn_measure = QPushButton("Measure")
        self._configure_input(self.btn_measure, min_width=100)
        self.btn_verify = QPushButton("Verify")
        self._configure_input(self.btn_verify, min_width=100)
        self._configure_input(self._btn_cancel, min_width=100)
        btn_layout.addWidget(self.btn_measure)
        btn_layout.addWidget(self.btn_verify)
        btn_layout.addWidget(self._btn_cancel)
        btn_layout.addStretch()
        meas_form.addRow("", btn_layout)

        main_layout.addWidget(meas_box)

        # ==== Fitting Configuration ====
        fit_box = self._create_group_box("Fitting Configuration")
        fit_form = self._create_form_layout(fit_box)

        model_layout = QHBoxLayout()
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
        fit_form.addRow("Model:", model_layout)

        self.chk_auto_eeprom = QCheckBox("Write to EEPROM after fit")
        self._configure_input(self.chk_auto_eeprom)
        self.chk_auto_eeprom.setChecked(False)
        fit_form.addRow("", self.chk_auto_eeprom)

        fit_btn_layout = QHBoxLayout()
        self.btn_run_fit = QPushButton("Run Fit")
        self._configure_input(self.btn_run_fit, min_width=100)
        fit_btn_layout.addWidget(self.btn_run_fit)
        fit_btn_layout.addStretch()
        fit_form.addRow("", fit_btn_layout)

        main_layout.addWidget(fit_box)

        # ==== Progress Table ====
        progress_box = self._create_group_box("Measurement Progress", min_height=180)
        progress_layout = QVBoxLayout(progress_box)
        progress_layout.setContentsMargins(12, 18, 12, 12)

        self._progress_label = QLabel("No measurement running")
        self._progress_label.setStyleSheet("color: #cccccc; font-size: 9pt;")
        progress_layout.addWidget(self._progress_label)

        self.progress_table = QTableWidget()
        self.progress_table.setColumnCount(5)
        self.progress_table.setHorizontalHeaderLabels(
            ["VSMU", "PA Channel", "IV Channel", "Status", "Points"]
        )
        self.progress_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.progress_table.setMinimumHeight(120)
        self.progress_table.verticalHeader().setDefaultSectionSize(24)
        self.progress_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        progress_layout.addWidget(self.progress_table)

        main_layout.addWidget(progress_box)

        # ==== Live Scatter Plot ====
        plot_box = self._create_group_box("Live Plot", min_height=250, expanding=True)
        plot_layout = QVBoxLayout(plot_box)
        plot_layout.setContentsMargins(12, 18, 12, 12)

        self.plot_widget = LivePlotWidget()
        self.plot_widget.set_labels("Calibration", "I_ref / A", "I_meas / A")
        self.plot_widget.setMinimumHeight(200)
        plot_layout.addWidget(self.plot_widget)

        main_layout.addWidget(plot_box)

        # ==== Analysis Plot (shown after fit) ====
        analysis_box = self._create_group_box(
            "Analysis", min_height=300, expanding=True,
        )
        analysis_layout = QVBoxLayout(analysis_box)
        analysis_layout.setContentsMargins(12, 18, 12, 12)

        self.analysis_widget = AnalysisPlotWidget()
        self.analysis_widget.setMinimumHeight(250)
        analysis_layout.addWidget(self.analysis_widget)

        main_layout.addWidget(analysis_box)

        # Register action buttons
        self._action_buttons = [self.btn_measure, self.btn_verify, self.btn_run_fit]

        # ==== Signals ====
        self.btn_measure.clicked.connect(self._on_measure)
        self.btn_verify.clicked.connect(self._on_verify)
        self.btn_run_fit.clicked.connect(self._on_run_fit)

        self._connect_service_signals()

        # Progress tracking state
        self._range_rows: dict[str, int] = {}
        self._loading_status = False

        # Auto-load calibration status on init
        QTimer.singleShot(500, self._load_calibration_status)

    # ---- Config helpers ----

    def _get_vsmu_mode(self) -> bool | None:
        return _VSMU_MAP.get(self.cb_vsmu.currentText())

    def _get_speed_preset(self) -> str:
        return _SPEED_MAP.get(self.cb_speed.currentText(), "normal")

    def _get_pa_channels(self) -> list[str]:
        return [name for name, chk in self.chk_pa.items() if chk.isChecked()]

    def _get_single_range(self) -> tuple[str, str] | None:
        if self.cb_scope.currentText() == "Single Range":
            return (self.cb_single_pa.currentText(), self.cb_single_iv.currentText())
        return None

    def _on_scope_changed(self, text: str) -> None:
        self._single_range_widget.setVisible(text == "Single Range")

    # ---- Actions ----

    def _on_measure(self) -> None:
        self._start_calibration_measure(verify=False)

    def _on_verify(self) -> None:
        self._start_calibration_measure(verify=True)

    def _start_calibration_measure(self, verify: bool) -> None:
        if not self.service:
            self._log("Service not available.")
            return

        pa_channels = self._get_pa_channels()
        if not pa_channels:
            self._log("Select at least one PA channel.")
            return

        label = "verification" if verify else "measurement"
        self._log(f"Starting calibration {label}...")
        self.plot_widget.clear()
        self.plot_widget.set_labels(
            f"Calibration {'Verify' if verify else 'Measure'}",
            "I_ref / A", "I_meas / A",
        )
        self._reset_progress_table()

        task = self.service.run_calibration_measure(
            vsmu_mode=self._get_vsmu_mode(),
            verify_calibration=verify,
            pa_channels=pa_channels,
            speed_preset=self._get_speed_preset(),
            single_range=self._get_single_range(),
        )
        if not task:
            self._log("Keithley IP not configured. Set it on the Connection page first.")
            return
        task.signals.data_chunk.connect(self._on_cal_chunk)
        self._start_task(task)

    def _on_run_fit(self) -> None:
        if not self.service:
            self._log("Service not available.")
            return

        model = "linear" if self.rb_linear.isChecked() else "gp"
        auto_cal = self.chk_auto_eeprom.isChecked()
        self._log(f"Running {model} fit (auto-EEPROM: {auto_cal})...")
        self.analysis_widget.clear()

        task = self.service.run_calibration_fit(
            draw_plot=True,
            auto_calibrate=auto_cal,
            model_type=model,
        )
        self._start_task(task)

    # ---- Live data handling ----

    def _on_cal_chunk(self, data) -> None:
        if not isinstance(data, dict):
            return

        chunk_type = data.get("type")

        if chunk_type == "cal_point":
            # Update scatter plot
            vsmu = data.get("vsmu", False)
            pa = data.get("pa", "?")
            iv = data.get("iv", "?")
            series = f"{'V' if vsmu else 'G'} {pa} {iv}"
            self.plot_widget.append_point(series, data["x"], data["y"])

            # Update progress label
            idx = data.get("point_index", 0)
            total = data.get("total_points", 0)
            if total > 0:
                pct = idx * 100 // total
                self._progress_label.setText(
                    f"Progress: {idx}/{total} points ({pct}%)"
                )

            # Update points column in table
            key = f"{vsmu}|{pa}|{iv}"
            if key in self._range_rows:
                row = self._range_rows[key]
                pts_item = self.progress_table.item(row, 4)
                if pts_item:
                    current = int(pts_item.text() or "0")
                    pts_item.setText(str(current + 1))

        elif chunk_type == "cal_range":
            status = data.get("status", "")
            pa = data.get("pa", "")
            iv = data.get("iv", "")
            vsmu = data.get("vsmu", False)
            key = f"{vsmu}|{pa}|{iv}"

            if status == "running":
                self._add_progress_row(key, vsmu, pa, iv)
            elif status == "done":
                self._update_progress_row(
                    key, "Done",
                    points=data.get("points", 0),
                    duration=data.get("duration"),
                )

    # ---- Progress table management ----

    def _reset_progress_table(self) -> None:
        self.progress_table.setRowCount(0)
        self._range_rows.clear()
        self._progress_label.setText("Measurement starting...")

    def _add_progress_row(self, key: str, vsmu, pa: str, iv: str) -> None:
        row = self.progress_table.rowCount()
        self.progress_table.insertRow(row)
        self.progress_table.setItem(row, 0, QTableWidgetItem(str(vsmu)))
        self.progress_table.setItem(row, 1, QTableWidgetItem(pa))
        self.progress_table.setItem(row, 2, QTableWidgetItem(iv))
        running_item = QTableWidgetItem("Running")
        running_item.setForeground(Qt.GlobalColor.yellow)
        self.progress_table.setItem(row, 3, running_item)
        self.progress_table.setItem(row, 4, QTableWidgetItem("0"))
        self._range_rows[key] = row
        self.progress_table.scrollToBottom()

    def _update_progress_row(
        self, key: str, status: str,
        points: int = 0, duration: float | None = None,
    ) -> None:
        if key not in self._range_rows:
            return
        row = self._range_rows[key]
        status_text = status
        if duration is not None:
            status_text += f" ({duration:.1f}s)"
        done_item = QTableWidgetItem(status_text)
        done_item.setForeground(Qt.GlobalColor.green)
        self.progress_table.setItem(row, 3, done_item)
        if points > 0:
            self.progress_table.setItem(row, 4, QTableWidgetItem(str(points)))

    # ---- Calibration status ----

    def _load_calibration_status(self) -> None:
        """Load calibration status from disk and populate the progress table."""
        if not self.service or self._loading_status:
            return
        task = self.service.run_load_calibration_status()
        if task is None:
            return
        self._loading_status = True
        task.signals.finished.connect(self._on_status_loaded)
        self._start_task(task)

    def _on_status_loaded(self, result) -> None:
        """Handle calibration status load result."""
        self._loading_status = False
        data = getattr(result, "data", None)
        if not isinstance(data, dict):
            return
        status_list = data.get("calibration_status", [])
        if status_list:
            self._show_calibration_status(status_list)

    def _show_calibration_status(self, ranges: list[dict]) -> None:
        """Populate the progress table with per-range measured/calibrated status."""
        self.progress_table.setRowCount(0)
        self._range_rows.clear()
        n_calibrated = 0
        n_measured = 0
        for info in ranges:
            row = self.progress_table.rowCount()
            self.progress_table.insertRow(row)
            vsmu = info.get("vsmu", False)
            pa = info.get("pa", "")
            iv = info.get("iv", "")
            calibrated = info.get("calibrated", False)
            measured = info.get("measured", False)

            self.progress_table.setItem(row, 0, QTableWidgetItem(str(vsmu)))
            self.progress_table.setItem(row, 1, QTableWidgetItem(pa))
            self.progress_table.setItem(row, 2, QTableWidgetItem(iv))

            if calibrated:
                status_item = QTableWidgetItem("Calibrated")
                status_item.setForeground(Qt.GlobalColor.cyan)
                n_calibrated += 1
            elif measured:
                status_item = QTableWidgetItem("Measured")
                status_item.setForeground(Qt.GlobalColor.yellow)
                n_measured += 1
            else:
                status_item = QTableWidgetItem("")

            self.progress_table.setItem(row, 3, status_item)
            self.progress_table.setItem(row, 4, QTableWidgetItem(""))

        total = len(ranges)
        self._progress_label.setText(
            f"{n_calibrated}/{total} ranges calibrated"
            + (f", {n_measured} measured" if n_measured else "")
        )

    # ---- Task finished ----

    def _on_task_finished(self, result) -> None:
        data = getattr(result, "data", None)
        if isinstance(data, dict):
            # Handle cancellation
            if data.get("cancelled"):
                completed = data.get("completed_ranges", 0)
                total = data.get("total_ranges", "?")
                self._progress_label.setText(
                    f"Cancelled: {completed}/{total} ranges measured and saved"
                )
                self._log(f"Measurement cancelled after {completed}/{total} ranges.")
                super()._on_task_finished(result)
                return

            # Show analysis plots if available
            plots = data.get("analysis_plots", [])
            if plots:
                self._log(f"Loading {len(plots)} analysis plots...")
                self.analysis_widget.set_images(plots)

            # Show calibrated ranges in progress table
            cal_ranges = data.get("calibrated_ranges", [])
            if cal_ranges:
                self._show_calibrated_ranges(cal_ranges)

        self._progress_label.setText("Idle")
        super()._on_task_finished(result)

        # Refresh calibration status after measurement or fit (not after status load itself)
        task_name = getattr(result, "name", "")
        if task_name != "Load Cal Status":
            self._load_calibration_status()

    def _show_calibrated_ranges(self, ranges: list[dict]) -> None:
        """Populate the progress table with calibrated range status (from fit results)."""
        self.progress_table.setRowCount(0)
        self._range_rows.clear()
        for info in ranges:
            row = self.progress_table.rowCount()
            self.progress_table.insertRow(row)
            vsmu = info.get("vsmu", False)
            pa = info.get("pa", "")
            iv = info.get("iv", "")
            self.progress_table.setItem(row, 0, QTableWidgetItem(str(vsmu)))
            self.progress_table.setItem(row, 1, QTableWidgetItem(pa))
            self.progress_table.setItem(row, 2, QTableWidgetItem(iv))
            status_item = QTableWidgetItem("Calibrated")
            status_item.setForeground(Qt.GlobalColor.cyan)
            self.progress_table.setItem(row, 3, status_item)
            self.progress_table.setItem(row, 4, QTableWidgetItem(""))
        self._progress_label.setText(
            f"{len(ranges)} ranges calibrated"
        )
