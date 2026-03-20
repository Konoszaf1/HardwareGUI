"""Voltage Unit controller for hardware operations.

This controller encapsulates all VU hardware workflows including setup, test,
calibration, coefficient management, and guard operations. Ports the logic from
the legacy setup_cal.py script into a structured controller.
"""

import os
import time
from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING

import numpy as np

from src.logging_config import get_logger
from src.logic.controllers.base_controller import (
    HardwareController,
    OperationResult,
)

if TYPE_CHECKING:
    import vxi11
    from dpimaincontrolunit.dpimaincontrolunit import DPIMainControlUnit
    from dpivoltageunit.dpivoltageunit import DPIVoltageUnit

logger = get_logger(__name__)

COLORS = ["C0", "C1", "C2"]


class VUController(HardwareController):
    """Controller for Voltage Unit hardware operations.

    Manages setup, test, calibration, coefficient, and guard workflows.

    Attributes:
        _vu: DPIVoltageUnit instance (injected by service).
        _mcu: DPIMainControlUnit instance (injected by service).
        _scope: vxi11.Instrument instance (injected by service).
        _coeffs: Current correction coefficients per channel.
        _vu_serial: VU serial number for artifact directory naming.
    """

    def __init__(
        self,
        vu: "DPIVoltageUnit",
        mcu: "DPIMainControlUnit",
        scope: "vxi11.Instrument",
        vu_serial: int = 0,
        artifact_dir: str | None = None,
    ) -> None:
        """Initialize VUController.

        Args:
            vu: Connected DPIVoltageUnit instance.
            mcu: Connected DPIMainControlUnit instance.
            scope: Connected vxi11 oscilloscope instance.
            vu_serial: VU serial number (used for artifact directory).
            artifact_dir: Base directory for saving calibration artifacts.
        """
        self._vu = vu
        self._mcu = mcu
        self._scope = scope
        self._vu_serial = vu_serial
        self._artifact_dir = artifact_dir or f"calibration_vu{vu_serial}"
        self._coeffs: dict[str, list[float]] = {
            "CH1": [1.0, 0.0],
            "CH2": [1.0, 0.0],
            "CH3": [1.0, 0.0],
        }

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def coeffs(self) -> dict[str, list[float]]:
        """Current correction coefficients for each channel."""
        return self._coeffs

    # =========================================================================
    # Scope Helpers
    # =========================================================================

    def _scope_setup_and_acquire(self, scope: "vxi11.Instrument") -> None:
        """Send SING and wait for AUTO-mode acquisition to complete.

        Mirrors setup_cal.py: ``scope.ask("SING;*OPC?")`` with default
        timeout — no custom timeout overrides.
        """
        scope.ask("SING;*OPC?")

    def _scope_wait_trigger(self, scope: "vxi11.Instrument") -> bool:
        """Wait for a NORM-mode triggered acquisition to complete.

        Mirrors setup_cal.py: ``scope.ask("*OPC?")`` with default timeout.
        Returns True if the scope triggered, False on timeout.
        """
        try:
            scope.ask("*OPC?")
            return True
        except Exception:
            print("  ⚠ Scope did not trigger — check probe connections")
            logger.warning("Scope NORM trigger timed out")
            self._scope_discard_link(scope)
            return False

    def _scope_discard_link(self, scope: "vxi11.Instrument") -> None:
        """Close the VXI-11 link and reopen a clean one.

        After a timed-out *OPC?, the scope's VXI11 link may hold stale
        state.  We close it, wait briefly for the scope to clean up, then
        open a fresh link with *RST + *CLS so the next test starts clean.
        """
        try:
            scope.close()
        except Exception:
            try:
                if scope.client is not None:
                    scope.client.close()
            except Exception:
                pass
        scope.link = None
        scope.client = None
        # Give the scope time to release the old link, then open a
        # fresh one and clear any pending error / acquisition state.
        time.sleep(0.5)
        try:
            scope.write("*RST;*CLS")
            scope.ask("*OPC?")
        except Exception:
            logger.warning("Scope recovery after discard failed")

    # =========================================================================
    # Setup Operations
    # =========================================================================

    def initialize_device(
        self,
        serial: int,
        processor_type: str = "746",
        connector_type: str = "BNC",
    ) -> OperationResult:
        """Initialize a new VU device after first flash.

        Args:
            serial: Device serial number (1-9999).
            processor_type: Processor type ("746").
            connector_type: Connector type ("BNC").

        Returns:
            OperationResult with success status and serial number.
        """
        try:
            self._vu.initNewDevice(
                serial=serial,
                processorType=processor_type,
                connectorType=connector_type,
            )
            logger.info("VU initialized: serial=%s", serial)
            return OperationResult(ok=True, serial=serial)
        except Exception as e:
            logger.error("VU initialization failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    # =========================================================================
    # Temperature
    # =========================================================================

    def read_temperature(self) -> OperationResult:
        """Read VU temperature sensor.

        Returns:
            OperationResult with temperature in data["temperature"].
        """
        try:
            temp = self._vu.get_temperature()
            logger.debug("VU temperature: %s", temp)
            return OperationResult(ok=True, data={"temperature": temp})
        except Exception as e:
            logger.error("VU temperature read failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    # =========================================================================
    # Autocalibration
    # =========================================================================

    def perform_autocalibration(self) -> OperationResult:
        """Run onboard autocalibration on all 3 channels.

        Mirrors the legacy autocal() function.

        Returns:
            OperationResult with updated coefficients.
        """
        try:
            print("── Onboard Autocalibration ──")
            for ch in ("CH1", "CH2", "CH3"):
                print(f"  Calibrating {ch}...")
                self._vu.performautocalibration(ch)
                print(f"  {ch} done.")
            # Re-read coefficients after calibration
            print("Reading back coefficients...")
            for ch in ("CH1", "CH2", "CH3"):
                self._coeffs[ch] = list(self._vu.get_correctionvalues(ch))
            print("Coefficients:")
            for ch in ("CH1", "CH2", "CH3"):
                k, d = self._coeffs[ch]
                print(f"  {ch}  k={k:.6f}  d={d:.6f}")
            logger.info("VU onboard autocalibration complete")
            return OperationResult(ok=True, data={"coeffs": self._coeffs})
        except Exception as e:
            logger.error("VU autocalibration failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    # =========================================================================
    # Coefficient Management
    # =========================================================================

    def read_coefficients(self) -> OperationResult:
        """Read correction coefficients from hardware.

        Returns:
            OperationResult with coefficients in data["coeffs"].
        """
        try:
            for ch in ("CH1", "CH2", "CH3"):
                self._coeffs[ch] = list(self._vu.get_correctionvalues(ch))
            logger.debug("VU coefficients read: %s", self._coeffs)
            return OperationResult(ok=True, data={"coeffs": self._coeffs})
        except Exception as e:
            logger.error("VU coefficient read failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def reset_coefficients(self, write_eeprom: bool = False) -> OperationResult:
        """Reset correction coefficients to defaults (k=1.0, d=0.0).

        By default only updates RAM so that EEPROM retains the previous
        calibration.  Pass ``write_eeprom=True`` to also persist the reset.

        Args:
            write_eeprom: If True, also write the reset values to EEPROM.

        Returns:
            OperationResult with reset coefficients.
        """
        try:
            for ch in ("CH1", "CH2", "CH3"):
                self._coeffs[ch] = [1.0, 0.0]
                k, d = self._coeffs[ch]
                zw = self._vu.voltageToRawWord(channel=ch, voltage=d)
                self._vu.set_correctionvalues(
                    channel=ch,
                    slope=k,
                    offset=d,
                    zeroword=zw,
                    writetoeeprom=write_eeprom,
                )
                logger.debug("VU %s coeffs reset: k=%s, d=%s", ch, k, d)
            return OperationResult(ok=True, data={"coeffs": self._coeffs})
        except Exception as e:
            logger.error("VU coefficient reset failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def write_coefficients(self) -> OperationResult:
        """Write current coefficients to EEPROM and verify by reading back.

        Mirrors the legacy write_coefficients() with wait_input=False.

        Returns:
            OperationResult with written coefficients.
        """
        try:
            for ch in ("CH1", "CH2", "CH3"):
                k, d = self._coeffs[ch]
                zw = self._vu.voltageToRawWord(channel=ch, voltage=d)
                self._vu.set_correctionvalues(
                    channel=ch,
                    slope=k,
                    offset=d,
                    zeroword=zw,
                    writetoeeprom=True,
                )
            # Verify by reading back
            mismatch = False
            for ch in ("CH1", "CH2", "CH3"):
                readback = list(self._vu.get_correctionvalues(ch))
                expected_k, expected_d = self._coeffs[ch]
                if abs(readback[0] - expected_k) > 1e-9 or abs(readback[1] - expected_d) > 1e-9:
                    print(
                        f"  {ch}  ⚠ EEPROM mismatch: wrote k={expected_k:.6f} d={expected_d:.6f}"
                        f"  read k={readback[0]:.6f} d={readback[1]:.6f}"
                    )
                    mismatch = True
            if mismatch:
                logger.warning("Coefficient EEPROM verification failed")
            return OperationResult(ok=not mismatch, data={"coeffs": self._coeffs})
        except Exception as e:
            logger.error("VU coefficient write failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    # =========================================================================
    # Guard Controls
    # =========================================================================

    def set_guard_signal(self) -> OperationResult:
        """Set output guard to signal mode.

        WARNING: Scope must not be connected when using signal mode.

        Returns:
            OperationResult with guard state.
        """
        try:
            self._vu.setOutputsGuardToSignal()
            logger.info("VU guard set to signal")
            return OperationResult(ok=True, data={"guard": "signal"})
        except Exception as e:
            logger.error("VU guard signal failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def set_guard_ground(self) -> OperationResult:
        """Set output guard to ground mode (safe default).

        Returns:
            OperationResult with guard state.
        """
        try:
            self._vu.setOutputsGuardToGND()
            logger.info("VU guard set to ground")
            return OperationResult(ok=True, data={"guard": "ground"})
        except Exception as e:
            logger.error("VU guard ground failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    # =========================================================================
    # Test Operations
    # =========================================================================

    def test_outputs(
        self,
        on_point_measured: Callable[[dict], None] | None = None,
    ) -> OperationResult:
        """Test output voltage accuracy across multiple setpoints.

        Measures scope channels at multiple voltages, computes error, adjusts
        offset coefficient, and saves a plot.

        Args:
            on_point_measured: Optional callback invoked after each voltage
                setpoint with a dict containing ``x``, ``y_ch1``, ``y_ch2``,
                ``y_ch3`` (error values in volts).

        Returns:
            OperationResult with ok status and artifacts list.
        """
        try:
            import matplotlib

            matplotlib.use("Agg")
            from matplotlib import pyplot as plt

            # Reload latest coefficients
            for ch in ("CH1", "CH2", "CH3"):
                self._coeffs[ch] = list(self._vu.get_correctionvalues(ch))

            scope = self._scope

            # Scope setup at 0.20 V/div — setOutputVoltage already accounts
            # for amplification, so ±0.75V setpoints produce ±0.75V output.
            scope.write("*RST")
            scope.write("CHAN:TYPE HRES")
            scope.write("ACQ:POIN 5000")
            scope.write("TIM:SCAL 1e-2")
            scope.write("CHAN1:SCAL 0.20")
            scope.write("CHAN2:SCAL 0.20")
            scope.write("CHAN3:SCAL 0.20")
            scope.write("FORM REAL")
            scope.write("FORM:BORD LSBF")
            scope.write("CHAN:DATA:POIN DMAX")
            scope.write("CHAN1:STAT ON")
            scope.write("CHAN2:STAT ON")
            scope.write("CHAN3:STAT ON")

            self._vu.setOutputsEnabled(0)
            print("── Output Voltage Test ──")
            print("Measuring scope offsets...")
            self._scope_setup_and_acquire(scope)
            offsets = [0.0, 0.0, 0.0]
            for channel in (1, 2, 3):
                off, _ = self._scope_get_data(channel)
                offsets[channel - 1] = np.mean(off)
                print(f"  CH{channel} offset: {offsets[channel - 1] * 1000:+.2f} mV")

            self._vu.setOutputsEnabled(1)
            print("Testing output voltages...")

            # Test at multiple voltages
            measured = [0, 0, 0]
            voltages = (-0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75)
            errors: list[list[float]] = [[], [], []]

            for voltage in voltages:
                self._vu.setOutputVoltage("all", (voltage, voltage, voltage))
                logger.info(f"Applied {voltage}V")
                self._scope_setup_and_acquire(scope)

                for channel in (1, 2, 3):
                    data, _t = self._scope_get_data(channel)
                    if voltage == 0:
                        measured[channel - 1] = np.mean(data) - offsets[channel - 1]
                    mean_val = float(np.mean(data))
                    corrected = mean_val - offsets[channel - 1] - voltage
                    # Detect scope clipping (±1V for 0.20 V/div scale)
                    clipping = abs(mean_val) > 0.95
                    err_mv = 1000 * corrected
                    ok_mark = "✓" if abs(err_mv) < 5 else "✗"
                    clip_warn = "  ⚠ CLIP" if clipping and voltage != 0 else ""
                    print(
                        f"  CH{channel} @ {voltage:+.2f}V  "
                        f"meas={mean_val:+.4f}V  err={err_mv:+.2f} mV  {ok_mark}{clip_warn}"
                    )
                    if clipping and voltage != 0:
                        logger.warning("CH%d clipping at %.4fV", channel, mean_val)
                    errors[channel - 1].append(corrected)
                    time.sleep(0.01)

                if on_point_measured is not None:
                    on_point_measured(
                        {
                            "x": voltage,
                            "y_ch1": errors[0][-1],
                            "y_ch2": errors[1][-1],
                            "y_ch3": errors[2][-1],
                        }
                    )

            # Check offset errors and adjust coefficients
            print("Offset check:")
            all_ok = True
            for channel in (1, 2, 3):
                offset_err = 1000 * measured[channel - 1]
                ok_mark = "✓" if abs(offset_err) < 2 else "✗"
                print(f"  CH{channel} offset error: {offset_err:+.2f} mV  {ok_mark}")
                if abs(offset_err) >= 2:
                    all_ok = False
                slope = self._coeffs[f"CH{channel}"][0]
                if abs(slope) > 1e-6:
                    offset_adj = measured[channel - 1] / slope
                    offset_adj = np.clip(offset_adj, -0.5, 0.5)
                    self._coeffs[f"CH{channel}"][1] -= offset_adj
                else:
                    print(f"  CH{channel}  ⚠ slope too small ({slope:.6f}), skipping")
                    all_ok = False

            # Save plot
            os.makedirs(self._artifact_dir, exist_ok=True)
            fig, ax = plt.subplots(figsize=(8, 5))
            for i, (ch, c) in enumerate(zip(("CH1", "CH2", "CH3"), COLORS)):
                ax.plot(voltages, [1000 * e for e in errors[i]], "x-", label=ch, c=c)
            ax.set_title(
                f"Output Voltage Error — VU {self._vu_serial}",
                fontsize=11, fontweight="bold",
            )
            ax.set_xlabel("Setpoint Voltage / V")
            ax.set_ylabel("Error / mV")
            ax.legend(loc="upper left")
            ax.grid(True, alpha=0.3)
            fig.tight_layout()
            fig.savefig(self._artifact_path("output"), dpi=150)
            plt.close(fig)

            # Build result before hardware reset so plot data is
            # preserved even if the reset commands fail.
            result = OperationResult(ok=all_ok, data={
                "artifacts": self._list_artifacts(),
                "plot": {
                    "type": "outputs",
                    "voltages": list(voltages),
                    "errors": [list(map(float, e)) for e in errors],
                },
            })

            # Reset outputs (best-effort — don't lose plot data)
            try:
                self._vu.setOutputVoltage("all", (0.0, 0.0, 0.0))
                self._vu.setOutputsEnabled(0)
            except Exception as e:
                logger.warning("Failed to reset VU outputs: %s", e)

            return result
        except Exception as e:
            print(f"  ✗ test_outputs failed: {e}")
            logger.error("VU test_outputs failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def test_ramp(
        self,
        on_waveform: Callable[[dict], None] | None = None,
    ) -> OperationResult:
        """Test voltage ramp linearity and slope accuracy.

        Generates a ramp signal, measures it with the scope, fits a linear model,
        and adjusts the slope coefficient.

        Args:
            on_waveform: Optional callback with waveform data per channel.

        Returns:
            OperationResult with ok status and artifacts list.
        """
        try:
            import matplotlib

            matplotlib.use("Agg")
            from matplotlib import pyplot as plt

            scale = []
            slopes = []
            flag_return = True

            # Reload latest coefficients and compute scales/slopes
            for _i, ch in enumerate(("CH1", "CH2", "CH3")):
                self._coeffs[ch] = list(self._vu.get_correctionvalues(ch))
                scale.append(abs(self._vu.get_Vout_Amplification(ch)))
                amp = self._vu.get_Vout_Amplification(ch)
                if ch == "CH1":
                    slopes.append(1 * 20 * amp)
                else:
                    slopes.append(20 * amp)

            print("── Ramp Linearity Test ──")
            print(f"Scope scales: CH1={scale[0]:.1f}  CH2={scale[1]:.1f}  CH3={scale[2]:.1f} V/div")
            print(f"Ramp slopes:  CH1={slopes[0]:.1f}  CH2={slopes[1]:.1f}  CH3={slopes[2]:.1f} V/s")

            scope = self._scope

            # Measure offsets
            scope.write("*RST")
            scope.write("CHAN:TYPE HRES")
            scope.write("ACQ:POIN 5000")
            scope.write("TIM:SCAL 1e-2")
            scope.write(f"CHAN1:SCAL {scale[0]}")
            scope.write(f"CHAN2:SCAL {scale[1]}")
            scope.write(f"CHAN3:SCAL {scale[2]}")
            scope.write("FORM REAL")
            scope.write("FORM:BORD LSBF")
            scope.write("CHAN:DATA:POIN DMAX")
            scope.write("CHAN1:STAT ON")
            scope.write("CHAN2:STAT ON")
            scope.write("CHAN3:STAT ON")

            self._vu.setOutputsEnabled(0)
            print("Measuring scope offsets...")
            self._scope_setup_and_acquire(scope)
            offsets = [0.0, 0.0, 0.0]
            for channel in (1, 2, 3):
                off, _ = self._scope_get_data(channel)
                offsets[channel - 1] = np.mean(off)
                print(f"  CH{channel} offset: {offsets[channel - 1] * 1000:+.2f} mV")

            self._vu.setOutputsEnabled(1)
            print("Generating ramp signal...")

            # Configure scope for ramp measurement
            scope.write("*RST")
            scope.write("CHAN:TYPE HRES")
            scope.write("ACQ:POIN 50000")
            scope.write("TIM:RANGE 500e-3")
            scope.write("TIM:POS 0.2")
            scope.write(f"CHAN1:SCAL {scale[0]}")
            scope.write(f"CHAN2:SCAL {scale[1]}")
            scope.write(f"CHAN3:SCAL {scale[2]}")
            scope.write("TRIG:A:MODE NORM")
            scope.write("TRIG:A:SOUR CH1")
            scope.write("TRIG:A:TYPE EDGE")
            scope.write("TRIG:A:EDGE:SLOPE NEG")
            trig_level = -0.5 * abs(slopes[0]) * 0.200
            scope.write(f"TRIG:A:LEVEL1:VAL {trig_level}")
            print(f"  Trigger level: {trig_level:+.2f} V  (NEG edge, CH1)")
            scope.write("FORM REAL")
            scope.write("FORM:BORD LSBF")
            scope.write("CHAN:DATA:POIN DMAX")
            scope.write("CHAN1:STAT ON")
            scope.write("CHAN2:STAT ON")
            scope.write("CHAN3:STAT ON")

            scope.ask("*OPC?")
            scope.write("SING")

            # Generate ramp output
            self._mcu.setVUSyncTimerFrequency(1e6)
            self._vu.setOutputsEnabled(1)
            time.sleep(0.1)
            self._vu.initTransientSignal(
                numperiods=1,
                settlingtime=2e-6,
                offsets=(0.0, 0.0, 0.0),
                repetitionstartindex=0,
            )
            length = 500
            time.sleep(0.1)

            for i in range(3):
                tin = np.arange(-250, 250) * 1000e-6
                din = tin * slopes[i]
                din[:50] = 0
                din[451:] = 0
                self._vu.writeVoltageTable(f"vch{i + 1}", data=din)

            self._vu.writeVoltageTable("sampling", data=[1] * length)
            self._vu.writeVoltageTable(
                "iteration",
                data=[np.uint64(1000.0)] * length,
            )

            for i in range(4):
                self._vu.writeVoltageTable(f"smubus{i + 1}", data=[255] * length)
            time.sleep(0.3)

            self._vu.startTransientSignal()
            print("Ramp started, acquiring...")
            time.sleep(0.3)
            self._vu.setOutputsEnabled(0)

            # Wait for trigger
            time.sleep(1)
            triggered = self._scope_wait_trigger(scope)

            if not triggered:
                print("  ⚠ No valid data — trigger did not fire")
                try:
                    self._vu.setOutputVoltage("all", (0.0, 0.0, 0.0))
                except Exception:
                    pass
                return OperationResult(
                    ok=False,
                    message="Trigger did not fire — check scope probe connections",
                )

            # Process data and plot
            waveforms = []
            fig, axs = plt.subplots(2, 1, sharex=True, figsize=(10, 6))
            for channel in range(3):
                head = scope.ask("CHAN1:DATA:HEAD?")
                scope.write(f"CHAN{channel + 1}:DATA?")
                raw = scope.read_raw()
                lead_digits = int(raw[1:2].decode("utf-8"))
                len_bytes = int(raw[2 : 2 + lead_digits].decode("utf-8"))
                data = np.frombuffer(
                    raw[lead_digits + 2 : lead_digits + 2 + len_bytes],
                    dtype=np.single,
                )
                t0 = float(head.split(",")[0])
                t1 = float(head.split(",")[1])
                t = np.linspace(t0, t1, len(data))

                # Segment and process
                data = data.copy()
                data -= offsets[channel]
                for idx in range(490):
                    data[idx - 10 : idx + 10] = np.nan

                tl = t[(t > -45e-3) * (t < -5e-3)]
                datal = data[(t > -45e-3) * (t < -5e-3)]
                tm = t[(t > 5e-3) * (t < 395e-3)]
                datam = data[(t > 5e-3) * (t < 395e-3)]
                tr = t[(t > 405e-3) * (t < 445e-3)]
                datar = data[(t > 405e-3) * (t < 445e-3)]

                # Fit slope — filter NaN before polyfit
                valid = ~(np.isnan(tm) | np.isnan(datam))
                tm_clean = tm[valid]
                datam_clean = datam[valid]

                fit_ok = False
                k, d_fit = 0.0, 0.0

                if len(tm_clean) < 10:
                    print(f"  CH{channel + 1}  ⚠ insufficient data ({len(tm_clean)} pts), skipping")
                    flag_return = False
                elif np.ptp(datam_clean) < 0.5:
                    print(f"  CH{channel + 1}  ⚠ signal too flat (pk-pk={np.ptp(datam_clean):.3f}V), skipping")
                    flag_return = False
                else:
                    k, d_fit = np.polyfit(tm_clean, datam_clean, deg=1)

                    # Sanity check: slope must be finite and not near zero
                    if not np.isfinite(k) or abs(k) < abs(slopes[channel]) * 0.001:
                        print(f"  CH{channel + 1}  ⚠ slope {k:.3f} V/s unreliable, skipping")
                        logger.warning("CH%d ramp: slope %.3f unreliable, skipping", channel + 1, k)
                        flag_return = False
                    else:
                        kre = (k - slopes[channel]) / slopes[channel]
                        ok_mark = "✓" if abs(100 * kre) < 0.1 else "✗"
                        print(
                            f"  CH{channel + 1}  slope={k:.1f} V/s  "
                            f"(expected {slopes[channel]:.1f})  "
                            f"err={kre * 100:+.2f}%  {ok_mark}"
                        )
                        if abs(100 * kre) >= 0.1:
                            flag_return = False

                        # Adjust coefficient (bounded to prevent divergence)
                        if np.sign(k) != np.sign(slopes[channel]):
                            print(f"         ⚠ slope sign mismatch")
                        ratio = slopes[channel] / k
                        if abs(ratio) > 5.0:
                            print(f"         ⚠ correction ratio {ratio:.2f} clamped to ±5.0")
                            ratio = np.clip(ratio, -5.0, 5.0)
                        self._coeffs[f"CH{channel + 1}"][0] *= ratio
                        fit_ok = True

                # Compute ideal ramp for this channel
                ideal = (t - 0.2) * slopes[channel]
                ideal[t < 0] = 0.0
                ideal[t > 0.4] = 0.0

                # Always collect waveform and plot (even if fit failed)
                waveforms.append({
                    "series": f"CH{channel + 1}",
                    "x": t.tolist(),
                    "y": data.tolist(),
                })
                waveforms.append({
                    "series": f"CH{channel + 1} (ideal)",
                    "x": t.tolist(),
                    "y": ideal.tolist(),
                    "linestyle": "--",
                    "alpha": 0.5,
                    "color": COLORS[channel],
                })

                if on_waveform is not None:
                    on_waveform({
                        "type": "ramp",
                        "series": f"CH{channel + 1}",
                        "x": t.tolist(),
                        "y": data.tolist(),
                    })
                    on_waveform({
                        "type": "ramp",
                        "series": f"CH{channel + 1} (ideal)",
                        "x": t.tolist(),
                        "y": ideal.tolist(),
                        "linestyle": "--",
                        "alpha": 0.5,
                        "color": COLORS[channel],
                    })

                # Plot
                c = COLORS[channel]
                axs[0].plot(t, data, label=f"CH{channel + 1}", c=c)
                if fit_ok:
                    axs[0].plot(tm, tm * k + d_fit, "k:")
                axs[0].plot(t, ideal, ls="-", c=c, alpha=0.5)

                idealm = (tm - 0.2) * slopes[channel]
                axs[1].plot(tl, 1000 * (datal - 0), c=c)
                axs[1].plot(tm, 1000 * (datam - idealm), c=c)
                axs[1].plot(tr, 1000 * (datar - 0), c=c)

            print("Updated coefficients:")
            for ch in ("CH1", "CH2", "CH3"):
                k_c, d_c = self._coeffs[ch]
                print(f"  {ch}  k={k_c:.6f}  d={d_c:.6f}")

            os.makedirs(self._artifact_dir, exist_ok=True)
            axs[0].set_title(
                f"Ramp Linearity Test — VU {self._vu_serial}",
                fontsize=11, fontweight="bold",
            )
            axs[1].set_xlabel("Time / s")
            axs[0].set_ylabel("Signal / V")
            axs[1].set_ylabel("Error / mV")
            axs[0].legend()
            axs[0].grid(True, alpha=0.3)
            axs[1].grid(True, alpha=0.3)
            fig.tight_layout()
            fig.savefig(self._artifact_path("ramp"), dpi=150)
            plt.close(fig)

            # Build result before hardware reset so plot data is
            # preserved even if the reset commands fail.
            result = OperationResult(ok=flag_return, data={
                "artifacts": self._list_artifacts(),
                "plot": {"type": "ramp", "waveforms": waveforms},
            })

            try:
                self._vu.setOutputVoltage("all", (0.0, 0.0, 0.0))
            except Exception as e:
                logger.warning("Failed to reset VU outputs: %s", e)

            return result
        except Exception as e:
            print(f"  ✗ test_ramp failed: {e}")
            logger.error("VU test_ramp failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def test_transient(
        self,
        on_waveform: Callable[[dict], None] | None = None,
    ) -> OperationResult:
        """Test transient response with MSM signal.

        Generates a step signal, measures timing and overshoot, and saves a plot.

        Args:
            on_waveform: Optional callback with waveform data per channel.

        Returns:
            OperationResult with ok status and artifacts list.
        """
        try:
            import matplotlib

            matplotlib.use("Agg")
            from dpi.configuration import DPIConfiguration
            from matplotlib import pyplot as plt

            print("── Transient Step Response ──")
            dac_bits = self._vu.get_DAC_bits()
            amplitude = 1
            timestep = 5e-6

            scope = self._scope

            if dac_bits == 20:
                timestep = 20e-6

            v_scale = 0.5 * amplitude
            timescale = timestep / 5.0

            scope.write("*RST")
            scope.write("CHAN:TYPE HRES")
            scope.write("ACQ:POIN 5000")
            scope.write(f"TIM:SCAL {timescale}")
            scope.write(f"CHAN1:SCAL {v_scale}")
            scope.write(f"CHAN2:SCAL {v_scale}")
            scope.write(f"CHAN3:SCAL {v_scale}")
            scope.write("TRIG:A:MODE NORM")
            scope.write("TRIG:A:SOUR CH1")
            scope.write("TRIG:A:TYPE EDGE")
            scope.write("TRIG:A:EDGE:SLOPE POS")
            scope.write("TRIG:A:LEVEL1:VAL 0.0")
            print(f"  Trigger level: 0.000 V  (POS edge, CH1)")
            scope.write("FORM REAL")
            scope.write("FORM:BORD LSBF")
            scope.write("CHAN:DATA:POIN DMAX")
            scope.write("CHAN1:STAT ON")
            scope.write("CHAN2:STAT ON")
            scope.write("CHAN3:STAT ON")

            scope.ask("*OPC?")
            scope.write("SING")

            # Generate MSM signal
            self._mcu.setVUSyncTimerFrequency(1e6)
            self._vu.setOutputsEnabled(1)
            time.sleep(0.3)

            parameters = DPIConfiguration().model_dump(by_alias=True)
            parameters["msm"]["dc"]["tstress"] = timestep
            parameters["msm"]["dc"]["trecovery"] = timestep

            for i in range(3):
                parameters["vu.1"][f"ch{i + 1}"]["msm"]["dc"]["vstress"] = -1.0 * amplitude
                parameters["vu.1"][f"ch{i + 1}"]["msm"]["dc"]["vrecovery"] = amplitude
                parameters["vu.1"][f"ch{i + 1}"]["msm"]["dc"]["vremain"] = 0.0

            for i in range(4):
                parameters[f"smu.bus_{i + 1}"]["msm"]["dc"]["__stresscurrentrange_index"] = 255
                parameters[f"smu.bus_{i + 1}"]["msm"]["dc"]["__recoverycurrentrange_index"] = 255

            parameters["smu.all"]["msm"]["signal_to_record"] = "recovery"
            self._vu.configureMSMSignal("dc", "vu.1", parameters=parameters)
            time.sleep(0.3)
            self._vu.startMSMSignal()
            logger.info(
                f"Applying msm signal, stress:{timestep * 1e6}us,-1V,"
                f" recovery:{timestep * 1e6}us,1V"
            )
            time.sleep(0.3)
            self._vu.setOutputsEnabled(0)

            triggered = self._scope_wait_trigger(scope)

            if not triggered:
                print("  ⚠ No valid data — trigger did not fire")
                return OperationResult(
                    ok=False,
                    message="Trigger did not fire — check scope probe connections",
                )

            # Process data and plot
            waveforms = []
            fig_t, ax_t = plt.subplots(figsize=(8, 5))
            for channel in range(3):
                data, t = self._scope_get_data(channel + 1)

                # Collect waveform for result
                waveforms.append({
                    "series": f"CH{channel + 1}",
                    "x": t.tolist(),
                    "y": data.tolist(),
                })

                # Emit waveform for live plot
                if on_waveform is not None:
                    on_waveform({
                        "type": "transient",
                        "series": f"CH{channel + 1}",
                        "x": t.tolist(),
                        "y": data.tolist(),
                    })

                c = COLORS[channel]
                ax_t.plot(t, data, label=f"CH{channel + 1}", c=c)

                # Timing analysis
                tl = t[t < -3e-6]
                datal = data[t < -3e-6]
                tr_seg = t[t > 3e-6]
                datar = data[t > 3e-6]
                mtl = tl[np.argmin(abs(datal - (-0.5)))]
                mtm = 0.0
                mtr = tr_seg[np.argmin(abs(datar - 0.5))]
                ax_t.plot([mtl, mtm, mtr], [-0.5, 0.0, 0.5], marker="x", ls="none", c=c)

                stress_time = 1e6 * (mtm - mtl)
                recovery_time = 1e6 * (mtr - mtm)
                el = (mtm - mtl) - 5e-6
                ok_s = "✓" if abs(el) < 0.5e-6 else "✗"
                er = (mtr - mtm) - 5e-6
                ok_r = "✓" if abs(er) < 0.5e-6 else "✗"
                print(
                    f"  CH{channel + 1}  stress={stress_time:.2f}µs (err={el*1e6:+.2f}µs) {ok_s}  "
                    f"recovery={recovery_time:.2f}µs (err={er*1e6:+.2f}µs) {ok_r}"
                )

                # Overshoot analysis
                osl = min(data[t < -4e-6]) - (-1)
                osm = max(data[abs(t) < 1e-6]) - 1
                osr = min(data[t > 4e-6])
                rosl = osl / -1
                rosm = osm / 2
                rosr = osr / -1
                print(
                    f"         overshoot: "
                    f"left={1000*osl:+.1f}mV ({100*rosl:.1f}%)  "
                    f"mid={1000*osm:+.1f}mV ({100*rosm:.1f}%)  "
                    f"right={1000*osr:+.1f}mV ({100*rosr:.1f}%)"
                )

            # Plot ideal and save
            os.makedirs(self._artifact_dir, exist_ok=True)
            ideal = t * 0
            ideal[t < 0] = -1.0
            ideal[t >= 0] = 1.0
            ideal[t < -5e-6] = 0
            ideal[t > 5e-6] = 0
            ax_t.plot(t, ideal, ls="--", c="k", alpha=0.75, label="Ideal")
            ax_t.set_title(
                f"Transient Step Response — VU {self._vu_serial}",
                fontsize=11, fontweight="bold",
            )
            ax_t.set_xlabel("Time / s")
            ax_t.set_ylabel("Signal / V")
            ax_t.legend()
            ax_t.grid(True, alpha=0.3)
            fig_t.tight_layout()
            fig_t.savefig(self._artifact_path("transient"), dpi=150)
            plt.close(fig_t)

            return OperationResult(ok=True, data={
                "artifacts": self._list_artifacts(),
                "plot": {"type": "transient", "waveforms": waveforms},
            })
        except Exception as e:
            print(f"  ✗ test_transient failed: {e}")
            logger.error("VU test_transient failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def test_all(
        self,
        on_point_measured: Callable[[dict], None] | None = None,
        on_waveform: Callable[[dict], None] | None = None,
    ) -> OperationResult:
        """Run all tests sequentially (outputs, ramp, transient).

        Args:
            on_point_measured: Optional callback forwarded to test_outputs.
            on_waveform: Optional callback forwarded to test_ramp/test_transient.

        Returns:
            OperationResult with combined ok status and artifacts.
        """
        r1 = self.test_outputs(on_point_measured=on_point_measured)
        r2 = self.test_ramp(on_waveform=on_waveform)
        r3 = self.test_transient(on_waveform=on_waveform)
        all_ok = r1.ok and r2.ok and r3.ok
        # Collect plot data from the last test that has waveform data
        plots = []
        for r in (r1, r2, r3):
            if r.data and "plot" in r.data:
                plots.append(r.data["plot"])
        return OperationResult(ok=all_ok, data={
            "artifacts": self._list_artifacts(),
            "plots": plots,
        })

    # =========================================================================
    # Python Auto-Calibration (iterative)
    # =========================================================================

    def auto_calibrate(
        self,
        max_iterations: int = 10,
        on_iteration: Callable[[dict], None] | None = None,
        on_point_measured: Callable[[dict], None] | None = None,
        on_waveform: Callable[[dict], None] | None = None,
    ) -> OperationResult:
        """Run iterative Python-based autocalibration.

        Mirrors the legacy auto_calibrate() function. Alternates between
        test_ramp and test_outputs for up to *max_iterations* iterations,
        adjusting coefficients until convergence.

        Args:
            max_iterations: Maximum number of calibration iterations.
            on_iteration: Optional callback invoked after each iteration with
                a dict containing ``iteration``, ``converged``, and ``coeffs``.
            on_point_measured: Optional callback forwarded to
                :meth:`test_outputs` for per-setpoint live data.

        Returns:
            OperationResult with ok status, coefficients, and artifacts.
        """
        try:
            self.reset_coefficients()
            calibration_finished = False

            for iteration in range(max_iterations):
                print(f"\n── Iteration {iteration + 1}/{max_iterations} ──")

                calibration_finished = self.test_ramp(on_waveform=on_waveform).ok
                self.write_coefficients()

                # Emit iteration marker BEFORE test_outputs so the GUI
                # clears the plot before new data points arrive.
                if on_iteration is not None:
                    on_iteration(
                        {
                            "iteration": iteration,
                            "converged": False,
                            "coeffs": {k: list(v) for k, v in self._coeffs.items()},
                        }
                    )

                calibration_finished = (
                    self.test_outputs(on_point_measured=on_point_measured).ok
                    and calibration_finished
                )
                self.write_coefficients()

                print("Coefficients:")
                for ch in ("CH1", "CH2", "CH3"):
                    k, d = self._coeffs[ch]
                    print(f"  {ch}  k={k:.6f}  d={d:.6f}")

                if calibration_finished:
                    print(f"\n✓ Converged at iteration {iteration + 1}")
                    break
                else:
                    print("Tolerance not met, continuing...")

            print("\n── Final Verification ──")
            if on_iteration is not None:
                on_iteration({"iteration": "final_transient", "converged": True, "coeffs": {
                    k: list(v) for k, v in self._coeffs.items()
                }})
            self.test_transient(on_waveform=on_waveform)
            if on_iteration is not None:
                on_iteration({"iteration": "final_outputs", "converged": True, "coeffs": {
                    k: list(v) for k, v in self._coeffs.items()
                }})
            final_outputs = self.test_outputs(on_point_measured=on_point_measured)
            if on_iteration is not None:
                on_iteration({"iteration": "final_ramp", "converged": True, "coeffs": {
                    k: list(v) for k, v in self._coeffs.items()
                }})
            final_ramp = self.test_ramp(on_waveform=on_waveform)

            plots = []
            if final_outputs.data and "plot" in final_outputs.data:
                plots.append(final_outputs.data["plot"])
            if final_ramp.data and "plot" in final_ramp.data:
                plots.append(final_ramp.data["plot"])
            return OperationResult(
                ok=True,
                data={
                    "coeffs": self._coeffs,
                    "artifacts": self._list_artifacts(),
                    "plot": plots[0] if len(plots) == 1 else None,
                    "plots": plots if len(plots) > 1 else None,
                },
            )
        except Exception as e:
            logger.error("VU auto_calibrate failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    # =========================================================================
    # Private Helpers
    # =========================================================================

    def _scope_get_data(self, channel: int) -> tuple[np.ndarray, np.ndarray]:
        """Read waveform data from a scope channel.

        Args:
            channel: Scope channel number (1-3).

        Returns:
            Tuple of (voltage data array, time array).
        """
        head = self._scope.ask("CHAN1:DATA:HEAD?")
        self._scope.write(f"CHAN{channel}:DATA?")
        raw = self._scope.read_raw()
        lead_digits = int(raw[1:2].decode("utf-8"))
        len_bytes = int(raw[2 : 2 + lead_digits].decode("utf-8"))
        data = np.frombuffer(
            raw[lead_digits + 2 : lead_digits + 2 + len_bytes],
            dtype=np.single,
        )
        t0 = float(head.split(",")[0])
        t1 = float(head.split(",")[1])
        t = np.linspace(t0, t1, len(data))
        return data, t

    def _artifact_path(self, prefix: str) -> str:
        """Generate a timestamped artifact file path.

        Args:
            prefix: File prefix (e.g. "output", "ramp", "transient").

        Returns:
            Path like ``calibration_vu2503/output_20260307_131042.png``.
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self._artifact_dir, f"{prefix}_{ts}.png")

    def _list_artifacts(self) -> list[str]:
        """List all artifact files in the artifact directory.

        Returns:
            List of absolute file paths to artifacts.
        """
        if not os.path.isdir(self._artifact_dir):
            return []
        return [
            os.path.join(self._artifact_dir, f)
            for f in os.listdir(self._artifact_dir)
            if os.path.isfile(os.path.join(self._artifact_dir, f))
        ]
