"""SU Calibration Fit class.

Inherits from CalibrationFitBase (dpi package) for standardized model training,
saving, and analysis. Uses correct SU data format: voltage-based columns with
amp_channel keys.
"""

import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import scipy
from dpi.calibration import CalibrationFitBase
from dpi.utilities import DPILogger
from plotly.subplots import make_subplots

from src.logic.calibration.su_calibration_gp_model import SUCalibrationGPModel
from src.logic.calibration.su_calibration_linear_model import SUCalibrationLinearModel


class SUCalibrationFit(CalibrationFitBase):
    """Fit, analyze and plot calibration data for a Sampling Unit.

    Handles loading raw measurement data, aggregating it, training various
    calibration models (linear, GP), and generating plots.
    """

    def __init__(
        self,
        calibration_folder: str,
        single_range=None,
        load_raw=True,
        verify_calibration=False,
        input_file: str = "raw_data.h5",
        input_file_verify: str = "raw_data_verify.h5",
        aggregated_file: str = "aggregated.h5",
        aggregated_file_verify: str = "aggregated_verify.h5",
        log_level=DPILogger.NOTICE,
    ):
        super().__init__(
            calibration_folder,
            single_range,
            load_raw,
            verify_calibration,
            input_file,
            input_file_verify,
            aggregated_file,
            aggregated_file_verify,
            log_level,
        )

    # -- CalibrationFitBase abstract method implementations --

    def _print_summary(self):
        super()._print_summary()
        self._logger.verbose(f"AMP Channels: {self.amp_channels}")

    def _init_channel_attributes(self):
        self.amp_channels = []

    def _populate_channel_attributes(self):
        self.amp_channels = self.data.keys()

    def _extract_key_from_dataframe(self, df):
        return df.attrs["amp_channel"]

    def _create_calibration_gp_model(self, key, data):
        return SUCalibrationGPModel(
            key, data.attrs["amp_range"],
            min_score=1e-11, grad_thresh=50e-6,
            log_level=DPILogger.NOTICE,
        )

    def _create_calibration_linear_model(self, key, data):
        return SUCalibrationLinearModel(
            key, data.attrs["amp_range"],
            log_level=DPILogger.NOTICE,
        )

    def _get_key_description(self, key):
        return f"AMP Channel: {key}"

    def _get_lin_thresh(self, key):
        return 10.0 ** self.data[key].attrs["amp_range"] * 1e-6

    def _get_suptitle(self, key):
        return f"AMP Channel: {key}, Range: {self.data[key].attrs['amp_range']}"

    def _get_file_name(self, key):
        return f"amp_{key}"

    def _get_unit_type(self):
        return "su"

    def _get_measured_unit(self):
        return "Voltage"

    # -- Aggregation --

    def aggregate_measurement(self, raw_data):
        data = {}
        attrs = {}

        cols = ["set", "ref", "meas", "std", "max", "min", "error"]

        for df in raw_data:
            df_attrs = df.attrs

            key = df_attrs["amp_channel"]
            df_attrs["name"] = (
                f"ampch={df_attrs['amp_channel']}, amp={df_attrs['amp_range']}"
            )
            measurement = [
                df.attrs["v_set"],
                df.attrs["v_ref"],
                df["voltage"].mean(),
                df["voltage"].std(),
                df["voltage"].max(),
                df["voltage"].min(),
                df.attrs["v_ref"] - df["voltage"].mean(),
            ]

            if key not in data:
                data[key] = []
                attrs[key] = df_attrs

            data[key].append(measurement)

        for key in data:
            df = pd.DataFrame(data[key], columns=cols)
            df.attrs.update(attrs[key])
            df.sort_values("set", inplace=True)
            data[key] = df.reset_index(drop=True)

        data = dict(sorted(data.items()))

        return data

    # -- Plotting --

    def plot_measurement_overview(self):
        if self.raw_data is None:
            self.load_raw_data()

        data = self.raw_data

        fig = make_subplots(
            rows=2, cols=1, subplot_titles=["Time Series", "Fourier Transform"]
        )

        trace_list = []

        for df in data:
            n = len(df.voltage)
            voltage = df.voltage.to_numpy()
            dt = np.mean(np.diff(df.time))

            freq, psd = scipy.signal.welch(voltage, fs=1 / dt, nperseg=min(256, n))

            name = (
                f"AMP {df.attrs['amp_channel']}, "
                f"Vset {df.attrs['v_set']:.2e}, Vref {df.attrs['v_ref']:.2e}"
            )
            name_fft = name + " FFT"

            trace_list.append((
                name,
                go.Scatter(x=df.time, y=df.voltage, mode="lines", name=name, visible="legendonly"),
                1, 1,
            ))
            trace_list.append((
                name_fft,
                go.Scatter(x=freq, y=psd, mode="lines", name=name_fft, visible="legendonly"),
                2, 1,
            ))

        trace_list.sort(key=lambda x: x[0])

        for _, trace, row, col in trace_list:
            fig.add_trace(trace, row=row, col=col)

        fig.update_layout(
            height=1200,
            width=1600,
            title_text="All Measurements",
            showlegend=True,
        )

        save_path = self.calibration_folder / "figures"
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        fig.write_html(save_path / "overview_measure.html")

    def plot_aggregated_overview(self):
        amplifiers = sorted(self.data.keys())
        n_cols = 1

        fig, axes = plt.subplots(1, n_cols, figsize=(4 * n_cols, 5), sharex="col")

        if n_cols == 1:
            axes = np.array([axes])

        legend_handles = []
        legend_labels = []
        amp_legend = set()

        col = 0
        axes[col].plot((-1e-2, 1e-2), (-1e-2, 1e-2), "--", color="k")
        axes[col].grid(True, color="grey", alpha=0.5)

        for amp in amplifiers:
            key = amp
            amp_label = self.data[key].attrs["amp_range"]

            (line,) = axes[col].plot(
                self.data[key].ref, self.data[key].meas,
                marker="x", label=f"AMP {amp_label:.2f}",
            )
            if amp_label not in amp_legend:
                legend_handles.append(line)
                legend_labels.append(f"AMP {amp_label:.2f}")
                amp_legend.add(amp_label)

        axes[col].set_title("Amplifier")
        axes[col].set_xscale("symlog", linthresh=1e-13)
        axes[col].set_yscale("symlog", linthresh=1e-13)
        axes[col].set_xlabel("Reference Voltage (symlog)")

        try:
            axes[col].set_box_aspect(1)
        except AttributeError:
            axes[col].set_aspect("equal", adjustable="box")

        axes[col].set_ylabel("Measured Voltage (symlog)")

        for label in axes[col].get_xticklabels():
            label.set_rotation(90)

        axes[col].legend(legend_handles, legend_labels, loc="lower right", frameon=True)
        plt.tight_layout()

        save_path = self.calibration_folder / "figures"
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        plt.savefig(save_path / "overview_agg.png", dpi=300)
        plt.close(fig)

    def plot_calibrated_overview(self, model_type="linear"):
        amplifiers = sorted(self.data.keys())
        n_cols = 1
        n_rows = 2

        fig, axes = plt.subplots(
            n_rows, n_cols, figsize=(4 * n_cols, 5 * n_rows), sharex="col"
        )

        if n_cols == 1:
            axes = axes.reshape(n_rows, 1)

        legend_handles = []
        legend_labels = []
        amp_legend = set()

        col = 0

        # --- Row 1: Uncalibrated ---
        ax = axes[0, col]
        ax.plot((-1e-2, 1e-2), (-1e-2, 1e-2), "--", color="k")
        ax.grid(True, color="grey", alpha=0.5)

        for amp in amplifiers:
            key = amp
            amp_label = self.data[key].attrs["amp_range"]

            (line,) = ax.plot(
                self.data[key].ref, self.data[key].meas,
                marker="x", label=f"AMP {amp_label:.2f}",
            )
            if amp_label not in amp_legend:
                legend_handles.append(line)
                legend_labels.append(f"AMP {amp_label:.2f}")
                amp_legend.add(amp_label)

        ax.set_title("Amplifier Uncalibrated")
        ax.set_xscale("symlog", linthresh=1e-13)
        ax.set_yscale("symlog", linthresh=1e-13)
        ax.set_xlabel("Reference Voltage (symlog)")

        try:
            ax.set_box_aspect(1)
        except AttributeError:
            ax.set_aspect("equal", adjustable="box")

        ax.set_ylabel("Measured Voltage (symlog)")

        for label in ax.get_xticklabels():
            label.set_rotation(90)

        # --- Row 2: Calibrated ---
        ax2 = axes[1, col]
        ax2.plot((-1e-2, 1e-2), (-1e-2, 1e-2), "--", color="k")
        ax2.grid(True, color="grey", alpha=0.5)

        for amp in amplifiers:
            key = amp
            model = self.model[key][model_type]
            y_cal = model.predict(self.data[key].meas)
            ax2.plot(self.data[key].ref, y_cal, marker="x", label=f"AMP {amp}")

        ax2.set_title("Amplifier Calibrated")
        ax2.set_xscale("symlog", linthresh=1e-13)
        ax2.set_yscale("symlog", linthresh=1e-13)
        ax2.set_xlabel("Reference Voltage (symlog)")

        try:
            ax2.set_box_aspect(1)
        except AttributeError:
            ax2.set_aspect("equal", adjustable="box")

        ax2.set_ylabel("Measured Voltage (symlog)")

        for label in ax2.get_xticklabels():
            label.set_rotation(90)

        ax.legend(legend_handles, legend_labels, loc="lower right", frameon=True)
        plt.tight_layout()

        save_path = self.calibration_folder / "figures"
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        plt.savefig(save_path / "overview_cal.png", dpi=300)
        plt.close(fig)

    def analyze_ranges(self, save_plot=True, show=False):
        for amp_ch in self.amp_channels:
            self.analyze_range(amp_ch, save_plot=save_plot, show=show)
