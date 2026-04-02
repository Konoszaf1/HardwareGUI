"""Sampling Unit controller for hardware operations.

This controller encapsulates all SU hardware workflows including setup, test,
and calibration operations. It uses direct imports from the dpi package.
"""

import contextlib
import re
import shutil
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from src.logging_config import get_logger
from src.logic.controllers.base_controller import (
    ChannelConfig,
    HardwareController,
    OperationResult,
)

if TYPE_CHECKING:
    from dpi import DPIMainControlUnit, DPISamplingUnit

logger = get_logger(__name__)


class _SUProgressAdapter:
    """Mimics tqdm interface to redirect measurement progress to callbacks."""

    def __init__(self, total, scm, on_point, on_range, verify=False):
        self.total = total
        self.n = 0
        self._scm = scm
        self._on_point = on_point
        self._on_range = on_range
        self._verify = verify
        self._current_desc = ""
        self._range_points = 0
        self._range_start = 0.0

    def update(self, n=1):
        self.n += n
        self._range_points += n
        if self._on_point and self._scm.data:
            df = self._scm.data[-1]
            self._on_point(
                {
                    "type": "cal_point",
                    "amp_channel": df.attrs.get("amp_channel"),
                    "verify": self._verify,
                    "x": float(df.attrs.get("v_ref", 0)),
                    "y": float(df["voltage"].mean()),
                    "v_set": float(df.attrs.get("v_set", 0)),
                    "point_index": self.n,
                    "total_points": self.total,
                }
            )

    @staticmethod
    def _parse_desc(desc: str) -> dict:
        """Extract amp_channel from a range description string."""
        m = re.match(r"AMP:\s*(\w+)", desc)
        if m:
            return {"amp_channel": m.group(1)}
        return {}

    def set_description(self, desc):
        if desc != self._current_desc:
            # Mark previous range as done
            if self._current_desc and self._on_range:
                elapsed = time.time() - self._range_start
                done_data = {
                    "type": "cal_range",
                    "status": "done",
                    "desc": self._current_desc,
                    "verify": self._verify,
                    "points": self._range_points,
                    "duration": elapsed,
                }
                done_data.update(self._parse_desc(self._current_desc))
                self._on_range(done_data)
            self._current_desc = desc
            self._range_points = 0
            self._range_start = time.time()
            if self._on_range:
                running_data = {
                    "type": "cal_range",
                    "status": "running",
                    "verify": self._verify,
                }
                running_data.update(self._parse_desc(desc))
                if "amp_channel" in running_data:
                    self._on_range(running_data)

    def close(self):
        if self._current_desc and self._on_range:
            elapsed = time.time() - self._range_start
            done_data = {
                "type": "cal_range",
                "status": "done",
                "desc": self._current_desc,
                "verify": self._verify,
                "points": self._range_points,
                "duration": elapsed,
            }
            done_data.update(self._parse_desc(self._current_desc))
            self._on_range(done_data)


