"""Source Measure Unit controller for hardware operations.

This controller encapsulates all SMU hardware workflows including setup, test,
relay control, and calibration operations. Uses direct imports from dpi package.
"""

import contextlib
import re
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from src.logging_config import get_logger
from src.logic.controllers.base_controller import (
    ChannelConfig,
    HardwareController,
    OperationResult,
)

if TYPE_CHECKING:
    from dpi import DPISourceMeasureUnit

logger = get_logger(__name__)

# Type aliases for relay settings
InputRouting = Literal["GND", "GUARD", "VSMU", "SU", "VSMU_AND_SU"]
VGuardRouting = Literal["GND", "VSMU"]
ReferenceType = Literal["GND", "VSMU"]


class _ProgressAdapter:
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
                    "vsmu": df.attrs.get("vsmu_mode"),
                    "pa": df.attrs.get("pa_channel"),
                    "iv": df.attrs.get("iv_channel"),
                    "verify": self._verify,
                    "x": float(df.attrs.get("i_ref", 0)),
                    "y": float(df["current"].mean()),
                    "i_set": float(df.attrs.get("i_set", 0)),
                    "point_index": self.n,
                    "total_points": self.total,
                }
            )

    @staticmethod
    def _parse_desc(desc: str) -> dict:
        """Extract pa/iv/vsmu fields from a range description string."""
        m = re.match(r"PA: (\w+), IV: (\w+), VSMU: (\w+)", desc)
        if m:
            return {"pa": m.group(1), "iv": m.group(2), "vsmu": m.group(3) == "True"}
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
                if "pa" in running_data:
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


