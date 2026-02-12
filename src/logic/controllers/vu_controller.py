"""Voltage Unit controller for hardware operations.

This controller encapsulates all VU hardware workflows including setup, test,
calibration, coefficient management, and guard operations. Ports the logic from
the legacy setup_cal.py script into a structured controller.
"""

import os
import time
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
            for ch in ("CH1", "CH2", "CH3"):
                self._vu.performautocalibration(ch)
            # Re-read coefficients after calibration
            for ch in ("CH1", "CH2", "CH3"):
                self._coeffs[ch] = list(self._vu.get_correctionvalues(ch))
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

    def reset_coefficients(self) -> OperationResult:
        """Reset correction coefficients to defaults (k=1.0, d=0.0) in RAM.

        Mirrors the legacy reset_coefficients() with wait_input=False.

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
                    writetoeeprom=True,
                )
                logger.debug("VU %s coeffs reset: k=%s, d=%s", ch, k, d)
            return OperationResult(ok=True, data={"coeffs": self._coeffs})
        except Exception as e:
            logger.error("VU coefficient reset failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def write_coefficients(self) -> OperationResult:
        """Write current coefficients to EEPROM.

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
                logger.info("VU %s coeffs written: k=%s, d=%s", ch, k, d)
            return OperationResult(ok=True, data={"coeffs": self._coeffs})
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

    def test_outputs(self) -> OperationResult:
        """Test output voltage accuracy across multiple setpoints.

        Measures scope channels at multiple voltages, computes error, adjusts
        offset coefficient, and saves a plot.

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

            # Measure offsets with outputs disabled
            self._vu.setOutputsEnabled(0)
            logger.info("Disable VU Outputs")
            scope.ask("SING;*OPC?")
            offsets = [0.0, 0.0, 0.0]
            for channel in (1, 2, 3):
                off, _ = self._scope_get_data(channel)
                offsets[channel - 1] = np.mean(off)
                logger.info(f"Scope Channel{channel} offset: {offsets[channel - 1] * 1000}mV")

            self._vu.setOutputsEnabled(1)
            logger.info("Enable VU Outputs")

            # Test at multiple voltages
            measured = [0, 0, 0]
            voltages = (-0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75)
            errors: list[list[float]] = [[], [], []]

            for voltage in voltages:
                self._vu.setOutputVoltage("all", (voltage, voltage, voltage))
                logger.info(f"Applied {voltage}V")
                scope.ask("SING;*OPC?")

                for channel in (1, 2, 3):
                    data, _t = self._scope_get_data(channel)
                    if voltage == 0:
                        measured[channel - 1] = np.mean(data) - offsets[channel - 1]
                    corrected = np.mean(data) - offsets[channel - 1] - voltage
                    if abs(1000 * corrected) < 5:
                        logger.info(
                            f"  Channel {channel}: measured {np.mean(data):.4f}V"
                            f"     error corrected {corrected:.6f}V ✓"
                        )
                    else:
                        logger.warning(
                            f"  Channel {channel}: measured {np.mean(data):.4f}V"
                            f"     error corrected {corrected:.6f}V ✗"
                        )
                    errors[channel - 1].append(corrected)
                    time.sleep(0.01)

            # Check offset errors and adjust coefficients
            all_ok = True
            for channel in (1, 2, 3):
                offset_err = 1000 * measured[channel - 1]
                logger.info(f"Channel {channel} offset error: {offset_err:.2f}mV")
                if abs(offset_err) < 2:
                    logger.info("  error within 2mV ✓")
                else:
                    logger.warning("  error larger than 2mV! ✗")
                    all_ok = False
                self._coeffs[f"CH{channel}"][1] -= (
                    measured[channel - 1] / self._coeffs[f"CH{channel}"][0]
                )

            # Save plot
            os.makedirs(self._artifact_dir, exist_ok=True)
            plt.plot(voltages, errors[0], "x-", label="CH1")
            plt.plot(voltages, errors[1], "x-", label="CH2")
            plt.plot(voltages, errors[2], "x-", label="CH3")
            plt.legend(loc="upper left")
            plt.savefig(f"{self._artifact_dir}/output.png")
            plt.close()

            # Reset outputs
            self._vu.setOutputVoltage("all", (0.0, 0.0, 0.0))
            self._vu.setOutputsEnabled(0)

            return OperationResult(ok=all_ok, data={"artifacts": self._list_artifacts()})
        except Exception as e:
            logger.error("VU test_outputs failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def test_ramp(self) -> OperationResult:
        """Test voltage ramp linearity and slope accuracy.

        Generates a ramp signal, measures it with the scope, fits a linear model,
        and adjusts the slope coefficient.

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
                    slopes.append(-1 * 20 * amp)
                else:
                    slopes.append(20 * amp)

            logger.info(f"Scale {scale}")
            logger.info(f"Slopes {slopes}")

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
            logger.info("Disable VU Outputs")
            scope.ask("SING;*OPC?")
            offsets = [0.0, 0.0, 0.0]
            for channel in (1, 2, 3):
                off, _ = self._scope_get_data(channel)
                offsets[channel - 1] = np.mean(off)
                logger.info(f"Scope Channel{channel} offset: {offsets[channel - 1] * 1000}mV")

            self._vu.setOutputsEnabled(1)
            logger.info("Enable VU Outputs")

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
            scope.write(f"TRIG:A:LEVEL1:VAL {-3.95 * scale[0]}")
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
            logger.info(f"Setting kch1={slopes[0]}V/s, kch2={slopes[1]}V/s, kch3={slopes[2]}V/s")
            time.sleep(0.3)
            self._vu.setOutputsEnabled(0)

            # Wait and acquire
            time.sleep(1)
            scope.ask("*OPC?")

            # Process data and plot
            fig, axs = plt.subplots(2, 1, sharex=True)
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

                # Fit slope
                k, d = np.polyfit(tm, datam, deg=1)
                logger.info(f"  Channel{channel + 1}: k={k:.3f}V/s")

                kre = (k - slopes[channel]) / slopes[channel]
                logger.info(f"    slope relative error: {kre * 100:.2f}%")
                if abs(100 * kre) < 0.1:
                    logger.info("    error within 0.1% ✓")
                else:
                    logger.warning("    error larger than 0.1%! ✗")
                    flag_return = False

                # Adjust coefficient
                self._coeffs[f"CH{channel + 1}"][0] *= slopes[channel] / k

                # Plot
                c = COLORS[channel]
                axs[0].plot(t, data, label=f"CH{channel + 1}", c=c)
                axs[0].plot(tm, tm * k + d, "k:")
                ideal = (t - 0.2) * slopes[channel]
                ideal[t < 0] = 0.0
                ideal[t > 0.4] = 0.0
                axs[0].plot(t, ideal, ls="-", c=c, alpha=0.5)

                idealm = (tm - 0.2) * slopes[channel]
                axs[1].plot(tl, 1000 * (datal - 0), c=c)
                axs[1].plot(tm, 1000 * (datam - idealm), c=c)
                axs[1].plot(tr, 1000 * (datar - 0), c=c)

            os.makedirs(self._artifact_dir, exist_ok=True)
            axs[1].set_xlabel("t / s")
            axs[0].set_ylabel("Signal / V")
            axs[1].set_ylabel("Error / mV")
            axs[0].legend()
            axs[0].grid()
            axs[1].grid()
            plt.savefig(f"{self._artifact_dir}/ramp.png")
            plt.close()

            self._vu.setOutputVoltage("all", (0.0, 0.0, 0.0))

            return OperationResult(ok=flag_return, data={"artifacts": self._list_artifacts()})
        except Exception as e:
            logger.error("VU test_ramp failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def test_transient(self) -> OperationResult:
        """Test transient response with MSM signal.

        Generates a step signal, measures timing and overshoot, and saves a plot.

        Returns:
            OperationResult with ok status and artifacts list.
        """
        try:
            import matplotlib

            matplotlib.use("Agg")
            from dpi.configuration import DPIConfiguration
            from matplotlib import pyplot as plt

            dac_bits = self._vu.get_DAC_bits()
            amplitude = 1
            timestep = 5e-6

            scope = self._scope
            scope.write("*RST")
            scope.write("CHAN:TYPE HRES")
            scope.write("ACQ:POIN 5000")

            if dac_bits == 20:
                timestep = 20e-6

            v_scale = 0.5 * amplitude
            timescale = timestep / 5.0

            scope.write(f"TIM:SCAL {timescale}")
            scope.write(f"CHAN1:SCAL {v_scale}")
            scope.write(f"CHAN2:SCAL {v_scale}")
            scope.write(f"CHAN3:SCAL {v_scale}")
            scope.write("TRIG:A:MODE NORM")
            scope.write("TRIG:A:SOUR CH1")
            scope.write("TRIG:A:TYPE EDGE")
            scope.write("TRIG:A:EDGE:SLOPE POS")
            scope.write("TRIG:A:LEVEL1:VAL 0.0")
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

            scope.ask("*OPC?")

            # Process data and plot
            for channel in range(3):
                data, t = self._scope_get_data(channel + 1)
                c = COLORS[channel]
                plt.plot(t, data, label=f"CH{channel + 1}", c=c)

                # Timing analysis
                tl = t[t < -3e-6]
                datal = data[t < -3e-6]
                tr_seg = t[t > 3e-6]
                datar = data[t > 3e-6]
                mtl = tl[np.argmin(abs(datal - (-0.5)))]
                mtm = 0.0
                mtr = tr_seg[np.argmin(abs(datar - 0.5))]
                plt.plot([mtl, mtm, mtr], [-0.5, 0.0, 0.5], marker="x", ls="none", c=c)

                stress_time = 1e6 * (mtm - mtl)
                recovery_time = 1e6 * (mtr - mtm)
                logger.info(f"  Channel{channel + 1} Stress time: {stress_time:.2f}us")
                el = (mtm - mtl) - 5e-6
                if abs(el) < 0.5e-6:
                    logger.info("    error within 0.5us ✓")
                else:
                    logger.warning("    error larger than 0.5us! ✗")

                logger.info(f"  Channel{channel + 1} Recovery time: {recovery_time:.2f}us")
                er = (mtr - mtm) - 5e-6
                if abs(er) < 0.5e-6:
                    logger.info("    error within 0.5us ✓")
                else:
                    logger.warning("    error larger than 0.5us! ✗")

                # Overshoot analysis
                osl = min(data[t < -4e-6]) - (-1)
                osm = max(data[abs(t) < 1e-6]) - 1
                osr = min(data[t > 4e-6])
                rosl = osl / -1
                rosm = osm / 2
                rosr = osr / -1
                for os_val, ros, txt in (
                    (osl, rosl, "left"),
                    (osm, rosm, "mid"),
                    (osr, rosr, "right"),
                ):
                    logger.info(
                        f"  Channel{channel + 1} Overshoot {txt}:"
                        f" {1000 * os_val:.2f}mV, {100 * ros:.2f}%"
                    )

            # Plot ideal and save
            os.makedirs(self._artifact_dir, exist_ok=True)
            ideal = t * 0
            ideal[t < 0] = -1.0
            ideal[t >= 0] = 1.0
            ideal[t < -5e-6] = 0
            ideal[t > 5e-6] = 0
            plt.plot(t, ideal, ls="--", c="k", alpha=0.75)
            plt.xlabel("t / s")
            plt.ylabel("Signal / V")
            plt.legend()
            plt.grid()
            plt.savefig(f"{self._artifact_dir}/transient.png")
            plt.close()

            return OperationResult(ok=True, data={"artifacts": self._list_artifacts()})
        except Exception as e:
            logger.error("VU test_transient failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def test_all(self) -> OperationResult:
        """Run all tests sequentially (outputs, ramp, transient).

        Returns:
            OperationResult with combined ok status and artifacts.
        """
        r1 = self.test_outputs()
        r2 = self.test_ramp()
        r3 = self.test_transient()
        all_ok = r1.ok and r2.ok and r3.ok
        return OperationResult(ok=all_ok, data={"artifacts": self._list_artifacts()})

    # =========================================================================
    # Python Auto-Calibration (iterative)
    # =========================================================================

    def auto_calibrate(self) -> OperationResult:
        """Run iterative Python-based autocalibration.

        Mirrors the legacy auto_calibrate() function. Alternates between
        test_ramp and test_outputs for up to 10 iterations, adjusting
        coefficients until convergence.

        Returns:
            OperationResult with ok status, coefficients, and artifacts.
        """
        try:
            self.reset_coefficients()
            calibration_finished = False

            for iteration in range(10):
                logger.info(f"\nCalibration iteration: {iteration}")
                calibration_finished = self.test_ramp().ok
                self.write_coefficients()
                calibration_finished = self.test_outputs().ok and calibration_finished
                self.write_coefficients()

                if calibration_finished:
                    logger.info(f"\nCalibration finished at Iteration {iteration}")
                    break

            self.test_transient()
            self.test_outputs()
            self.test_ramp()

            return OperationResult(
                ok=True,
                data={"coeffs": self._coeffs, "artifacts": self._list_artifacts()},
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
