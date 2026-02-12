"""SU Calibration Fit class.

Ported from /measdata/dpi/samplingunit/python/dev/calibration_fit.py
All imports use proper dpi package paths — no device_scripts symlinks.
"""

import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import scipy
from dpi import DPISourceMeasureUnit
from dpi.utilities import DPIHDF5, DPILogger
from dpisourcemeasureunit.calibration import SMUCalibrationModel
from plotly.subplots import make_subplots
from scipy.interpolate import splev, splrep
from sklearn.metrics import mean_squared_error, r2_score


class SUCalibrationFit:
    """Fit, analyze and plot calibration data for a Sampling Unit.

    Handles loading raw measurement data, aggregating it, training various
    calibration models (linear, cubic, GP, spline), and generating plots.
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
        self._logger = DPILogger(level=log_level)

        self.load_raw = load_raw
        self.verify_calibration = verify_calibration

        self.calibration_folder = Path(calibration_folder)

        self.input_file: str = input_file
        self.aggregated_file: str = aggregated_file

        self.raw_data = None
        self.data = {}
        self.model = {}

        if self.verify_calibration:
            self.raw_data_verify = None
            self.data_verify = {}
            self.model_verify = {}

            self.input_file_verify: str = input_file_verify
            self.aggregated_file_verify: str = aggregated_file_verify

        self.vsmu_modes = []
        self.pa_channels = []
        self.pa_ranges = []
        self.iv_channels = []
        self.iv_ranges = []

        if self.load_raw:
            self.load_raw_data()
            if self.verify_calibration:
                self.load_raw_data_verify()
        else:
            # load aggregated data
            self.data = self.load_aggregate_data(
                self.calibration_folder / self.aggregated_file
            )
            self.model = self.prepare_model_dict(self.model)

            if self.verify_calibration:
                self.data_verify = self.load_aggregate_data(
                    self.calibration_folder / self.aggregated_file_verify
                )
                self.model_verify = self.prepare_model_dict(self.model_verify)

        if single_range is not None:
            self.data = {single_range: self.data[single_range]}
            self.model = {single_range: self.model[single_range]}
            self.single_range = True
        else:
            self.single_range = False

        # Assume at least one key exists
        first_group = next(iter(self.data.values()))
        self.frame_size = len(first_group)
        self.total_frames = len(self.data)

        # Populate unique attributes from the data
        for key in self.data.keys():
            (vsmu_mode, pa_channel, iv_channel) = key
            if vsmu_mode not in self.vsmu_modes:
                self.vsmu_modes.append(vsmu_mode)
            if pa_channel not in self.pa_channels:
                self.pa_channels.append(pa_channel)
                self.pa_ranges.append(self.data[key].attrs["pa_range"])
            if iv_channel not in self.iv_channels:
                self.iv_channels.append(iv_channel)
                self.iv_ranges.append(self.data[key].attrs["iv_range"])

        # Print summary of the calibration
        self._logger.verbose(f"Total frames: {self.total_frames}")
        self._logger.verbose(f"VSMU Modes: {[bool(x) for x in self.vsmu_modes]}")
        pa_pairs = tuple(
            (ch, int(rng)) for ch, rng in zip(self.pa_channels, self.pa_ranges)
        )
        self._logger.verbose(f"PA Channels: {pa_pairs}")
        iv_pairs = tuple(
            (ch, int(rng)) for ch, rng in zip(self.iv_channels, self.iv_ranges)
        )
        self._logger.verbose(f"IV Channels: {iv_pairs}")
        self._logger.debug(f"Frame size: {self.frame_size}")

    def load_raw_data(self):
        """Load and aggregate raw measurement data."""
        self.raw_data = DPIHDF5.load(self.calibration_folder / self.input_file)

        # aggregate measurement data
        self.data = self.aggregate_measurement(self.raw_data)
        self.model = self.prepare_model_dict(self.model)

        # save aggregated data
        DPIHDF5.save(
            list(self.data.values()), self.calibration_folder / self.aggregated_file
        )

    def load_raw_data_verify(self):
        """Load and aggregate verification measurement data."""
        self.raw_data_verify = DPIHDF5.load(
            self.calibration_folder / self.input_file_verify
        )

        # aggregate measurement data
        self.data_verify = self.aggregate_measurement(self.raw_data_verify)
        self.model_verify = self.prepare_model_dict(self.model_verify)

        # save aggregated data
        DPIHDF5.save(
            list(self.data_verify.values()),
            self.calibration_folder / self.aggregated_file_verify,
        )

    def load_aggregate_data(self, file_path):
        """Load previously aggregated data from HDF5."""
        data = {}
        dataframes = DPIHDF5.load(file_path)

        for df in dataframes:
            key = (
                df.attrs["vsmu_mode"],
                df.attrs["pa_channel"],
                df.attrs["iv_channel"],
            )
            data[key] = df

        return data

    def aggregate_measurement(self, raw_data):
        """Aggregate raw measurement data into per-channel DataFrames."""
        data = {}
        attrs = {}

        cols = ["i_set", "i_ref", "i_meas", "std", "max", "min", "error"]

        for df in raw_data:
            df_attrs = df.attrs

            key = (
                df_attrs["vsmu_mode"],
                df_attrs["pa_channel"],
                df_attrs["iv_channel"],
            )
            df_attrs["name"] = (
                f"vsmu={df_attrs['vsmu_mode']} pach={df_attrs['pa_channel']} "
                f"ivch={df_attrs['iv_channel']} pa={df_attrs['pa_range']} "
                f"iv={df_attrs['iv_range']}"
            )
            measurement = [
                df.attrs["i_set"],
                df.attrs["i_ref"],
                df["current"].mean(),
                df["current"].std(),
                df["current"].max(),
                df["current"].min(),
                df.attrs["i_ref"] - df["current"].mean(),
            ]

            if key not in data:
                data[key] = []
                attrs[key] = df_attrs

            data[key].append(measurement)

        for key in data:
            df = pd.DataFrame(data[key], columns=cols)
            df.attrs.update(attrs[key])
            df.sort_values("i_set", inplace=True)
            data[key] = df.reset_index(drop=True)

        # sort by key
        data = dict(sorted(data.items()))

        return data

    def prepare_model_dict(self, model):
        """Initialize empty model dict for each data key."""
        for key in self.data.keys():
            model[key] = {}
        return model

    def plot_measurement_overview(self):
        """Generate interactive HTML overview of raw measurements."""
        if self.raw_data is None:
            self.load_raw_data()

        data = self.raw_data

        fig = make_subplots(
            rows=2, cols=1, subplot_titles=["Time Series", "Fourier Transform"]
        )

        trace_list = []

        for df in data:
            n = len(df.current)
            dt = np.mean(np.diff(df.time))

            freq, psd = scipy.signal.welch(df.current, fs=1 / dt, nperseg=min(256, n))

            name = (
                f"VSMU {df.attrs['vsmu_mode']}, pa {df.attrs['pa_channel']}, "
                f"iv {df.attrs['iv_channel']}, Iset {df.attrs['i_set']:.2e}, "
                f"Iref {df.attrs['i_ref']:.2e}"
            )
            name_fft = name + " FFT"

            trace_list.append(
                (
                    name,
                    go.Scatter(
                        x=df.time,
                        y=df.current,
                        mode="lines",
                        name=name,
                        visible="legendonly",
                    ),
                    1,
                    1,
                )
            )
            trace_list.append(
                (
                    name_fft,
                    go.Scatter(
                        x=freq,
                        y=psd,
                        mode="lines",
                        name=name_fft,
                        visible="legendonly",
                    ),
                    2,
                    1,
                )
            )

        # Sort traces by name
        trace_list.sort(key=lambda x: x[0])

        # Add traces in sorted order
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
        """Generate matplotlib overview of aggregated data."""
        amplifiers = sorted(set(key[1] for key in self.data.keys()))
        currents = sorted(set(key[2] for key in self.data.keys()), reverse=True)

        n_cols = len(amplifiers)
        fig, axes = plt.subplots(1, n_cols, figsize=(4 * n_cols, 5), sharex="col")

        if n_cols == 1:
            axes = np.array([axes])

        legend_handles = []
        legend_labels = []
        iv_legend = set()

        vsmu_mode = False
        for col, pa in enumerate(amplifiers):
            if col == 0:
                axes[col].plot((-1e-2, 1e-2), (1e-2, -1e-2), "--", color="k")
            else:
                axes[col].plot((-1e-2, 1e-2), (-1e-2, 1e-2), "--", color="k")

            axes[col].grid(True, color="grey", alpha=0.5)

            for iv in currents:
                key = (vsmu_mode, pa, iv)

                iv_label = self.data[key].attrs["iv_range"]

                (line,) = axes[col].plot(
                    self.data[key].i_ref,
                    self.data[key].i_meas,
                    marker="x",
                    label=f"IV {iv_label}",
                )
                if iv_label not in iv_legend:
                    legend_handles.append(line)
                    legend_labels.append(f"IV {iv_label}")
                    iv_legend.add(iv_label)

            axes[col].set_title(f"Amplifier {pa}")
            axes[col].set_xscale("symlog", linthresh=1e-13)
            axes[col].set_yscale("symlog", linthresh=1e-13)
            axes[col].set_xlabel("Reference Current (symlog)")

            try:
                axes[col].set_box_aspect(1)
            except AttributeError:
                axes[col].set_aspect("equal", adjustable="box")

            if col == 0:
                axes[col].set_ylabel("Measured Current (symlog)")
            else:
                axes[col].set_ylabel("")
                axes[col].set_yticklabels([])

            for label in axes[col].get_xticklabels():
                label.set_rotation(90)

        fig.legend(
            legend_handles,
            legend_labels,
            loc="center left",
            bbox_to_anchor=(0.90, 0.56),
            borderaxespad=0.0,
        )
        plt.tight_layout(rect=[0, 0, 0.9, 1])

        save_path = self.calibration_folder / "figures"
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        plt.savefig(save_path / "overview_agg.png", dpi=300)

    def plot_calibrated_overview(self):
        """Generate matplotlib calibrated overview with GP predictions."""
        amplifiers = sorted(set(key[1] for key in self.data.keys()))
        n_cols = len(amplifiers)
        n_rows = 2

        fig, axes = plt.subplots(
            n_rows, n_cols, figsize=(4 * n_cols, 5 * n_rows), sharex="col"
        )

        if n_cols == 1:
            axes = axes.reshape(n_rows, 1)

        legend_handles = []
        legend_labels = []
        iv_legend = set()

        vsmu_mode = False
        for col, pa in enumerate(self.pa_channels):
            # --- FIRST ROW ---
            ax = axes[0, col]
            if col == 0:
                ax.plot((-1e-2, 1e-2), (1e-2, -1e-2), "--", color="k")
            else:
                ax.plot((-1e-2, 1e-2), (-1e-2, 1e-2), "--", color="k")

            ax.grid(True, color="grey", alpha=0.5)

            for iv in self.iv_channels:
                key = (vsmu_mode, pa, iv)
                (line,) = ax.plot(
                    self.data[key].i_ref,
                    self.data[key].i_meas,
                    marker="x",
                    label=f"IV {iv}",
                )
                if iv not in iv_legend:
                    legend_handles.append(line)
                    legend_labels.append(f"IV {iv}")
                    iv_legend.add(iv)

            ax.set_title(f"Amplifier {pa}")
            ax.set_xscale("symlog", linthresh=1e-13)
            ax.set_yscale("symlog", linthresh=1e-13)
            ax.set_xlabel("Reference Current (symlog)")

            try:
                ax.set_box_aspect(1)
            except AttributeError:
                ax.set_aspect("equal", adjustable="box")

            if col == 0:
                ax.set_ylabel("Measured Current (symlog)")
            else:
                ax.set_ylabel("")
                ax.set_yticklabels([])

            for label in ax.get_xticklabels():
                label.set_rotation(90)

            # --- SECOND ROW ---
            ax2 = axes[1, col]
            ax2.plot((-1e-2, 1e-2), (-1e-2, 1e-2), "--", color="k")
            ax2.grid(True, color="grey", alpha=0.5)

            for iv in self.iv_channels:
                key = (vsmu_mode, pa, iv)

                model = self.model[key]["gp"]
                y_gp = model.predict(self.data[key].i_meas)

                ax2.plot(self.data[key].i_ref, y_gp, marker="x", label=f"IV {iv}")

            ax2.set_title(f"Amplifier {pa} Calibrated")
            ax2.set_xscale("symlog", linthresh=1e-13)
            ax2.set_yscale("symlog", linthresh=1e-13)
            ax2.set_xlabel("Reference Current (symlog)")

            try:
                ax2.set_box_aspect(1)
            except AttributeError:
                ax2.set_aspect("equal", adjustable="box")

            if col == 0:
                ax2.set_ylabel("Measured Current (symlog)")
            else:
                ax2.set_ylabel("")
                ax2.set_yticklabels([])

            for label in ax2.get_xticklabels():
                label.set_rotation(90)

        fig.legend(
            legend_handles,
            legend_labels,
            loc="center left",
            bbox_to_anchor=(0.90, 0.56),
            borderaxespad=0.0,
        )
        plt.tight_layout(rect=[0, 0, 0.9, 1])

        save_path = self.calibration_folder / "figures"
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        plt.savefig(save_path / "overview_cal.png", dpi=300)

    def train_linear_model(self):
        """Train linear (k*x + d) calibration model for each data key."""
        for key, data in self.data.items():
            k, d = np.polyfit(data.i_meas, data.i_ref, 1)
            self.model[key]["linear"] = {"k": k, "d": d}

    def train_cubic_model(self):
        """Train cubic polynomial calibration model for each data key."""
        for key, data in self.data.items():
            coeffs = np.polyfit(data.i_meas, data.i_ref, deg=3)
            a, b, c, d = coeffs
            self.model[key]["cubic"] = {"a": a, "b": b, "c": c, "d": d}

    def train_gp_model(self):
        """Train Gaussian Process calibration model for each data key."""
        for key, data in self.data.items():
            x = data.i_meas
            y = data.i_ref

            gp = SMUCalibrationModel(
                key,
                data.attrs["pa_range"],
                data.attrs["iv_range"],
                log_level=DPILogger.NOTICE,
            )

            gp.fit(x, y)
            self.model[key]["gp"] = gp

    def train_spline_model(self):
        """Train spline calibration model for each data key."""
        for key, data in self.data.items():
            x = data.i_meas.values.copy()
            y = data.i_ref.values.copy()

            while True:
                out_of_order = np.where(np.diff(x) < 0)[0]
                if len(out_of_order) == 0:
                    break
                i = out_of_order[0]
                x = np.delete(x, i)
                y = np.delete(y, i)

            try:
                spline = splrep(x, y, s=0, k=1)
                self.model[key]["spline"] = spline
            except Exception as e:
                (vsmu, pa, iv) = key
                self._logger.warning(
                    f"Failed to fit spline for VSMU Mode: {vsmu}, "
                    f"Amplifier Channel: {pa}, Current Channel: {iv}: {e}."
                )

    def analyze_add_type(self, analyze_lists, type, i_ref, i_meas, verbose=False):
        """Compute error metrics and add to analyze_lists."""
        # Error
        error = i_ref - i_meas
        error_mean = error.abs().mean()
        error_std = error.abs().std()

        # Error percent
        error_p = error / i_ref
        mse = mean_squared_error(i_ref, i_meas)
        r2 = r2_score(i_ref, i_meas)

        # Gradient
        grad = np.gradient(i_ref, i_meas)
        grad_normalized = grad / np.max(np.abs(grad))

        # Message
        message = (
            f"{type} Values: Error Mean: {error_mean:.5e}, Error Std: {error_std:.5e}, "
            f"Error Mean %: {error_p.mean():.2f}, MSE: {mse:.5e}, R2: {r2:.10e}"
        )

        # Add to list
        analyze_lists["type"].append(type)
        analyze_lists["i_ref"].append(i_ref)
        analyze_lists["i_meas"].append(i_meas)
        analyze_lists["error"].append(error)
        analyze_lists["error_mean"].append(error_mean)
        analyze_lists["error_std"].append(error_std)
        analyze_lists["error_p"].append(error_p)
        analyze_lists["mean_squared_error"].append(mse)
        analyze_lists["r2_score"].append(r2)
        analyze_lists["gradient"].append(grad)
        analyze_lists["message"].append(message)

        if verbose:
            self._logger.debug(
                f"{type} Values: {'I Ref'} - {'I Measure'} - {'Error'} - {'Error %'}"
            )
            for i_r, i_m, err, err_p in zip(i_ref, i_meas, error, error_p):
                self._logger.debug(
                    f"{type} Values: {i_r:.5e} {i_m:.5e} {err:.5e} {err_p:.2f} %"
                )

        self._logger.debug(
            f"{type} Values: Error Mean: {error_mean:.5e}, Error Std: {error_std:.5e}, "
            f"MSE: {mse:.5e}, R2: {r2:.10e}"
        )

    def analyze_range(self, vsmu, pa, iv, save_plot=True, show=False):
        """Analyze a single range with multiple model types and generate plots."""
        error_log = ""
        msg_offset = 1

        analyze_lists = {
            "type": [],
            "i_ref": [],
            "i_meas": [],
            "error": [],
            "error_mean": [],
            "error_std": [],
            "error_p": [],
            "mean_squared_error": [],
            "r2_score": [],
            "gradient": [],
            "message": [],
        }

        self._logger.debug(
            f"VSMU Mode: {vsmu}, Amplifier Channel: {pa}, Current Channel: {iv}."
        )

        key = (vsmu, pa, iv)
        if key not in self.data or self.data[key].empty:
            self._logger.warning(
                f"No data for VSMU Mode: {vsmu}, Amplifier Channel: {pa}, "
                f"Current Channel: {iv}."
            )
            return

        df = self.data[key]

        if self.verify_calibration:
            df_verify = self.data_verify[key]

        # Values
        i_ref = df.i_ref
        i_meas = df.i_meas

        self.analyze_add_type(analyze_lists, "Measured", i_ref, i_meas, verbose=False)

        if (
            analyze_lists["r2_score"][0] > -2.8 or analyze_lists["r2_score"][0] < -3.2
        ) and (
            analyze_lists["r2_score"][0] > 1.0 or analyze_lists["r2_score"][0] < 0.9
        ):
            message = (
                f"VSMU Mode: {vsmu}, Amplifier Channel: {pa}, Current Channel: {iv}, "
                f"R2 Score {analyze_lists['r2_score'][0]:.5e} out of line, "
                f"check the measurement for analog errors."
            )
            self._logger.warning(message)
            error_log = f"WARNING - {message}"

        if key in self.data and "linear" in self.model[key]:
            k = self.model[key]["linear"]["k"]
            d = self.model[key]["linear"]["d"]
            linear_fit = k * df.i_meas + d
            self.analyze_add_type(
                analyze_lists, "Linear", df.i_ref, linear_fit, verbose=False
            )

        if key in self.data and "cubic" in self.model[key]:
            cubic = self.model[key]["cubic"]
            cubic_fit = (
                cubic["a"] * df.i_meas**3
                + cubic["b"] * df.i_meas**2
                + cubic["c"] * df.i_meas
                + cubic["d"]
            )
            self.analyze_add_type(
                analyze_lists, "Cubic", df.i_ref, cubic_fit, verbose=False
            )

        if key in self.data and "gp" in self.model[key]:
            model = self.model[key]["gp"]
            gp_fit, gp_std = model.predict(df.i_meas, return_std=True)
            self.analyze_add_type(
                analyze_lists, "GP", df.i_ref, gp_fit, verbose=False
            )

            if self.verify_calibration:
                gp_fit_verify, gp_std_verify = model.predict(
                    df_verify.i_meas, return_std=True
                )
                self.analyze_add_type(
                    analyze_lists,
                    "GP Verify",
                    df_verify.i_ref,
                    gp_fit_verify,
                    verbose=False,
                )

        if key in self.data and "spline" in self.model[key]:
            spline = self.model[key]["spline"]
            spline_fit = splev(df.i_meas, spline)
            self.analyze_add_type(
                analyze_lists, "Spline", df.i_ref, spline_fit, verbose=False
            )

        if save_plot or show:
            nrows = len(analyze_lists["type"])
            fig, axes = plt.subplots(nrows, 5, figsize=(5 * 5, 5 * nrows))

            messages = error_log

            for i, (type, i_ref, i_meas, error, error_p, grad, message) in enumerate(
                zip(
                    analyze_lists["type"],
                    analyze_lists["i_ref"],
                    analyze_lists["i_meas"],
                    analyze_lists["error"],
                    analyze_lists["error_p"],
                    analyze_lists["gradient"],
                    analyze_lists["message"],
                )
            ):
                if i == 0:
                    i_ref_sign = -1 if pa == "pach0" else 1
                else:
                    i_ref_sign = 1

                # 1. Linear scale plot
                axes[i, 0].plot(i_ref, i_ref * i_ref_sign, "--", color="k")
                axes[i, 0].plot(i_ref, i_meas, marker="x", label="Measured")
                axes[i, 0].set_xlabel("Reference Current")
                axes[i, 0].set_ylabel("Measured Current")
                axes[i, 0].set_title(f"{type} Linear scale")
                axes[i, 0].legend()
                axes[i, 0].grid(True)

                # 2. Symlog scale plot
                axes[i, 1].plot(i_ref, i_ref * i_ref_sign, "--", color="k")
                axes[i, 1].plot(i_ref, i_meas, marker="x", label="Measured")
                axes[i, 1].set_xscale("symlog", linthresh=1e-13)
                axes[i, 1].set_yscale("symlog", linthresh=1e-13)
                axes[i, 1].set_xlabel("Reference Current (symlog)")
                axes[i, 1].set_ylabel("Measured Current (symlog)")
                axes[i, 1].set_title(f"{type} Symlog scale")
                axes[i, 1].legend()
                axes[i, 1].grid(True)

                # 3. Error plot
                axes[i, 2].plot(i_ref, np.zeros(len(i_ref)), "--", color="k")
                axes[i, 2].plot(i_ref, error, marker="x", label="Measured")
                axes[i, 2].set_xscale("symlog", linthresh=1e-13)
                axes[i, 2].set_ylabel("Error (ref - meas)")
                axes[i, 2].set_title(f"{type} Error Current")
                axes[i, 2].legend()
                axes[i, 2].grid(True)

                # 4. Error % plot
                axes[i, 3].plot(i_ref, np.zeros(len(i_ref)), "--", color="k")
                axes[i, 3].plot(i_ref, error_p, marker="x", label="Measured")
                axes[i, 3].set_xscale("symlog", linthresh=1e-13)
                axes[i, 3].set_xlabel("Reference Current")
                axes[i, 3].set_ylabel("Error % (ref - meas)")
                axes[i, 3].set_title(f"{type} Error % Current")
                axes[i, 3].legend()
                axes[i, 3].grid(True)

                # 5. Gradient
                axes[i, 4].plot(i_ref, grad, marker="x", label="Measured")
                axes[i, 4].set_xscale("symlog", linthresh=1e-13)
                axes[i, 4].set_xlabel("Reference Current")
                axes[i, 4].set_ylabel("Gradient")
                axes[i, 4].set_title(f"{type} Gradient")
                axes[i, 4].legend()
                axes[i, 4].grid(True)

                if messages == "":
                    messages = message
                    msg_offset = 0
                else:
                    messages += "\n" + message

            for row in axes:
                for axis in row:
                    for label in axis.get_xticklabels():
                        label.set_rotation(90)

            plt.suptitle(
                f"VSMU Mode: {vsmu}, Amplifier Channel: {pa}, "
                f"Amplifier Range: {self.data[key].attrs['pa_range']}, "
                f"Current Channel: {iv}, "
                f"Current Range: {self.data[key].attrs['iv_range']}"
            )

            if "ERROR" in messages:
                msg_color = "red"
            elif "WARNING" in messages:
                msg_color = "#A2A914"
            else:
                msg_color = "black"

            fig.text(
                0.5, 0.01, messages, ha="center", fontsize="large", color=msg_color
            )
            line = len(analyze_lists["message"]) + msg_offset

            plt.tight_layout(rect=[0, 0.01 * line + 0.02, 1, 0.95])

            if save_plot:
                save_path = self.calibration_folder / "figures/ranges"
                if not os.path.exists(save_path):
                    os.makedirs(save_path)

                plt.savefig(
                    save_path / f"vsmu_{vsmu}_pa_{pa}_iv_{iv}_analyze.png", dpi=300
                )
            if show:
                plt.show()
            plt.close(fig)

    def analyze_ranges(self):
        """Analyze all ranges for all channels and VSMU modes."""
        for vsmu in self.vsmu_modes:
            for pa in self.pa_channels:
                for iv in self.iv_channels:
                    self.analyze_range(vsmu, pa, iv, save_plot=True, show=False)