class SUController(HardwareController):
    """Controller for Sampling Unit hardware operations.

    Manages setup, test, and calibration workflows for SU devices.
    Optionally integrates with MCU (Maincontrol Unit) for synchronized operations.

    Attributes:
        _su: DPISamplingUnit instance (injected or auto-created).
        _mcu: Optional DPIMainControlUnit for synchronized timing.
    """

    def __init__(
        self,
        su: "DPISamplingUnit | None" = None,
        mcu: "DPIMainControlUnit | None" = None,
    ) -> None:
        """Initialize SUController.

        Args:
            su: Optional pre-connected DPISamplingUnit instance.
            mcu: Optional pre-connected DPIMainControlUnit instance.
        """
        self._su = su
        self._mcu = mcu

    # =========================================================================
    # Setup Operations (hw_setup)
    # =========================================================================

    def initialize_device(
        self,
        serial: int,
        processor_type: str = "746",
        connector_type: str = "BNC",
    ) -> OperationResult:
        """Initialize a new SU device after first flash.

        Writes device identity to EEPROM.

        Args:
            serial: Device serial number (1-9999).
            processor_type: Processor type ("746").
            connector_type: Connector type ("BNC" or "SMA").

        Returns:
            OperationResult with success status and serial number.
        """
        try:
            su = self._get_su()
            su.initNewDevice(
                serial=serial,
                processorType=processor_type,
                connectorType=connector_type,
            )
            logger.info("SU initialized: serial=%s", serial)
            return OperationResult(ok=True, serial=serial)
        except Exception as e:
            logger.error("SU initialization failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def configure_channel(self, config: ChannelConfig) -> OperationResult:
        """Configure an amplifier channel.

        Note: Channel configuration is runtime-only (lost on disconnect).

        Args:
            config: Channel configuration parameters.

        Returns:
            OperationResult with success status.
        """
        try:
            self._get_su()
            logger.info("SU channel configured: %s", config.channel_id)
            return OperationResult(ok=True, data={"channel_id": config.channel_id})
        except Exception as e:
            logger.error("SU channel configuration failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def save_channel_config(self) -> OperationResult:
        """Save current channel configuration to EEPROM.

        Note: Channel calibration is managed by the calibration workflow.

        Returns:
            OperationResult with informational message.
        """
        try:
            self._get_su()
            print("Note: Channel calibration is managed by the calibration workflow.")
            print("Use 'Run Calibration' on the Calibration page to write to EEPROM.")
            return OperationResult(ok=True, message="Use calibration workflow for EEPROM writes.")
        except Exception as e:
            logger.error("SU EEPROM save failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def load_channel_config(self) -> OperationResult:
        """Load channel configuration from EEPROM.

        Returns:
            OperationResult with channel data.
        """
        try:
            su = self._get_su()
            print("Reading SU EEPROM content...")
            try:
                su.printEpromContent()
            except AttributeError:
                print("EEPROM content display not available for this device.")
            return OperationResult(ok=True, data={})
        except Exception as e:
            logger.error("SU EEPROM load failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    # =========================================================================
    # Test Operations (hw_verify)
    # =========================================================================

    def read_temperature(self) -> OperationResult:
        """Read SU temperature sensor.

        Returns:
            OperationResult with temperature in data["temperature"].
        """
        try:
            su = self._get_su()
            temp = su.get_temperature()
            logger.debug("SU temperature: %s", temp)
            return OperationResult(ok=True, data={"temperature": temp})
        except Exception as e:
            logger.error("SU temperature read failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def perform_autocalibration(self) -> OperationResult:
        """Run autocalibration on SU.

        Returns:
            OperationResult with success status.
        """
        try:
            su = self._get_su()
            su.performautocalibration()
            serial = getattr(su, "_serial", None) or su.serial
            logger.info("SU autocalibration complete: serial=%s", serial)
            return OperationResult(ok=True, serial=serial)
        except Exception as e:
            logger.error("SU autocalibration failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def single_shot_measure(
        self,
        dac_voltage: float = 0.0,
        source: str = "VCAL",
        reference: str = "CAL",
    ) -> OperationResult:
        """Perform single-shot voltage measurement.

        Args:
            dac_voltage: DAC output voltage.
            source: Signal source path ("VCAL", "IN", "GND", "REF_GND").
            reference: Reference selection.

        Returns:
            OperationResult with voltage in data["voltage"].
        """
        try:
            su = self._get_su()
            su.singleshot_init(1)
            su.setDACValue(dac_voltage)
            su.setPath(source=source, ac=0, adc=None, amp=1.0)
            # readInputVoltage returns (samples_array, timestamps_array)
            samples, _timestamps = su.readInputVoltage()
            voltage = float(samples[0])
            logger.debug("SU single-shot: %sV", voltage)
            return OperationResult(ok=True, data={"voltage": voltage})
        except Exception as e:
            logger.error("SU single-shot failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def transient_measure(
        self,
        measurement_time: float,
        sampling_rate: float = 1e-6,
        trigger: str = "none",
    ) -> OperationResult:
        """Perform transient measurement.

        Args:
            measurement_time: Total measurement time in seconds.
            sampling_rate: Sampling period in seconds.
            trigger: Trigger mode.

        Returns:
            OperationResult with time/values arrays in data.
        """
        sampling_started = False
        try:
            su = self._get_su()
            mcu = self._get_mcu()

            # Setup MCU sync if available
            if mcu:
                mcu.setSUSyncTimerFrequency(1000e3)

            su.transientSampling_init(
                measurementTime=measurement_time,
                trigger=trigger,
                samplingmode=("linear", sampling_rate),
                measurementDelay=0.0,
                adcmaster=0 if mcu else 1,
            )
            su.transientSampling_start()
            sampling_started = True

            # Read data — returns (samples, (timestamps, split))
            samples, (timestamps, _split) = su.transientSampling_readData()
            logger.debug("SU transient: %s samples", len(samples))
            time_data = timestamps.tolist() if hasattr(timestamps, "tolist") else list(timestamps)
            values_data = samples.tolist() if hasattr(samples, "tolist") else list(samples)
            return OperationResult(
                ok=True,
                data={"time": time_data, "values": values_data},
            )
        except Exception as e:
            if sampling_started:
                with contextlib.suppress(Exception):
                    self._get_su().singleshot_init(1)
                    logger.info("SU reset to single-shot after transient failure")
            logger.error("SU transient failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def pulse_measure(
        self,
        num_samples: int,
        sampling_rate: float = 1e6,
    ) -> OperationResult:
        """Perform pulse measurement.

        Args:
            num_samples: Number of samples to acquire.
            sampling_rate: Sampling frequency in Hz.

        Returns:
            OperationResult with time/values arrays in data.
        """
        sampling_started = False
        try:
            su = self._get_su()
            mcu = self._get_mcu()

            # Setup MCU sync if available
            if mcu:
                mcu.setSUSyncTimerFrequency(1000e3)

            su.singleshot_init(1)  # Workaround for pulse mode
            su.pulseSampling_init(num_samples)
            su.setADC(master=0, dcmi=1, adcB=0, frequency=sampling_rate)
            su.pulseSampling_start()
            sampling_started = True

            # Trigger via MCU if available
            if mcu:
                mcu.su_set_trigger()

            # Read data — returns (samples, timestamps)
            samples, timestamps = su.pulseSampling_readData()
            logger.debug("SU pulse: %s samples", len(samples))
            time_data = timestamps.tolist() if hasattr(timestamps, "tolist") else list(timestamps)
            values_data = samples.tolist() if hasattr(samples, "tolist") else list(samples)
            return OperationResult(
                ok=True,
                data={"time": time_data, "values": values_data},
            )
        except Exception as e:
            if sampling_started:
                with contextlib.suppress(Exception):
                    self._get_su().singleshot_init(1)
                    logger.info("SU reset to single-shot after pulse failure")
            logger.error("SU pulse failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    # =========================================================================
    # Calibration Operations
    # =========================================================================

    # Speed preset definitions: (decades, delta_log, delta_lin)
    # Original script: calibration max_value=2.4, decades=7, delta_log=1/3, delta_lin=1/8
    # max_value MUST stay ≤2.4 — higher values drive the SU amplifiers into
    # saturation (flat ADC output), corrupting the calibration model.
    SPEED_PRESETS = {
        "fast": (2.0, 1 / 2, 1.0),
        "normal": (7, 1 / 3, 1 / 8),
        "precise": (8, 1 / 10, 1 / 5),
    }
    # Verification uses sparser points at slightly lower voltage to avoid
    # retesting the exact same setpoints as calibration.
    VERIFY_PRESETS = {
        "fast": (2.0, 1 / 2, 1 / 3),
        "normal": (8, 1 / 2, 1 / 5),
        "precise": (8, 1 / 3, 1 / 5),
    }
    _CAL_MAX_VALUE = 2.4
    _VERIFY_MAX_VALUE = 2.2

    def calibration_measure(
        self,
        keithley_ip: str,
        smu_serial: int | None,
        smu_interface: int | None,
        su_serial: int | None,
        su_interface: int | None,
        folder_path: str,
        verify_calibration: bool = False,
        verify_only: bool = False,
        amp_channels: list[str] | None = None,
        speed_preset: str = "normal",
        single_range: str | None = None,
        on_point_measured: Callable[[dict], None] | None = None,
        on_range_started: Callable[[dict], None] | None = None,
        cancel_event: threading.Event | None = None,
    ) -> OperationResult:
        """Run the full calibration measurement workflow.

        Creates an SUCalibrationMeasure instance, measures all or single
        ranges, emits live progress via callbacks, and saves results to HDF5.

        Args:
            keithley_ip: Keithley instrument IP address.
            smu_serial: SMU serial number (None for autodetect).
            smu_interface: SMU interface number.
            su_serial: SU serial number (None for autodetect).
            su_interface: SU interface number.
            folder_path: Output folder for calibration data.
            verify_calibration: If True, also run verification measurements.
            verify_only: If True, only run verification measurements.
            amp_channels: AMP channels to measure (default: all from device).
            speed_preset: "fast", "normal", or "precise".
            single_range: If set, amp_channel name for single range measurement.
            on_point_measured: Callback for each measured point.
            on_range_started: Callback for range start/done events.
            cancel_event: Optional threading event to cancel measurement.

        Returns:
            OperationResult with folder path in data.
        """
        scm = None
        try:
            from dpi.utilities import DPILogger

            from src.logic.calibration import SUCalibrationMeasure

            # Ensure absolute path
            folder_path = str(Path(folder_path).resolve())

            print("-- SU Calibration Measurement --")
            print(f"  Keithley  : {keithley_ip}")
            print(f"  Folder    : {folder_path}")
            print(f"  Speed     : {speed_preset}")

            scm = SUCalibrationMeasure(
                keithley_ip,
                smu_serial,
                smu_interface,
                su_serial,
                su_interface,
                DPILogger.VERBOSE,
            )

            # Prepare voltage values for calibration and verification.
            # Calibration uses denser points; verification uses sparser
            # points at a slightly lower max to avoid retesting identical
            # setpoints.  max_value ≤ 2.4 V — higher values saturate the
            # SU amplifiers.
            cal_values = None
            verify_values = None
            if speed_preset in self.SPEED_PRESETS:
                d, dl, dlin = self.SPEED_PRESETS[speed_preset]
                cal_values = scm.prepare_measurement_values(
                    max_value=self._CAL_MAX_VALUE,
                    decades=d,
                    delta_log=dl,
                    delta_lin=dlin,
                )
                vd, vdl, vdlin = self.VERIFY_PRESETS[speed_preset]
                verify_values = scm.prepare_measurement_values(
                    max_value=self._VERIFY_MAX_VALUE,
                    decades=vd,
                    delta_log=vdl,
                    delta_lin=vdlin,
                )

            if verify_only:
                verify_list = [True]
            elif verify_calibration:
                verify_list = [False, True]
            else:
                verify_list = [False]

            # Determine which amp channels to measure
            available = list(scm.ampchannels)
            if amp_channels:
                invalid = [ch for ch in amp_channels if ch not in available]
                if invalid:
                    print(
                        f"  WARNING: Channels {invalid} not found on device "
                        f"(available: {available}) — skipping"
                    )
                channels_to_measure = [ch for ch in amp_channels if ch in available]
                if not channels_to_measure:
                    return OperationResult(
                        ok=False,
                        message=f"None of the selected channels {amp_channels} "
                        f"exist on the device (available: {available})",
                    )
            else:
                channels_to_measure = available
            print(f"  Channels  : {', '.join(channels_to_measure)}")

            completed_ranges = 0
            total_ranges = 0
            cancelled = False

            # save_measurement appends device_serial to folder_path,
            # so strip it to avoid double-appending
            save_base = folder_path
            device_serial = str(scm.device_serial)
            if device_serial and save_base.endswith(device_serial):
                save_base = save_base[: -len(device_serial)]

            for verify in verify_list:
                phase = "Verification" if verify else "Calibration"
                print(f"\n>> Measuring ({phase})...")
                scm.data = []

                voltage_values = verify_values if verify else cal_values
                filename = "raw_data_verify.h5" if verify else "raw_data.h5"

                # Delete old file so we start fresh (unless single-range,
                # where the user is intentionally appending one range at a time)
                if not single_range:
                    old_file = Path(f"{save_base}{scm.device_serial}") / filename
                    if old_file.exists():
                        old_file.unlink()
                        print(f"  Cleared previous {filename}")

                if single_range:
                    # Single range measurement
                    print(f"  Range: AMP={single_range}")
                    total = len(voltage_values) if voltage_values is not None else 0
                    adapter = _SUProgressAdapter(
                        total,
                        scm,
                        on_point_measured,
                        on_range_started,
                        verify=verify,
                    )
                    adapter.set_description(f"AMP: {single_range}, VL: {total}")
                    scm.measure_single_range(
                        single_range,
                        voltage_values,
                        progress_bar=adapter,
                    )
                    adapter.close()
                    completed_ranges += 1
                    scm.save_measurement(
                        folder_path=save_base,
                        file_name=filename,
                        append_data=True,
                    )
                else:
                    # Per-range loop for cancel support
                    total_ranges += len(channels_to_measure)
                    total = len(channels_to_measure) * (
                        len(voltage_values) if voltage_values is not None else 0
                    )
                    adapter = _SUProgressAdapter(
                        total,
                        scm,
                        on_point_measured,
                        on_range_started,
                        verify=verify,
                    )

                    for amp_ch in channels_to_measure:
                        if cancel_event and cancel_event.is_set():
                            cancelled = True
                            break
                        n_vals = len(voltage_values) if voltage_values is not None else 0
                        adapter.set_description(f"AMP: {amp_ch}, VL: {n_vals}")
                        scm.measure_single_range(
                            amp_ch,
                            voltage_values,
                            progress_bar=adapter,
                        )
                        completed_ranges += 1
                        scm.save_measurement(
                            folder_path=save_base,
                            file_name=filename,
                            append_data=True,
                        )
                    adapter.close()

                print(f"  Saved {filename}")
                if cancelled:
                    break

            scm.cleanup()
            # Release USB connections so subsequent runs can reconnect
            with contextlib.suppress(Exception):
                scm.smu.disconnect()
            with contextlib.suppress(Exception):
                scm.su.disconnect()

            if cancelled:
                print(
                    f"-- Cancelled: {completed_ranges}/{total_ranges} ranges measured and saved --"
                )
                logger.info("SU calibration cancelled after %d ranges", completed_ranges)
                return OperationResult(
                    ok=True,
                    data={
                        "folder": folder_path,
                        "cancelled": True,
                        "completed_ranges": completed_ranges,
                        "total_ranges": total_ranges,
                    },
                )

            print("-- Measurement complete --")
            logger.info("SU calibration measure complete: %s", folder_path)
            return OperationResult(ok=True, data={"folder": folder_path})
        except Exception as e:
            # Attempt to release USB even on failure
            if scm is not None:
                with contextlib.suppress(Exception):
                    scm.cleanup()
                with contextlib.suppress(Exception):
                    scm.smu.disconnect()
                with contextlib.suppress(Exception):
                    scm.su.disconnect()
            logger.error("SU calibration measure failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def calibration_fit(
        self,
        folder_path: str,
        draw_plot: bool = True,
        auto_calibrate: bool = False,
        model_type: str = "linear",
        verify_calibration: bool = True,
        single_range: str | None = None,
    ) -> OperationResult:
        """Run calibration fit and optionally write to EEPROM.

        Loads raw measurement data, trains models, analyzes ranges,
        and optionally writes calibration to the device EEPROM.
        Returns paths to generated analysis PNGs.

        Args:
            folder_path: Folder containing calibration measurements.
            draw_plot: If True, generate overview plots.
            auto_calibrate: If True, write calibration to EEPROM.
            model_type: Model to save ("linear" or "gp").
            verify_calibration: If True, load verification data too.
            single_range: If set, amp_channel to fit only that range.
                Loads existing model first so other ranges are preserved.

        Returns:
            OperationResult with folder path and analysis_plots list.
        """
        try:
            from dpi.utilities import DPILogger

            from src.logic.calibration import SUCalibrationFit

            # Ensure absolute path
            folder_path = str(Path(folder_path).resolve())

            # Auto-detect verify data availability
            verify_file = Path(folder_path) / "raw_data_verify.h5"
            if verify_calibration and not verify_file.exists():
                print("  No verification data found, skipping verify.")
                verify_calibration = False

            print("-- SU Calibration Fit --")
            print(f"  Folder  : {folder_path}")
            print(f"  Model   : {model_type}")
            print(f"  Verify  : {verify_calibration}")
            if single_range:
                print(f"  Range   : {single_range}")

            smf = SUCalibrationFit(
                calibration_folder=folder_path,
                load_raw=True,
                verify_calibration=verify_calibration,
                log_level=DPILogger.DEBUG,
            )

            if single_range:
                key = single_range

                # Load existing models so other ranges are preserved
                print(">> Loading existing model...")
                try:
                    smf.load_model(script_dir=Path("/"), model_type=model_type)
                except Exception as e:
                    print(f"  No existing model found ({e}), starting fresh.")

                # Verify data exists for this key
                if key not in (smf.data or {}):
                    available = list((smf.data or {}).keys())
                    print(f"  ERROR: No data for key {key}")
                    print(f"  Available keys: {available}")
                    return OperationResult(
                        ok=False,
                        message=f"No measurement data for amp_channel={key}. "
                        f"Available: {available}",
                    )

                # Ensure model dict exists
                if smf.model is None:
                    smf.model = {}
                if key not in smf.model:
                    smf.model[key] = {}

                print(f">> Training {model_type} model for {key}...")
                smf.train_linear_model(key)
                if model_type == "gp":
                    smf.train_gp_model(key)

                smf.save_model(script_dir=Path("/"), model_type=model_type)

                print(f">> Analyzing range {key}...")
                smf.analyze_range(key, save_plot=True)

            else:
                if draw_plot:
                    print(">> Plotting measurement overview...")
                    smf.plot_measurement_overview()
                    try:
                        smf.plot_aggregated_overview()
                    except (KeyError, Exception) as e:
                        print(f"  Aggregated overview skipped ({e})")

                print(">> Training linear model...")
                smf.train_linear_model()

                if model_type == "gp":
                    print(">> Training GP model...")
                    smf.train_gp_model()

                # save_model does script_dir / calibration_folder internally.
                # Since calibration_folder is absolute, Path("/") works as a no-op root.
                smf.save_model(script_dir=Path("/"), model_type=model_type)
                print(">> Analyzing ranges...")
                smf.analyze_ranges(save_plot=True)

                if draw_plot:
                    print(">> Plotting calibrated overview...")
                    try:
                        smf.plot_calibrated_overview(model_type=model_type)
                    except (KeyError, Exception) as e:
                        print(f"  Calibrated overview skipped ({e})")

            # Collect analysis plot paths
            analysis_plots = self._collect_analysis_plots(folder_path)
            calibrated_ranges = self._parse_calibrated_ranges(analysis_plots)
            print(f"  Generated {len(analysis_plots)} analysis plots")

            if auto_calibrate:
                print(">> Writing calibration to EEPROM...")
                su = self._get_su()
                su.calibrate_eeprom(folder_path=Path(folder_path))
                print("  EEPROM written successfully")

            print("-- Fit complete --")
            logger.info("SU calibration fit complete: %s", folder_path)
            return OperationResult(
                ok=True,
                data={
                    "folder": folder_path,
                    "analysis_plots": analysis_plots,
                    "calibrated_ranges": calibrated_ranges,
                },
            )
        except Exception as e:
            import traceback

            traceback.print_exc()
            print(f"Fit failed: {e}")
            logger.error("SU calibration fit failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def _collect_analysis_plots(self, folder_path: str) -> list[str]:
        """Collect generated analysis PNG paths from the figures directory."""
        ranges_dir = Path(folder_path) / "figures" / "ranges"
        if not ranges_dir.exists():
            return []
        return sorted(str(p) for p in ranges_dir.glob("*_analyze.png"))

    # Regex matching the HDF5 key format produced by SU's save_measurement:
    #   amp=AMP1 v_set=0.001
    _H5_KEY_RE = re.compile(r"amp=(\w+)")

    @staticmethod
    def _parse_calibrated_ranges(plot_paths: list[str]) -> list[dict]:
        """Parse analysis plot filenames to extract calibrated range info.

        Filenames follow: amp_{channel}_analyze.png
        """
        ranges = []
        for p in plot_paths:
            stem = Path(p).stem.replace("_analyze", "")
            # Expected: "amp_AMP1" -> amp_channel = "AMP1"
            if stem.startswith("amp_"):
                amp_channel = stem[4:]
                ranges.append({"amp_channel": amp_channel})
        return ranges

    def get_calibration_status(self, folder_path: str) -> list[dict]:
        """Scan calibration folder and return per-range status.

        Checks raw_data.h5 for measured keys, raw_data_verify.h5 for
        verified keys, and figures/ranges/ for analysis plots to determine
        which ranges are measured/verified/calibrated.

        Returns:
            List of dicts with keys: amp_channel, measured, verified,
            calibrated, points, verify_points.
        """
        from collections import defaultdict

        folder = Path(folder_path)
        calibrated_keys: set[str] = set()

        def _scan_h5(filepath: Path) -> dict[str, int]:
            counts: dict[str, int] = defaultdict(int)
            if not filepath.exists():
                return counts
            try:
                import h5py

                with h5py.File(str(filepath), "r") as f:
                    for key in f:
                        m = self._H5_KEY_RE.search(key)
                        if m:
                            counts[m.group(1)] += 1
            except Exception as e:
                print(f"  Warning: could not read {filepath.name}: {e}")
            return counts

        measured_counts = _scan_h5(folder / "raw_data.h5")
        verified_counts = _scan_h5(folder / "raw_data_verify.h5")

        # Check analysis plots for calibrated ranges
        analysis_plots = self._collect_analysis_plots(folder_path)
        for info in self._parse_calibrated_ranges(analysis_plots):
            calibrated_keys.add(info["amp_channel"])

        # Merge into unified list
        all_keys = set(measured_counts) | set(verified_counts) | calibrated_keys
        ranges = []
        for amp_ch in sorted(all_keys):
            ranges.append(
                {
                    "amp_channel": amp_ch,
                    "measured": amp_ch in measured_counts,
                    "verified": amp_ch in verified_counts,
                    "calibrated": amp_ch in calibrated_keys,
                    "points": measured_counts.get(amp_ch, 0),
                    "verify_points": verified_counts.get(amp_ch, 0),
                }
            )
        return ranges

    def delete_calibration_ranges(
        self,
        folder_path: str,
        ranges: list[str],
        target: str = "raw",
    ) -> OperationResult:
        """Delete specific ranges from calibration HDF5 files.

        Args:
            folder_path: Calibration folder.
            ranges: List of amp_channel names to delete.
            target: "raw", "verify", or "both".

        Returns:
            OperationResult with deleted count.
        """
        try:
            import h5py

            targets_set = set(ranges)
            filenames = []
            if target in ("raw", "both"):
                filenames.append("raw_data.h5")
            if target in ("verify", "both"):
                filenames.append("raw_data_verify.h5")

            total_deleted = 0
            for fname in filenames:
                fpath = Path(folder_path) / fname
                if not fpath.exists():
                    continue
                with h5py.File(str(fpath), "a") as f:
                    keys_to_delete = []
                    for key in f:
                        m = self._H5_KEY_RE.search(key)
                        if m and m.group(1) in targets_set:
                            keys_to_delete.append(key)
                    for key in keys_to_delete:
                        del f[key]
                    total_deleted += len(keys_to_delete)
                print(f"  Deleted {len(keys_to_delete)} entries from {fname}")

            print(f"-- Deleted {total_deleted} total entries --")
            return OperationResult(ok=True, data={"deleted": total_deleted})
        except Exception as e:
            logger.error("Delete calibration ranges failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def clear_calibration_file(
        self,
        folder_path: str,
        target: str = "raw",
    ) -> OperationResult:
        """Delete an entire calibration HDF5 file.

        Args:
            folder_path: Calibration folder.
            target: "raw" or "verify".

        Returns:
            OperationResult with success status.
        """
        try:
            fname = "raw_data_verify.h5" if target == "verify" else "raw_data.h5"
            fpath = Path(folder_path) / fname
            if fpath.exists():
                fpath.unlink()
                print(f"  Deleted {fname}")
            else:
                print(f"  {fname} does not exist")
            return OperationResult(ok=True, data={"file": fname})
        except Exception as e:
            logger.error("Clear calibration file failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def clear_fitted_data(self, folder_path: str) -> OperationResult:
        """Delete fitted/analysis calibration artifacts.

        Removes aggregated HDF5 files, model files (.cal), and
        the figures directory (analysis plots + overview).

        Args:
            folder_path: Calibration folder.

        Returns:
            OperationResult with list of deleted items.
        """
        folder = Path(folder_path)
        deleted = []
        try:
            # Aggregated data files
            for name in ("aggregated.h5", "aggregated_verify.h5"):
                p = folder / name
                if p.exists():
                    p.unlink()
                    deleted.append(name)
                    print(f"  Deleted {name}")

            # Model files (linear_model.cal, gp_model.cal, etc.)
            for cal_file in folder.glob("*.cal"):
                cal_file.unlink()
                deleted.append(cal_file.name)
                print(f"  Deleted {cal_file.name}")

            # Figures directory (ranges plots + overview HTML)
            figures_dir = folder / "figures"
            if figures_dir.exists():
                shutil.rmtree(figures_dir)
                deleted.append("figures/")
                print("  Deleted figures/")

            print(f"-- Cleared {len(deleted)} fitted data item(s) --")
            return OperationResult(ok=True, data={"deleted": deleted})
        except Exception as e:
            logger.error("Clear fitted data failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    # =========================================================================
    # MCU Operations
    # =========================================================================

    def set_sync_frequency(
        self,
        su_frequency: float = 1000e3,
        vu_frequency: float = 1000e3,
    ) -> OperationResult:
        """Set MCU synchronization timer frequencies.

        Args:
            su_frequency: SU sync frequency in Hz.
            vu_frequency: VU sync frequency in Hz.

        Returns:
            OperationResult with success status.
        """
        try:
            mcu = self._get_mcu()
            if not mcu:
                return OperationResult(
                    ok=False,
                    message="MCU not connected",
                )
            mcu.setSUSyncTimerFrequency(su_frequency)
            mcu.setVUSyncTimerFrequency(vu_frequency)
            logger.debug("MCU sync frequencies: SU=%s, VU=%s", su_frequency, vu_frequency)
            return OperationResult(ok=True)
        except Exception as e:
            logger.error("MCU sync setup failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def trigger_su(self) -> OperationResult:
        """Send trigger to SU via MCU.

        Returns:
            OperationResult with success status.
        """
        try:
            mcu = self._get_mcu()
            if not mcu:
                return OperationResult(ok=False, message="MCU not connected")
            mcu.su_set_trigger()
            logger.debug("MCU trigger sent to SU")
            return OperationResult(ok=True)
        except Exception as e:
            logger.error("MCU trigger failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    # =========================================================================
    # Private helpers
    # =========================================================================

    def _get_su(self) -> "DPISamplingUnit":
        """Get or create DPISamplingUnit instance."""
        if self._su is None:
            from dpi import DPISamplingUnit

            self._su = DPISamplingUnit(autoinit=True)
        return self._su

    def _get_mcu(self) -> "DPIMainControlUnit | None":
        """Get MCU instance if available."""
        return self._mcu
