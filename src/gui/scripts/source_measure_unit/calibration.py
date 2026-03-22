"""Calibration page for Source Measure Unit calibration."""

import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFrame,
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

# Unified table column indices
_COL_VSMU = 0
_COL_PA = 1
_COL_IV = 2
_COL_MEASURED = 3
_COL_VERIFIED = 4
_COL_FITTED = 5
_COL_STATUS = 6


def _status_item(text: str, color: Qt.GlobalColor) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setForeground(color)
    return item


class SMUCalibrationPage(BaseHardwarePage):
    """Calibration page for Source Measure Unit.

    Layout (top to bottom):
    - Sticky progress bar (always visible): progress label + elapsed timer
    - Scrollable content:
      - Measurement config (speed, VSMU, PA channels, scope, buttons)
      - Fitting config (model, auto-EEPROM, Run Fit)
      - Unified calibration ranges table (measured/verified/fitted + live status)
      - Live scatter plot
      - Analysis plots
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        service: SourceMeasureUnitService | None = None,
        shared_panels: SharedPanelsWidget | None = None,
    ):
        super().__init__(parent, service, shared_panels)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # ==== Sticky progress bar (outside scroll) ====
        self._progress_bar = QFrame()
        self._progress_bar.setStyleSheet(
            "QFrame { background: #2a2a2a; border-bottom: 1px solid #444; }"
        )
        bar_layout = QHBoxLayout(self._progress_bar)
        bar_layout.setContentsMargins(12, 6, 12, 6)

        self._progress_label = QLabel("Idle")
        self._progress_label.setStyleSheet("color: #cccccc; font-size: 9pt;")
        bar_layout.addWidget(self._progress_label)
        bar_layout.addStretch()
        self._timer_label = QLabel("")
        self._timer_label.setStyleSheet(
            "color: #aaaaaa; font-size: 9pt; font-family: monospace;"
        )
        bar_layout.addWidget(self._timer_label)

        outer_layout.addWidget(self._progress_bar)

        # ==== Scrollable content ====
        scroll, content, main_layout = self._create_scroll_area(min_width=600)
        outer_layout.addWidget(scroll)

        # ==== Title ====
        title = QLabel("Source Measure Unit – Calibration")
        title.setObjectName("title")
        main_layout.addWidget(title)

        # ==== Measurement Configuration ====
        meas_box = self._create_group_box("Measurement Configuration")
        meas_form = self._create_form_layout(meas_box)

        self.cb_speed = QComboBox()
        self.cb_speed.addItems(list(_SPEED_MAP.keys()))
        self.cb_speed.setCurrentText("Normal")
        self._configure_input(self.cb_speed)
        meas_form.addRow("Speed:", self.cb_speed)

        self.cb_vsmu = QComboBox()
        self.cb_vsmu.addItems(list(_VSMU_MAP.keys()))
        self._configure_input(self.cb_vsmu)
        meas_form.addRow("VSMU Mode:", self.cb_vsmu)

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
        self.cb_single_iv.addItems([f"ivch{i}" for i in range(1, 10)])
        self._configure_input(self.cb_single_iv)
        sr_layout.addWidget(self.cb_single_iv)
        sr_layout.addStretch()
        meas_form.addRow("", self._single_range_widget)
        self._single_range_widget.hide()

        btn_layout = QHBoxLayout()
        # Primary action: full workflow (measure + verify), matching original script
        self.btn_verify = QPushButton("Measure + Verify")
        self._configure_input(self.btn_verify, min_width=140)
        # Secondary action: measurement only, skip verification pass
        self.btn_measure = QPushButton("Measure Only")
        self._configure_input(self.btn_measure, min_width=110)
        self._configure_input(self._btn_cancel, min_width=100)
        btn_layout.addWidget(self.btn_verify)
        btn_layout.addWidget(self.btn_measure)
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

        # ==== Unified Calibration Ranges Table ====
        ranges_box = self._create_group_box("Calibration Ranges", min_height=220)
        ranges_layout = QVBoxLayout(ranges_box)
        ranges_layout.setContentsMargins(12, 18, 12, 12)

        self._overview_summary = QLabel("No calibration data found")
        self._overview_summary.setStyleSheet("color: #cccccc; font-size: 9pt;")
        ranges_layout.addWidget(self._overview_summary)

        self.ranges_table = QTableWidget()
        self.ranges_table.setColumnCount(7)
        self.ranges_table.setHorizontalHeaderLabels(
            ["VSMU", "PA Channel", "IV Channel",
             "Measured", "Verified", "Fitted", "Status"]
        )
        header = self.ranges_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.ranges_table.setMinimumHeight(150)
        self.ranges_table.verticalHeader().setDefaultSectionSize(24)
        self.ranges_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.ranges_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.ranges_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.ranges_table.cellClicked.connect(self._on_range_row_clicked)
        ranges_layout.addWidget(self.ranges_table)

        ranges_btn_layout = QHBoxLayout()
        self.btn_refresh = QPushButton("Refresh")
        self._configure_input(self.btn_refresh, min_width=100)
        self.btn_refresh.clicked.connect(self._load_calibration_status)
        ranges_btn_layout.addWidget(self.btn_refresh)
        ranges_btn_layout.addStretch()
        ranges_layout.addLayout(ranges_btn_layout)

        main_layout.addWidget(ranges_box)

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
        self._action_buttons = [
            self.btn_measure, self.btn_verify, self.btn_run_fit, self.btn_refresh,
        ]

        # ==== Signals ====
        self.btn_measure.clicked.connect(self._on_measure)
        self.btn_verify.clicked.connect(self._on_verify)
        self.btn_run_fit.clicked.connect(self._on_run_fit)

        self._connect_service_signals()

        # State
        self._row_keys: dict[str, int] = {}   # "vsmu|pa|iv" -> row index
        self._range_points: dict[str, int] = {}  # live point counts per range
        self._loading_status = False
        self._measuring = False

        # Elapsed timer
        self._measure_start: float = 0.0
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(1000)
        self._elapsed_timer.timeout.connect(self._update_elapsed)

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

    # ---- Row-click → populate single-range selector ----

    def _on_range_row_clicked(self, row: int, _col: int) -> None:
        pa_item = self.ranges_table.item(row, _COL_PA)
        iv_item = self.ranges_table.item(row, _COL_IV)
        if not pa_item or not iv_item:
            return
        pa = pa_item.text()
        iv = iv_item.text()
        # Switch to Single Range mode and populate selectors
        self.cb_scope.setCurrentText("Single Range")
        idx_pa = self.cb_single_pa.findText(pa)
        if idx_pa >= 0:
            self.cb_single_pa.setCurrentIndex(idx_pa)
        idx_iv = self.cb_single_iv.findText(iv)
        if idx_iv >= 0:
            self.cb_single_iv.setCurrentIndex(idx_iv)

    # ---- Elapsed timer ----

    @staticmethod
    def _format_elapsed(seconds: float) -> str:
        s = int(seconds)
        h, s = divmod(s, 3600)
        m, s = divmod(s, 60)
        if h:
            return f"{h:d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def _start_elapsed_timer(self) -> None:
        self._measure_start = time.monotonic()
        self._timer_label.setText("00:00")
        self._elapsed_timer.start()

    def _stop_elapsed_timer(self) -> None:
        self._elapsed_timer.stop()
        if self._measure_start:
            elapsed = time.monotonic() - self._measure_start
            self._timer_label.setText(f"Total: {self._format_elapsed(elapsed)}")

    def _update_elapsed(self) -> None:
        elapsed = time.monotonic() - self._measure_start
        self._timer_label.setText(self._format_elapsed(elapsed))

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
        # Clear live status column but keep overview data
        self._clear_status_column()
        self._range_points.clear()
        self._measuring = True
        self._start_elapsed_timer()
        self._progress_label.setText("Measurement starting...")

        task = self.service.run_calibration_measure(
            vsmu_mode=self._get_vsmu_mode(),
            verify_calibration=verify,
            pa_channels=pa_channels,
            speed_preset=self._get_speed_preset(),
            single_range=self._get_single_range(),
        )
        if not task:
            self._stop_elapsed_timer()
            self._measuring = False
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
        self._start_elapsed_timer()
        self._progress_label.setText("Fitting...")

        task = self.service.run_calibration_fit(
            draw_plot=True,
            auto_calibrate=auto_cal,
            model_type=model,
        )
        self._start_task(task)

    # ---- Unified table helpers ----

    @staticmethod
    def _range_key(vsmu, pa: str, iv: str) -> str:
        return f"{vsmu}|{pa}|{iv}"

    def _find_or_insert_row(self, vsmu, pa: str, iv: str) -> int:
        """Find existing row for this range or insert a new one."""
        key = self._range_key(vsmu, pa, iv)
        if key in self._row_keys:
            return self._row_keys[key]
        row = self.ranges_table.rowCount()
        self.ranges_table.insertRow(row)
        self.ranges_table.setItem(row, _COL_VSMU, QTableWidgetItem(str(vsmu)))
        self.ranges_table.setItem(row, _COL_PA, QTableWidgetItem(pa))
        self.ranges_table.setItem(row, _COL_IV, QTableWidgetItem(iv))
        # Persistent columns default to "--"
        for col in (_COL_MEASURED, _COL_VERIFIED, _COL_FITTED):
            self.ranges_table.setItem(
                row, col, _status_item("--", Qt.GlobalColor.darkGray),
            )
        self.ranges_table.setItem(row, _COL_STATUS, QTableWidgetItem(""))
        self._row_keys[key] = row
        return row

    def _clear_status_column(self) -> None:
        """Clear the live Status column for all rows."""
        for row in range(self.ranges_table.rowCount()):
            self.ranges_table.setItem(row, _COL_STATUS, QTableWidgetItem(""))

    # ---- Live data handling ----

    def _on_cal_chunk(self, data) -> None:
        if not isinstance(data, dict):
            return

        chunk_type = data.get("type")

        if chunk_type == "cal_point":
            vsmu = data.get("vsmu", False)
            pa = data.get("pa", "?")
            iv = data.get("iv", "?")
            series = f"{'V' if vsmu else 'G'} {pa} {iv}"
            self.plot_widget.append_point(series, data["x"], data["y"])

            # Update sticky progress label
            idx = data.get("point_index", 0)
            total = data.get("total_points", 0)
            if total > 0:
                pct = idx * 100 // total
                self._progress_label.setText(
                    f"Progress: {idx}/{total} points ({pct}%)"
                )

            # Update Status column with point count
            key = self._range_key(vsmu, pa, iv)
            if key in self._row_keys:
                pts = self._range_points.get(key, 0) + 1
                self._range_points[key] = pts
                row = self._row_keys[key]
                status_item = self.ranges_table.item(row, _COL_STATUS)
                if status_item:
                    status_item.setText(f"Running ({pts} pts)")

        elif chunk_type == "cal_range":
            status = data.get("status", "")
            pa = data.get("pa", "")
            iv = data.get("iv", "")
            vsmu = data.get("vsmu", False)
            key = self._range_key(vsmu, pa, iv)

            if status == "running":
                row = self._find_or_insert_row(vsmu, pa, iv)
                item = _status_item("Running", Qt.GlobalColor.yellow)
                self.ranges_table.setItem(row, _COL_STATUS, item)
                self._range_points[key] = 0
                self.ranges_table.scrollToItem(
                    self.ranges_table.item(row, _COL_STATUS),
                )

            elif status == "done":
                if key in self._row_keys:
                    row = self._row_keys[key]
                    pts = data.get("points", 0)
                    duration = data.get("duration")
                    text = "Done"
                    if pts:
                        text += f" ({pts} pts"
                        if duration is not None:
                            text += f", {duration:.1f}s"
                        text += ")"
                    elif duration is not None:
                        text += f" ({duration:.1f}s)"
                    item = _status_item(text, Qt.GlobalColor.green)
                    self.ranges_table.setItem(row, _COL_STATUS, item)

    # ---- Calibration status (disk) ----

    def _load_calibration_status(self) -> None:
        if not self.service or self._loading_status:
            return
        task = self.service.run_load_calibration_status()
        if task is None:
            return
        self._loading_status = True
        task.signals.finished.connect(self._on_status_loaded)
        self._start_task(task)

    def _on_status_loaded(self, result) -> None:
        self._loading_status = False
        data = getattr(result, "data", None)
        if not isinstance(data, dict):
            return
        status_list = data.get("calibration_status", [])
        self._populate_ranges_table(status_list)

    def _populate_ranges_table(self, ranges: list[dict]) -> None:
        """Rebuild the unified table from disk-loaded calibration status."""
        self.ranges_table.setRowCount(0)
        self._row_keys.clear()
        n_measured = 0
        n_verified = 0
        n_fitted = 0

        for info in ranges:
            vsmu = info.get("vsmu", False)
            pa = info.get("pa", "")
            iv = info.get("iv", "")
            measured = info.get("measured", False)
            verified = info.get("verified", False)
            calibrated = info.get("calibrated", False)

            row = self._find_or_insert_row(vsmu, pa, iv)

            if measured:
                self.ranges_table.setItem(
                    row, _COL_MEASURED, _status_item("Yes", Qt.GlobalColor.green),
                )
                n_measured += 1
            if verified:
                self.ranges_table.setItem(
                    row, _COL_VERIFIED, _status_item("Yes", Qt.GlobalColor.green),
                )
                n_verified += 1
            if calibrated:
                self.ranges_table.setItem(
                    row, _COL_FITTED, _status_item("Yes", Qt.GlobalColor.cyan),
                )
                n_fitted += 1

        total = len(ranges)
        if total == 0:
            self._overview_summary.setText("No calibration data found")
            return

        parts = [f"{total} ranges"]
        if n_measured:
            parts.append(f"{n_measured} measured")
        if n_verified:
            parts.append(f"{n_verified} verified")
        if n_fitted:
            parts.append(f"{n_fitted} fitted")
        self._overview_summary.setText(" | ".join(parts))

    # ---- Task finished ----

    def _on_task_finished(self, result) -> None:
        self._stop_elapsed_timer()
        self._measuring = False

        data = getattr(result, "data", None)
        if isinstance(data, dict):
            if data.get("cancelled"):
                completed = data.get("completed_ranges", 0)
                total = data.get("total_ranges", "?")
                self._progress_label.setText(
                    f"Cancelled: {completed}/{total} ranges measured and saved"
                )
                self._log(f"Measurement cancelled after {completed}/{total} ranges.")
                super()._on_task_finished(result)
                return

            plots = data.get("analysis_plots", [])
            if plots:
                self._log(f"Loading {len(plots)} analysis plots...")
                self.analysis_widget.set_images(plots)

        self._progress_label.setText("Idle")
        super()._on_task_finished(result)

        # Refresh table from disk after measurement or fit
        task_name = getattr(result, "name", "")
        if task_name != "Load Cal Status":
            self._load_calibration_status()