class SMUController(HardwareController):
    """Controller for Source Measure Unit hardware operations.

    Manages setup, test, relay control, and calibration workflows for SMU devices.

    Attributes:
        _smu: DPISourceMeasureUnit instance (injected or auto-created).
    """

    def __init__(self, smu: "DPISourceMeasureUnit | None" = None) -> None:
        """Initialize SMUController.

        Args:
            smu: Optional pre-connected DPISourceMeasureUnit instance.
        """
        self._smu = smu

    # =========================================================================
    # Setup Operations (hw_setup)
    # =========================================================================

    def initialize_device(
        self,
        serial: int,
        processor_type: str = "746",
        connector_type: str = "BNC",
    ) -> OperationResult:
        """Initialize a new SMU device after first flash.

        Sets EEPROM defaults and writes device identity.

        Args:
            serial: Device serial number (1-9999).
            processor_type: Processor type ("746").
            connector_type: Connector type ("BNC" or "TRIAX").

        Returns:
            OperationResult with success status and serial number.
        """
        try:
            smu = self._get_smu()
            smu.set_eeprom_default_values()
            smu.initNewDevice(
                serial=serial,
                processorType=processor_type,
                connectorType=connector_type,
            )
            logger.info("SMU initialized: serial=%s", serial)
            return OperationResult(ok=True, serial=serial)
        except Exception as e:
            logger.error("SMU initialization failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def set_eeprom_defaults(self) -> OperationResult:
        """Reset EEPROM to default values.

        Returns:
            OperationResult with success status.
        """
        try:
            smu = self._get_smu()
            smu.set_eeprom_default_values()
            logger.info("SMU EEPROM defaults set")
            return OperationResult(ok=True)
        except Exception as e:
            logger.error("SMU EEPROM defaults failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def calibrate_eeprom(self) -> OperationResult:
        """Calibrate EEPROM values.

        Returns:
            OperationResult with success status.
        """
        try:
            smu = self._get_smu()
            smu.calibrate_eeprom()
            logger.info("SMU EEPROM calibrated")
            return OperationResult(ok=True)
        except Exception as e:
            logger.error("SMU EEPROM calibration failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def configure_channel(self, config: ChannelConfig) -> OperationResult:
        """Configure an amplifier channel.

        Note: Channel config is calculated from R and C values (runtime only).

        Args:
            config: Channel configuration parameters.

        Returns:
            OperationResult with success status.
        """
        try:
            self._get_smu()
            logger.info("SMU channel configured: %s", config.channel_id)
            return OperationResult(ok=True, data={"channel_id": config.channel_id})
        except Exception as e:
            logger.error("SMU channel configuration failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def save_channel_config(self) -> OperationResult:
        """Save current channel configuration to EEPROM.

        Note: Channel calibration is managed by the calibration workflow.

        Returns:
            OperationResult with informational message.
        """
        try:
            self._get_smu()
            print(
                "Note: Channel calibration is managed by the calibration workflow.\n"
                "Use 'Run Calibration' on the Calibration page to write to EEPROM."
            )
            return OperationResult(ok=True, message="Use calibration workflow for EEPROM writes.")
        except Exception as e:
            logger.error("SMU EEPROM save failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def load_channel_config(self) -> OperationResult:
        """Load channel configuration from EEPROM.

        Returns:
            OperationResult with channel list in data["channels"].
            Each channel dict has: id, ch_type, type, gain, range, bandwidth.
        """
        try:
            import numpy as np
            from dpi.unit import DPIEpromEntry

            smu = self._get_smu()
            print("-- Reading EEPROM --")
            with contextlib.suppress(AttributeError):
                smu.printEpromContent()

            channels = []
            try:
                eprom = smu.get_eeprom_interface().entries
                for name, entry in eprom.items():
                    ch_type_str = (
                        "INPUT" if entry.ch_type == DPIEpromEntry.ChannelType.INPUT else "AMPLIFIER"
                    )
                    amp_type = getattr(entry.type, "name", str(entry.type))
                    gain = getattr(entry, "gain", 0)
                    bw = getattr(entry, "bandwidth", None)

                    if ch_type_str == "INPUT":
                        iv_range = round(-np.log10(np.abs(gain)), 1) if gain != 0 else 0
                        ch_info = {
                            "id": name,
                            "ch_type": ch_type_str,
                            "type": amp_type,
                            "gain": gain,
                            "range": iv_range,
                            "bandwidth": bw,
                        }
                    else:
                        pa_range = round(np.log10(np.abs(gain))) if gain != 0 else 0
                        ch_info = {
                            "id": name,
                            "ch_type": ch_type_str,
                            "type": amp_type,
                            "gain": gain,
                            "range": pa_range,
                            "bandwidth": bw,
                        }

                    channels.append(ch_info)
                    tag = "IV" if ch_type_str == "INPUT" else "PA"
                    print(
                        f"  [{tag}] {name:<8} {amp_type:<6} "
                        f"gain={gain:.2e}  range={ch_info['range']}"
                    )
                print(f"  {len(channels)} channels loaded")
            except Exception as e:
                print(f"  EEPROM enumeration failed: {e}")

            return OperationResult(ok=True, data={"channels": channels})
        except Exception as e:
            logger.error("SMU EEPROM load failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    # =========================================================================
    # Test Operations (hw_verify) - Temperature
    # =========================================================================

    def read_temperature(self) -> OperationResult:
        """Read SMU temperature sensor.

        Returns:
            OperationResult with temperature in data["temperature"].
        """
        try:
            smu = self._get_smu()
            temp = smu.get_temperature()
            logger.debug("SMU temperature: %s", temp)
            return OperationResult(ok=True, data={"temperature": temp})
        except Exception as e:
            logger.error("SMU temperature read failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def perform_autocalibration(self) -> OperationResult:
        """Run autocalibration on SMU.

        Returns:
            OperationResult with success status.
        """
        try:
            smu = self._get_smu()
            smu.calibrate_eeprom()
            serial = smu.serial
            logger.info("SMU autocalibration complete: serial=%s", serial)
            return OperationResult(ok=True, serial=serial)
        except Exception as e:
            logger.error("SMU autocalibration failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    # =========================================================================
    # Relay Controls
    # =========================================================================

    def set_iv_channel(
        self,
        channel: int,
        reference: ReferenceType = "GND",
    ) -> OperationResult:
        """Set IV-Converter channel and reference.

        Args:
            channel: Channel number (0=disable, 1-9=enable).
            reference: Reference voltage ("GND" or "VSMU").

        Returns:
            OperationResult with success status.
        """
        try:
            smu = self._get_smu()
            if channel == 0:
                smu.ivconverter_channel(channel=0)
            else:
                smu.ivconverter_channelreference(channel=channel, reference=reference)
            logger.debug("SMU IV channel: %s, ref=%s", channel, reference)
            return OperationResult(
                ok=True,
                data={"channel": channel, "reference": reference},
            )
        except Exception as e:
            logger.error("SMU IV channel set failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def get_iv_channel(self) -> OperationResult:
        """Get current IV-Converter channel.

        Returns:
            OperationResult with channel in data["channel"].
        """
        try:
            smu = self._get_smu()
            channel = smu.ivconverter_getchannel()
            return OperationResult(ok=True, data={"channel": channel})
        except Exception as e:
            logger.error("SMU IV channel get failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def set_pa_channel(self, channel: int) -> OperationResult:
        """Set Post-Amplifier channel.

        Args:
            channel: Channel number (0=disable, 1-4=enable).

        Returns:
            OperationResult with success status.
        """
        try:
            smu = self._get_smu()
            if channel == 0:
                smu.postamplifier_disable()
            else:
                smu.postamplifier_enable(channel=channel)
            logger.debug("SMU PA channel: %s", channel)
            return OperationResult(ok=True, data={"channel": channel})
        except Exception as e:
            logger.error("SMU PA channel set failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def set_pa_clip(self, channel: int, enabled: bool) -> OperationResult:
        """Enable/disable Post-Amplifier clip detection.

        Args:
            channel: PA channel (1-4).
            enabled: Whether to enable clip detection.

        Returns:
            OperationResult with success status.
        """
        try:
            smu = self._get_smu()
            smu.postamplifier_clip_enable(channel=channel, state=1 if enabled else 0)
            logger.debug("SMU PA clip: ch=%s, enabled=%s", channel, enabled)
            return OperationResult(ok=True)
        except Exception as e:
            logger.error("SMU PA clip set failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def set_highpass(self, enabled: bool) -> OperationResult:
        """Enable/disable highpass filter.

        Args:
            enabled: Whether to enable highpass.

        Returns:
            OperationResult with success status.
        """
        try:
            smu = self._get_smu()
            if enabled:
                smu.highpass_enable()
            else:
                smu.highpass_disable()
            logger.debug("SMU highpass: enabled=%s", enabled)
            return OperationResult(ok=True, data={"enabled": enabled})
        except Exception as e:
            logger.error("SMU highpass set failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def get_highpass_state(self) -> OperationResult:
        """Get current highpass filter state.

        Returns:
            OperationResult with state in data["enabled"].
        """
        try:
            smu = self._get_smu()
            state = smu.highpass_state()
            return OperationResult(ok=True, data={"enabled": bool(state)})
        except Exception as e:
            logger.error("SMU highpass state get failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def set_input_routing(self, target: InputRouting) -> OperationResult:
        """Set input routing (DUT connection).

        Args:
            target: Input routing target.

        Returns:
            OperationResult with success status.
        """
        try:
            smu = self._get_smu()
            routing_map = {
                "GND": smu.iin_to_gnd,
                "GUARD": smu.iin_to_guard,
                "VSMU": smu.iin_to_vsmu,
                "SU": smu.iin_to_su,
                "VSMU_AND_SU": smu.iin_to_vsmu_and_su,
            }
            routing_map[target]()
            logger.debug("SMU input routing: %s", target)
            return OperationResult(ok=True, data={"target": target})
        except Exception as e:
            logger.error("SMU input routing set failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def set_vguard(self, target: VGuardRouting) -> OperationResult:
        """Set VGUARD routing.

        Args:
            target: VGUARD target ("GND" or "VSMU").

        Returns:
            OperationResult with success status.
        """
        try:
            smu = self._get_smu()
            if target == "GND":
                smu.vguard_to_gnd()
            else:
                smu.vguard_to_vsmu()
            logger.debug("SMU VGUARD: %s", target)
            return OperationResult(ok=True, data={"target": target})
        except Exception as e:
            logger.error("SMU VGUARD set failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def get_saturation_state(self) -> OperationResult:
        """Get saturation detection state.

        Returns:
            OperationResult with IV and PA states.
        """
        try:
            smu = self._get_smu()
            state_iv, state_pa = smu.saturationdetection_state()
            return OperationResult(
                ok=True,
                data={"iv_saturated": bool(state_iv), "pa_saturated": bool(state_pa)},
            )
        except Exception as e:
            logger.error("SMU saturation state get failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def clear_saturation(self) -> OperationResult:
        """Clear saturation detection flags.

        Returns:
            OperationResult with success status.
        """
        try:
            smu = self._get_smu()
            smu.saturationdetection_clear()
            return OperationResult(ok=True)
        except Exception as e:
            logger.error("SMU saturation clear failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    # =========================================================================
    # Calibration Operations
    # =========================================================================

    # Speed preset definitions: (decades, delta_log, delta_lin)
    SPEED_PRESETS = {
        "fast": (2.0, 1 / 2, 1.0),
        "normal": (5, 1 / 3, 1 / 4),
        "precise": (8, 1 / 10, 1 / 5),
    }

    def calibration_measure(
        self,
        keithley_ip: str,
        smu_serial: int | None,
        smu_interface: int | None,
        su_serial: int | None,
        su_interface: int | None,
        folder_path: str,
        vsmu_mode: bool | None = None,
        verify_calibration: bool = False,
        verify_only: bool = False,
        pa_channels: list[str] | None = None,
        speed_preset: str = "normal",
        single_range: tuple[str, str] | None = None,
        on_point_measured: Callable[[dict], None] | None = None,
        on_range_started: Callable[[dict], None] | None = None,
        cancel_event: threading.Event | None = None,
    ) -> OperationResult:
        """Run the full calibration measurement workflow.

        Creates an SMUCalibrationMeasure instance, measures all or single
        ranges, emits live progress via callbacks, and saves results to HDF5.

        Args:
            keithley_ip: Keithley instrument IP address.
            smu_serial: SMU serial number (None for autodetect).
            smu_interface: SMU interface number.
            su_serial: SU serial number (None for autodetect).
            su_interface: SU interface number.
            folder_path: Output folder for calibration data.
            vsmu_mode: True for VSMU mode, False for normal, None for both.
            verify_calibration: If True, also run verification measurements.
            pa_channels: PA channels to measure (default: pach0, pach2, pach3).
            speed_preset: "fast", "normal", or "precise".
            single_range: If set, (pa_channel, iv_channel) for single range.
            on_point_measured: Callback for each measured point.
            on_range_started: Callback for range start/done events.
            cancel_event: Optional threading event to cancel measurement.
            verify_only: If True, only run verification measurements.

        Returns:
            OperationResult with folder path in data.
        """
        try:
            from dpi.utilities import DPILogger
            from dpisourcemeasureunit.calibration import SMUCalibrationMeasure

            if pa_channels is None:
                pa_channels = ["pach0", "pach2", "pach3"]

            # Ensure absolute path
            folder_path = str(Path(folder_path).resolve())

            vsmu_label = {None: "Both", True: "VSMU only", False: "Normal only"}.get(
                vsmu_mode, str(vsmu_mode)
            )
            print("-- SMU Calibration Measurement --")
            print(f"  Keithley  : {keithley_ip}")
            print(f"  Folder    : {folder_path}")
            print(f"  Channels  : {', '.join(pa_channels)}")
            print(f"  VSMU      : {vsmu_label}")
            print(f"  Speed     : {speed_preset}")

            scm = SMUCalibrationMeasure(
                keithley_ip,
                smu_serial,
                smu_interface,
                su_serial,
                su_interface,
                DPILogger.VERBOSE,
            )

            # Prepare current values based on speed preset
            current_values = None
            if speed_preset in self.SPEED_PRESETS:
                decades, delta_log, delta_lin = self.SPEED_PRESETS[speed_preset]
                current_values = scm.prepare_measurement_values(
                    max_value=6.5,
                    decades=decades,
                    delta_log=delta_log,
                    delta_lin=delta_lin,
                )

            if verify_only:
                verify_list = [True]
            elif verify_calibration:
                verify_list = [False, True]
            else:
                verify_list = [False]
            completed_ranges = 0
            total_ranges = 0
            cancelled = False

            for verify in verify_list:
                phase = "Verification" if verify else "Calibration"
                print(f"\n>> Measuring ({phase})...")
                scm.data = []

                filename = "raw_data_verify.h5" if verify else "raw_data.h5"
                # save_measurement appends device_serial to folder_path,
                # so strip it to avoid double-appending
                save_base = folder_path
                device_serial = str(scm.device_serial)
                if device_serial and save_base.endswith(device_serial):
                    save_base = save_base[: -len(device_serial)]

                if single_range:
                    pa_ch, iv_ch = single_range
                    vsmu_val = vsmu_mode if vsmu_mode is not None else False
                    print(f"  Range: PA={pa_ch}, IV={iv_ch}, VSMU={vsmu_val}")
                    try:
                        total = scm._calculate_total_measurements(
                            [pa_ch],
                            [iv_ch],
                            vsmu_val,
                            verify,
                            current_values=current_values,
                        )
                    except Exception:
                        total = len(current_values) if current_values is not None else 0
                    adapter = _ProgressAdapter(
                        total,
                        scm,
                        on_point_measured,
                        on_range_started,
                        verify=verify,
                    )
                    adapter.set_description(f"PA: {pa_ch}, IV: {iv_ch}, VSMU: {vsmu_val}")
                    scm.measure_single_range(
                        pa_ch,
                        iv_ch,
                        vsmu_mode=vsmu_val,
                        verify_calibration=verify,
                        current_values=current_values,
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
                    # Explicit per-range loop for cancel support
                    vsmu_modes = [False, True] if vsmu_mode is None else [vsmu_mode]
                    range_combos = [
                        (pa, iv, vsmu_val)
                        for vsmu_val in vsmu_modes
                        for pa in pa_channels
                        for iv in scm.ivchannels
                    ]
                    total_ranges += len(range_combos)

                    total = scm._calculate_total_measurements(
                        pa_channels,
                        scm.ivchannels,
                        vsmu_mode,
                        verify,
                        current_values=current_values,
                    )
                    adapter = _ProgressAdapter(
                        total,
                        scm,
                        on_point_measured,
                        on_range_started,
                        verify=verify,
                    )

                    for pa, iv, vsmu_val in range_combos:
                        if cancel_event and cancel_event.is_set():
                            cancelled = True
                            break
                        adapter.set_description(f"PA: {pa}, IV: {iv}, VSMU: {vsmu_val}")
                        scm.measure_single_range(
                            pa,
                            iv,
                            vsmu_mode=vsmu_val,
                            verify_calibration=verify,
                            current_values=current_values,
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
                logger.info("SMU calibration cancelled after %d ranges", completed_ranges)
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
            logger.info("SMU calibration measure complete: %s", folder_path)
            return OperationResult(ok=True, data={"folder": folder_path})
        except Exception as e:
            # Attempt to release USB even on failure
            with contextlib.suppress(Exception):
                scm.cleanup()
            with contextlib.suppress(Exception):
                scm.smu.disconnect()
            with contextlib.suppress(Exception):
                scm.su.disconnect()
            logger.error("SMU calibration measure failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def calibration_fit(
        self,
        folder_path: str,
        draw_plot: bool = True,
        auto_calibrate: bool = False,
        model_type: str = "linear",
        verify_calibration: bool = True,
        single_range: tuple[bool, str, str] | None = None,
        vsmu_filter: bool | None = None,
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
            single_range: If set, (vsmu, pa_channel, iv_channel) to fit
                only that range. Loads existing model first so other
                ranges are preserved.
            vsmu_filter: If not None, only fit ranges matching this VSMU
                mode. Ignored when single_range is set.

        Returns:
            OperationResult with folder path and analysis_plots list.
        """
        try:
            from dpi.utilities import DPILogger
            from dpisourcemeasureunit.calibration import SMUCalibrationFit

            # Ensure absolute path
            folder_path = str(Path(folder_path).resolve())

            # Auto-detect verify data availability
            verify_file = Path(folder_path) / "raw_data_verify.h5"
            if verify_calibration and not verify_file.exists():
                print("  No verification data found, skipping verify.")
                verify_calibration = False

            print("-- SMU Calibration Fit --")
            print(f"  Folder  : {folder_path}")
            print(f"  Model   : {model_type}")
            print(f"  Verify  : {verify_calibration}")
            if single_range:
                print(
                    f"  Range   : vsmu={single_range[0]}, "
                    f"pa={single_range[1]}, iv={single_range[2]}"
                )

            smf = SMUCalibrationFit(
                calibration_folder=folder_path,
                load_raw=True,
                verify_calibration=verify_calibration,
                log_level=DPILogger.DEBUG,
            )

            if single_range:
                key = tuple(single_range)

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
                        message=f"No measurement data for vsmu={key[0]}, "
                        f"pa={key[1]}, iv={key[2]}. "
                        f"Available: {available}",
                    )

                # Ensure model dict exists and key is present
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

            elif vsmu_filter is not None:
                # All ranges filtered by VSMU mode: train all, analyze filtered
                print(f">> Training all ranges (will analyze VSMU={vsmu_filter} only)...")
                smf.train_linear_model()
                if model_type == "gp":
                    smf.train_gp_model()
                smf.save_model(script_dir=Path("/"), model_type=model_type)

                matching = [k for k in smf.model if k[0] == vsmu_filter]
                print(f">> Analyzing {len(matching)} ranges with VSMU={vsmu_filter}...")
                for key in matching:
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
                smu = self._get_smu()
                smu.calibrate_eeprom(folder_path=Path(folder_path))
                print("  EEPROM written successfully")

            print("-- Fit complete --")
            logger.info("SMU calibration fit complete: %s", folder_path)
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
            logger.error("SMU calibration fit failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def _collect_analysis_plots(self, folder_path: str) -> list[str]:
        """Collect generated analysis PNG paths from the figures directory."""
        ranges_dir = Path(folder_path) / "figures" / "ranges"
        if not ranges_dir.exists():
            return []
        return sorted(str(p) for p in ranges_dir.glob("*_analyze.png"))

    # Regex matching the HDF5 key format produced by DPI's save_measurement:
    #   vsmu=False pa=pach2 iv=ivch3 i_set=-1.000e-09
    _H5_KEY_RE = re.compile(r"vsmu=(True|False)\s+pa=(\w+)\s+iv=(\w+)")

    def get_calibration_status(self, folder_path: str) -> list[dict]:
        """Scan calibration folder and return per-range status.

        Checks raw_data.h5 for measured keys, raw_data_verify.h5 for
        verified keys, and figures/ranges/ for analysis plots to determine
        which ranges are measured/verified/calibrated.

        Returns:
            List of dicts with keys: vsmu, pa, iv, measured, verified,
            calibrated, points, verify_points.
        """
        from collections import defaultdict

        folder = Path(folder_path)
        calibrated_keys: set[tuple[bool, str, str]] = set()

        def _scan_h5(filepath: Path) -> dict[tuple[bool, str, str], int]:
            counts: dict[tuple[bool, str, str], int] = defaultdict(int)
            if not filepath.exists():
                return counts
            try:
                import h5py

                with h5py.File(str(filepath), "r") as f:
                    for key in f:
                        m = self._H5_KEY_RE.search(key)
                        if m:
                            vsmu = m.group(1) == "True"
                            counts[(vsmu, m.group(2), m.group(3))] += 1
            except Exception as e:
                print(f"  Warning: could not read {filepath.name}: {e}")
            return counts

        measured_counts = _scan_h5(folder / "raw_data.h5")
        verified_counts = _scan_h5(folder / "raw_data_verify.h5")

        # Check analysis plots for calibrated ranges
        analysis_plots = self._collect_analysis_plots(folder_path)
        for info in self._parse_calibrated_ranges(analysis_plots):
            calibrated_keys.add((info.get("vsmu", False), info.get("pa", ""), info.get("iv", "")))

        # Merge into unified list
        all_keys = set(measured_counts) | set(verified_counts) | calibrated_keys
        ranges = []
        for vsmu, pa, iv in sorted(all_keys):
            key = (vsmu, pa, iv)
            ranges.append(
                {
                    "vsmu": vsmu,
                    "pa": pa,
                    "iv": iv,
                    "measured": key in measured_counts,
                    "verified": key in verified_counts,
                    "calibrated": key in calibrated_keys,
                    "points": measured_counts.get(key, 0),
                    "verify_points": verified_counts.get(key, 0),
                }
            )
        return ranges

    def delete_calibration_ranges(
        self,
        folder_path: str,
        ranges: list[tuple[bool, str, str]],
        target: str = "raw",
    ) -> OperationResult:
        """Delete specific ranges from calibration HDF5 files.

        Args:
            folder_path: Calibration folder.
            ranges: List of (vsmu, pa, iv) tuples to delete.
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
                        if m:
                            vsmu = m.group(1) == "True"
                            if (vsmu, m.group(2), m.group(3)) in targets_set:
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
        import shutil

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

    @staticmethod
    def _parse_calibrated_ranges(plot_paths: list[str]) -> list[dict]:
        """Parse analysis plot filenames to extract calibrated range info.

        Filenames follow: vsmu_{bool}_pa_{pach}_iv_{ivch}_analyze.png
        """
        ranges = []
        for p in plot_paths:
            stem = Path(p).stem.replace("_analyze", "")
            parts = stem.split("_")
            info: dict = {}
            for i, token in enumerate(parts):
                if token == "vsmu" and i + 1 < len(parts):
                    info["vsmu"] = parts[i + 1] == "True"
                elif token == "pa" and i + 1 < len(parts):
                    info["pa"] = parts[i + 1]
                elif token == "iv" and i + 1 < len(parts):
                    info["iv"] = parts[i + 1]
            if "pa" in info and "iv" in info:
                ranges.append(info)
        return ranges

    # =========================================================================
    # Private helpers
    # =========================================================================

    def _get_smu(self) -> "DPISourceMeasureUnit":
        """Get or create DPISourceMeasureUnit instance."""
        if self._smu is None:
            from dpi import DPISourceMeasureUnit

            self._smu = DPISourceMeasureUnit(autoinit=True)
        return self._smu
