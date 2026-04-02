"""Calibration page for Sampling Unit voltage channel calibration."""

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
    QMessageBox,
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
from src.logic.services.su_service import SamplingUnitService

# Speed preset mapping
_SPEED_MAP = {"Fast": "fast", "Normal": "normal", "Precise": "precise"}

# Table column indices
_COL_AMP = 0
_COL_POINTS = 1
_COL_MEASURED = 2
_COL_VERIFIED = 3
_COL_FITTED = 4
_COL_STATUS = 5


def _status_item(text: str, color: Qt.GlobalColor) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setForeground(color)
    return item


class SUCalibrationPage(BaseHardwarePage):
    """Calibration page for Sampling Unit.

    Layout (top to bottom):
    - Sticky progress bar (always visible): progress label + elapsed timer
    - Scrollable content:
      - Measurement config (speed, amp channels, scope, buttons)
      - Fitting config (model, auto-EEPROM, scope, Run Fit)
      - Calibration ranges table (measured/verified/fitted + live status)
      - Live scatter plot
      - Analysis plots
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        service: SamplingUnitService | None = None,
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
        self._timer_label.setStyleSheet("color: #aaaaaa; font-size: 9pt; font-family: monospace;")
        bar_layout.addWidget(self._timer_label)

        outer_layout.addWidget(self._progress_bar)

        # ==== Scrollable content ====
        scroll, content, main_layout = self._create_scroll_area(min_width=600)
        outer_layout.addWidget(scroll)

        # ==== Title ====
        title = QLabel("Sampling Unit \u2013 Calibration")
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

        amp_layout = QHBoxLayout()
        self.chk_amp: dict[str, QCheckBox] = {}
        for amp in ["AMP01", "AMP1", "AMP2", "AMP3"]:
            chk = QCheckBox(amp)
            self._configure_input(chk)
            chk.setChecked(amp in ("AMP01", "AMP1"))
            amp_layout.addWidget(chk)
            self.chk_amp[amp] = chk
        amp_layout.addStretch()
        meas_form.addRow("AMP Channels:", amp_layout)

        self.cb_scope = QComboBox()
        self.cb_scope.addItems(["All Ranges", "Single Range"])
        self._configure_input(self.cb_scope)
        self.cb_scope.currentTextChanged.connect(self._on_scope_changed)
        meas_form.addRow("Scope:", self.cb_scope)

        # Single range selector (hidden by default)
        self._single_range_widget = QWidget()
        sr_layout = QHBoxLayout(self._single_range_widget)
        sr_layout.setContentsMargins(0, 0, 0, 0)
        sr_layout.addWidget(QLabel("AMP:"))
        self.cb_single_amp = QComboBox()
        self.cb_single_amp.addItems(["AMP01", "AMP1", "AMP2", "AMP3"])
        self._configure_input(self.cb_single_amp)
        sr_layout.addWidget(self.cb_single_amp)
        sr_layout.addStretch()
        meas_form.addRow("", self._single_range_widget)
        self._single_range_widget.hide()

        btn_layout = QHBoxLayout()
        # Primary: full workflow (measure + verify)
        self.btn_verify = QPushButton("Measure + Verify")
        self._configure_input(self.btn_verify, min_width=140)
        # Secondary: measurement only
        self.btn_measure = QPushButton("Measure Only")
        self._configure_input(self.btn_measure, min_width=110)
        # Verify-only: re-run verification pass
        self.btn_verify_only = QPushButton("Verify Only")
        self._configure_input(self.btn_verify_only, min_width=110)
        self._configure_input(self._btn_cancel, min_width=100)
        btn_layout.addWidget(self.btn_verify)
        btn_layout.addWidget(self.btn_measure)
        btn_layout.addWidget(self.btn_verify_only)
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

        # Fit scope selector
        self.cb_fit_scope = QComboBox()
        self.cb_fit_scope.addItems(["All Ranges", "Single Range"])
        self._configure_input(self.cb_fit_scope)
        self.cb_fit_scope.currentTextChanged.connect(self._on_fit_scope_changed)
        fit_form.addRow("Scope:", self.cb_fit_scope)

        # Fit single-range selector (hidden by default)
        self._fit_single_range_widget = QWidget()
        fsr_layout = QHBoxLayout(self._fit_single_range_widget)
        fsr_layout.setContentsMargins(0, 0, 0, 0)
        fsr_layout.addWidget(QLabel("AMP:"))
        self.cb_fit_amp = QComboBox()
        self.cb_fit_amp.addItems(["AMP01", "AMP1", "AMP2", "AMP3"])
        self._configure_input(self.cb_fit_amp)
        fsr_layout.addWidget(self.cb_fit_amp)
        fsr_layout.addStretch()
        fit_form.addRow("", self._fit_single_range_widget)
        self._fit_single_range_widget.hide()

        fit_btn_layout = QHBoxLayout()
        self.btn_run_fit = QPushButton("Run Fit")
        self._configure_input(self.btn_run_fit, min_width=100)
        fit_btn_layout.addWidget(self.btn_run_fit)
        fit_btn_layout.addStretch()
        fit_form.addRow("", fit_btn_layout)

        main_layout.addWidget(fit_box)

        # ==== Calibration Ranges Table ====
        ranges_box = self._create_group_box("Calibration Ranges", min_height=180)
        ranges_layout = QVBoxLayout(ranges_box)
        ranges_layout.setContentsMargins(12, 18, 12, 12)

        self._overview_summary = QLabel("No calibration data found")
        self._overview_summary.setStyleSheet("color: #cccccc; font-size: 9pt;")
        ranges_layout.addWidget(self._overview_summary)

        self.ranges_table = QTableWidget()
        self.ranges_table.setColumnCount(6)
        self.ranges_table.setHorizontalHeaderLabels(
            ["AMP Channel", "Points", "Measured", "Verified", "Fitted", "Status"]
        )
        header = self.ranges_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.ranges_table.setMinimumHeight(120)
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

        self.btn_delete_selected = QPushButton("Delete Selected")
        self._configure_input(self.btn_delete_selected, min_width=120)
        self.btn_delete_selected.clicked.connect(self._on_delete_selected)
        ranges_btn_layout.addWidget(self.btn_delete_selected)

        self.btn_clear_raw = QPushButton("Clear Raw Data")
        self._configure_input(self.btn_clear_raw, min_width=120)
        self.btn_clear_raw.clicked.connect(self._on_clear_raw)
        ranges_btn_layout.addWidget(self.btn_clear_raw)

        self.btn_clear_verify = QPushButton("Clear Verify Data")
        self._configure_input(self.btn_clear_verify, min_width=130)
        self.btn_clear_verify.clicked.connect(self._on_clear_verify)
        ranges_btn_layout.addWidget(self.btn_clear_verify)

        self.btn_clear_fitted = QPushButton("Clear Fitted Data")
        self._configure_input(self.btn_clear_fitted, min_width=130)
        self.btn_clear_fitted.clicked.connect(self._on_clear_fitted)
        ranges_btn_layout.addWidget(self.btn_clear_fitted)

        ranges_btn_layout.addStretch()
        ranges_layout.addLayout(ranges_btn_layout)

        main_layout.addWidget(ranges_box)

        # ==== Live Scatter Plot ====
        plot_box = self._create_group_box("Live Plot", min_height=250, expanding=True)
        plot_layout = QVBoxLayout(plot_box)
        plot_layout.setContentsMargins(12, 18, 12, 12)

        # Range selector above the plot
        plot_selector_layout = QHBoxLayout()
        plot_selector_layout.addWidget(QLabel("View:"))
        self.cb_plot_range = QComboBox()
        self._configure_input(self.cb_plot_range, min_width=200)
        self.cb_plot_range.addItem("Current")
        self.cb_plot_range.addItem("All")
        self.cb_plot_range.currentIndexChanged.connect(self._on_plot_range_changed)
        plot_selector_layout.addWidget(self.cb_plot_range)
        plot_selector_layout.addStretch()
        plot_layout.addLayout(plot_selector_layout)

        self.plot_widget = LivePlotWidget()
        self.plot_widget.set_labels("Calibration", "V_ref / V", "V_meas / V")
        self.plot_widget.setMinimumHeight(200)
        plot_layout.addWidget(self.plot_widget)

        main_layout.addWidget(plot_box)

        # ==== Analysis Plots (shown after fit) ====
        analysis_box = self._create_group_box(
            "Analysis",
            min_height=300,
            expanding=True,
        )
        analysis_layout = QVBoxLayout(analysis_box)
        analysis_layout.setContentsMargins(12, 18, 12, 12)

        self.analysis_widget = AnalysisPlotWidget()
        self.analysis_widget.setMinimumHeight(250)
        analysis_layout.addWidget(self.analysis_widget)

        main_layout.addWidget(analysis_box)

        # Register action buttons
        self._action_buttons = [
            self.btn_measure,
            self.btn_verify,
            self.btn_verify_only,
            self.btn_run_fit,
            self.btn_refresh,
            self.btn_delete_selected,
            self.btn_clear_raw,
            self.btn_clear_verify,
            self.btn_clear_fitted,
        ]

        # ==== Signals ====
        self.btn_measure.clicked.connect(self._on_measure)
        self.btn_verify.clicked.connect(self._on_verify)
        self.btn_verify_only.clicked.connect(self._on_verify_only)
        self.btn_run_fit.clicked.connect(self._on_run_fit)

        self._connect_service_signals()

        # State
        self._row_keys: dict[str, int] = {}  # amp_channel -> row index
        self._range_points: dict[str, int] = {}  # live point counts per range
        self._active_series: set[str] = set()  # currently active series names
        self._completed_series: list[str] = []  # finished series in order
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

    def _get_speed_preset(self) -> str:
        return _SPEED_MAP.get(self.cb_speed.currentText(), "normal")

    def _get_amp_channels(self) -> list[str]:
        return [name for name, chk in self.chk_amp.items() if chk.isChecked()]

    def _get_single_range(self) -> str | None:
        if self.cb_scope.currentText() == "Single Range":
            return self.cb_single_amp.currentText()
        return None

    def _on_scope_changed(self, text: str) -> None:
        self._single_range_widget.setVisible(text == "Single Range")

    def _on_fit_scope_changed(self, text: str) -> None:
        self._fit_single_range_widget.setVisible(text == "Single Range")

    # ---- Row-click -> populate single-range selector ----

    def _on_range_row_clicked(self, row: int, _col: int) -> None:
        amp_item = self.ranges_table.item(row, _COL_AMP)
        if not amp_item:
            return
        amp = amp_item.text()

        # Populate measurement scope selectors
        self.cb_scope.setCurrentText("Single Range")
        idx = self.cb_single_amp.findText(amp)
        if idx >= 0:
            self.cb_single_amp.setCurrentIndex(idx)

        # Populate fit scope selectors
        self.cb_fit_scope.setCurrentText("Single Range")
        idx = self.cb_fit_amp.findText(amp)
        if idx >= 0:
            self.cb_fit_amp.setCurrentIndex(idx)

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

    def _on_verify_only(self) -> None:
        self._start_calibration_measure(verify=False, verify_only=True)

    def _start_calibration_measure(
        self,
        verify: bool,
        verify_only: bool = False,
    ) -> None:
        if not self.service:
            self._log("Service not available.")
            return

        amp_channels = self._get_amp_channels()
        if not amp_channels:
            self._log("Select at least one AMP channel.")
            return

        if verify_only:
            label = "verify-only"
        elif verify:
            label = "measure + verify"
        else:
            label = "measurement"
        self._log(f"Starting calibration {label}...")
        self.plot_widget.clear()
        self.plot_widget.set_labels(
            f"Calibration {'Verify' if (verify or verify_only) else 'Measure'}",
            "V_ref / V",
            "V_meas / V",
        )
        # Reset plot range selector
        self._completed_series.clear()
        self._active_series.clear()
        self.cb_plot_range.blockSignals(True)
        while self.cb_plot_range.count() > 2:  # keep "Current" and "All"
            self.cb_plot_range.removeItem(1)
        self.cb_plot_range.setCurrentIndex(0)  # "Current"
        self.cb_plot_range.blockSignals(False)
        # Clear live status column but keep overview data
        self._clear_status_column()
        self._range_points.clear()
        self._measuring = True
        self._start_elapsed_timer()
        self._progress_label.setText("Measurement starting...")

        task = self.service.run_calibration_measure(
            verify_calibration=verify,
            verify_only=verify_only,
            amp_channels=amp_channels,
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
        is_single = self.cb_fit_scope.currentText() == "Single Range"

        single_range = None
        if is_single:
            single_range = self.cb_fit_amp.currentText()

        # Log what we're doing
        if single_range:
            self._log(f"Running {model} fit for {single_range}...")
        else:
            self._log(f"Running {model} fit on all ranges (auto-EEPROM: {auto_cal})...")

        self.analysis_widget.clear()
        self._start_elapsed_timer()
        self._progress_label.setText("Fitting...")

        task = self.service.run_calibration_fit(
            draw_plot=not bool(single_range),
            auto_calibrate=auto_cal,
            model_type=model,
            single_range=single_range,
        )
        self._start_task(task)

    # ---- Table helpers ----

    def _find_or_insert_row(self, amp_channel: str) -> int:
        """Find existing row for this range or insert a new one."""
        if amp_channel in self._row_keys:
            return self._row_keys[amp_channel]
        row = self.ranges_table.rowCount()
        self.ranges_table.insertRow(row)
        self.ranges_table.setItem(row, _COL_AMP, QTableWidgetItem(amp_channel))
        self.ranges_table.setItem(row, _COL_POINTS, QTableWidgetItem(""))
        # Persistent columns default to "--"
        for col in (_COL_MEASURED, _COL_VERIFIED, _COL_FITTED):
            self.ranges_table.setItem(
                row,
                col,
                _status_item("--", Qt.GlobalColor.darkGray),
            )
        self.ranges_table.setItem(row, _COL_STATUS, QTableWidgetItem(""))
        self._row_keys[amp_channel] = row
        return row

    def _clear_status_column(self) -> None:
        """Clear the live Status column for all rows."""
        for row in range(self.ranges_table.rowCount()):
            self.ranges_table.setItem(row, _COL_STATUS, QTableWidgetItem(""))

    # ---- Plot range selector ----

    def _on_plot_range_changed(self) -> None:
        """Handle plot range combo box selection."""
        text = self.cb_plot_range.currentText()
        if text == "Current":
            if self._active_series:
                self.plot_widget.set_series_visible(self._active_series)
            else:
                self.plot_widget.set_series_visible(None)
        elif text == "All":
            self.plot_widget.set_series_visible(None)
        else:
            # Specific completed series
            self.plot_widget.set_series_visible({text})

    # ---- Live data handling ----

    @staticmethod
    def _series_name(amp_channel: str, verify: bool = False) -> str:
        """Build a unique plot series name for a range + phase."""
        suffix = " (verify)" if verify else ""
        return f"{amp_channel}{suffix}"

    def _on_cal_chunk(self, data) -> None:
        if not isinstance(data, dict):
            return

        chunk_type = data.get("type")

        if chunk_type == "cal_point":
            amp_ch = data.get("amp_channel", "?")
            verify = data.get("verify", False)
            series = self._series_name(amp_ch, verify)
            self.plot_widget.append_point(series, data["x"], data["y"])

            # Update sticky progress label
            idx = data.get("point_index", 0)
            total = data.get("total_points", 0)
            phase = "verify" if verify else "measure"
            if total > 0:
                pct = idx * 100 // total
                self._progress_label.setText(f"Progress ({phase}): {idx}/{total} points ({pct}%)")
            else:
                self._progress_label.setText(f"Progress ({phase}): {idx} points")

            # Update Status column with point count
            if amp_ch in self._row_keys:
                pts = self._range_points.get(amp_ch, 0) + 1
                self._range_points[amp_ch] = pts
                row = self._row_keys[amp_ch]
                status_item = self.ranges_table.item(row, _COL_STATUS)
                if status_item:
                    label = "Verifying" if verify else "Measuring"
                    status_item.setText(f"{label} ({pts} pts)")

        elif chunk_type == "cal_range":
            status = data.get("status", "")
            amp_ch = data.get("amp_channel", "")
            verify = data.get("verify", False)
            series = self._series_name(amp_ch, verify)

            if status == "running":
                # Hide previous series, show only the new active one
                self._active_series = {series}
                if self.cb_plot_range.currentText() == "Current":
                    self.plot_widget.set_series_visible(self._active_series)

                row = self._find_or_insert_row(amp_ch)
                label = "Verifying" if verify else "Measuring"
                item = _status_item(label, Qt.GlobalColor.yellow)
                self.ranges_table.setItem(row, _COL_STATUS, item)
                self._range_points[amp_ch] = 0
                self.ranges_table.scrollToItem(
                    self.ranges_table.item(row, _COL_STATUS),
                )

            elif status == "done":
                # Add completed series to the dropdown
                if series not in self._completed_series:
                    self._completed_series.append(series)
                    # Insert before "All" (which is always the last item)
                    insert_idx = self.cb_plot_range.count() - 1
                    self.cb_plot_range.insertItem(insert_idx, series)

                if amp_ch in self._row_keys:
                    row = self._row_keys[amp_ch]
                    pts = data.get("points", 0)
                    duration = data.get("duration")
                    text = "Done"
                    if verify:
                        text = "Verified"
                    if pts:
                        text += f" ({pts} pts"
                        if duration is not None:
                            text += f", {duration:.1f}s"
                        text += ")"
                    elif duration is not None:
                        text += f" ({duration:.1f}s)"
                    item = _status_item(text, Qt.GlobalColor.green)
                    self.ranges_table.setItem(row, _COL_STATUS, item)

    # ---- Data management ----

    def _get_selected_ranges(self) -> list[str]:
        """Collect amp_channel strings from selected table rows."""
        selected = []
        for row in range(self.ranges_table.rowCount()):
            if self.ranges_table.selectionModel().isRowSelected(row):
                amp_item = self.ranges_table.item(row, _COL_AMP)
                if amp_item:
                    selected.append(amp_item.text())
        return selected

    def _on_delete_selected(self) -> None:
        """Delete selected ranges from raw calibration data."""
        if not self.service:
            self._log("Service not available.")
            return
        ranges = self._get_selected_ranges()
        if not ranges:
            self._log("Select rows in the table first (click to select, Ctrl+click for multiple).")
            return
        reply = QMessageBox.question(
            self,
            "Delete Calibration Data",
            f"Delete {len(ranges)} selected range(s) from raw and verify data?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._log(f"Deleting {len(ranges)} range(s)...")
        task = self.service.run_delete_calibration_ranges(ranges, target="both")
        if task:
            self._start_task(task)

    def _on_clear_raw(self) -> None:
        """Clear the entire raw_data.h5 file."""
        self._confirm_and_clear("raw")

    def _on_clear_verify(self) -> None:
        """Clear the entire raw_data_verify.h5 file."""
        self._confirm_and_clear("verify")

    def _on_clear_fitted(self) -> None:
        """Clear fitted/analysis data (aggregated, models, figures)."""
        if not self.service:
            self._log("Service not available.")
            return
        reply = QMessageBox.question(
            self,
            "Clear Fitted Data",
            "Delete all fitted data (aggregated files, model files, and analysis plots)?\n"
            "This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._log("Clearing fitted data...")
        task = self.service.run_clear_fitted_data()
        if task:
            self._start_task(task)

    def _confirm_and_clear(self, target: str) -> None:
        if not self.service:
            self._log("Service not available.")
            return
        label = "raw_data.h5" if target == "raw" else "raw_data_verify.h5"
        reply = QMessageBox.question(
            self,
            "Clear Calibration File",
            f"Delete {label}? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._log(f"Clearing {label}...")
        task = self.service.run_clear_calibration_file(target)
        if task:
            self._start_task(task)

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
        # NOTE: _loading_status is cleared in _on_task_finished (not here)
        # to prevent infinite reload loops.
        data = getattr(result, "data", None)
        if not isinstance(data, dict):
            return
        status_list = data.get("calibration_status", [])
        self._populate_ranges_table(status_list)

    def _populate_ranges_table(self, ranges: list[dict]) -> None:
        """Rebuild the table from disk-loaded calibration status."""
        self.ranges_table.setRowCount(0)
        self._row_keys.clear()
        n_measured = 0
        n_verified = 0
        n_fitted = 0
        total_points = 0

        for info in ranges:
            amp_ch = info.get("amp_channel", "")
            measured = info.get("measured", False)
            verified = info.get("verified", False)
            calibrated = info.get("calibrated", False)
            pts = info.get("points", 0)
            vpts = info.get("verify_points", 0)

            row = self._find_or_insert_row(amp_ch)

            # Point counts
            pts_parts = []
            if pts:
                pts_parts.append(str(pts))
            if vpts:
                pts_parts.append(f"v:{vpts}")
            pts_text = " / ".join(pts_parts) if pts_parts else "--"
            self.ranges_table.setItem(row, _COL_POINTS, QTableWidgetItem(pts_text))
            total_points += pts + vpts

            if measured:
                self.ranges_table.setItem(
                    row,
                    _COL_MEASURED,
                    _status_item("Yes", Qt.GlobalColor.green),
                )
                n_measured += 1
            if verified:
                self.ranges_table.setItem(
                    row,
                    _COL_VERIFIED,
                    _status_item("Yes", Qt.GlobalColor.green),
                )
                n_verified += 1
            if calibrated:
                self.ranges_table.setItem(
                    row,
                    _COL_FITTED,
                    _status_item("Yes", Qt.GlobalColor.cyan),
                )
                n_fitted += 1

        total = len(ranges)
        if total == 0:
            self._overview_summary.setText("No calibration data found")
            return

        parts = [f"{total} ranges", f"{total_points} points"]
        if n_measured:
            parts.append(f"{n_measured} measured")
        if n_verified:
            parts.append(f"{n_verified} verified")
        if n_fitted:
            parts.append(f"{n_fitted} fitted")
        self._overview_summary.setText(" | ".join(parts))

    # ---- Task finished ----

    def _on_task_finished(self, result) -> None:
        """Handle results from calibration tasks."""
        was_status_load = self._loading_status
        self._loading_status = False
        self._stop_elapsed_timer()
        self._measuring = False

        data = getattr(result, "data", None)
        if isinstance(data, dict):
            analysis_plots = data.get("analysis_plots", [])
            if analysis_plots:
                self.analysis_widget.set_images(analysis_plots)

            cancelled = data.get("cancelled", False)
            if cancelled:
                completed = data.get("completed_ranges", 0)
                total = data.get("total_ranges", 0)
                self._progress_label.setText(f"Cancelled ({completed}/{total} ranges)")
            else:
                self._progress_label.setText("Done")

        super()._on_task_finished(result)
        # Refresh calibration status after measure/fit/clear tasks — not after status load itself
        if not was_status_load:
            QTimer.singleShot(200, self._load_calibration_status)
