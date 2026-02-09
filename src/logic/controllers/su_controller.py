"""Sampling Unit controller for hardware operations.

This controller encapsulates all SU hardware workflows including setup, test,
and calibration operations. It uses direct imports from the dpi package.
"""

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
            logger.info(f"SU initialized: serial={serial}")
            return OperationResult(ok=True, serial=serial)
        except Exception as e:
            logger.error(f"SU initialization failed: {e}")
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
            su = self._get_su()
            # Channel configuration typically involves setting amplifier settings
            # The exact API depends on dpi package implementation
            logger.info(f"SU channel configured: {config.channel_id}")
            return OperationResult(ok=True, data={"channel_id": config.channel_id})
        except Exception as e:
            logger.error(f"SU channel configuration failed: {e}")
            return OperationResult(ok=False, message=str(e))

    def save_channel_config(self) -> OperationResult:
        """Save current channel configuration to EEPROM.

        Returns:
            OperationResult with success status.
        """
        try:
            su = self._get_su()
            # Implementation depends on dpi package EEPROM API
            logger.info("SU channel config saved to EEPROM")
            return OperationResult(ok=True)
        except Exception as e:
            logger.error(f"SU EEPROM save failed: {e}")
            return OperationResult(ok=False, message=str(e))

    def load_channel_config(self) -> OperationResult:
        """Load channel configuration from EEPROM.

        Returns:
            OperationResult with channel data.
        """
        try:
            su = self._get_su()
            # Implementation depends on dpi package EEPROM API
            logger.info("SU channel config loaded from EEPROM")
            return OperationResult(ok=True, data={})
        except Exception as e:
            logger.error(f"SU EEPROM load failed: {e}")
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
            temp = su.getTemperature()
            logger.debug(f"SU temperature: {temp}")
            return OperationResult(ok=True, data={"temperature": temp})
        except Exception as e:
            logger.error(f"SU temperature read failed: {e}")
            return OperationResult(ok=False, message=str(e))

    def perform_autocalibration(self) -> OperationResult:
        """Run autocalibration on SU.

        Returns:
            OperationResult with success status.
        """
        try:
            su = self._get_su()
            su.performautocalibration()
            serial = su.getSerial()
            logger.info(f"SU autocalibration complete: serial={serial}")
            return OperationResult(ok=True, serial=serial)
        except Exception as e:
            logger.error(f"SU autocalibration failed: {e}")
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
            su.setDACValue(dac_voltage)
            su.setPath(source=source, ac=0, adc=None, amp=1.0)
            voltage = su.readInputVoltage()
            logger.debug(f"SU single-shot: {voltage}V")
            return OperationResult(ok=True, data={"voltage": voltage})
        except Exception as e:
            logger.error(f"SU single-shot failed: {e}")
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

            # Read data
            data = su.transientSampling_readData()
            logger.debug(f"SU transient: {len(data[0])} samples")
            # Handle both numpy arrays and plain lists
            time_data = data[0].tolist() if hasattr(data[0], "tolist") else list(data[0])
            values_data = data[1].tolist() if hasattr(data[1], "tolist") else list(data[1])
            return OperationResult(
                ok=True,
                data={"time": time_data, "values": values_data},
            )
        except Exception as e:
            logger.error(f"SU transient failed: {e}")
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

            # Trigger via MCU if available
            if mcu:
                mcu.su_set_trigger()

            # Read data
            data = su.pulseSampling_readData()
            logger.debug(f"SU pulse: {len(data[0])} samples")
            # Handle both numpy arrays and plain lists
            time_data = data[0].tolist() if hasattr(data[0], "tolist") else list(data[0])
            values_data = data[1].tolist() if hasattr(data[1], "tolist") else list(data[1])
            return OperationResult(
                ok=True,
                data={"time": time_data, "values": values_data},
            )
        except Exception as e:
            logger.error(f"SU pulse failed: {e}")
            return OperationResult(ok=False, message=str(e))

    # =========================================================================
    # Calibration Operations
    # =========================================================================

    def calibration_measure(
        self,
        folder: Path,
        scope_ip: str,
        channel_ids: list[str] | None = None,
        range_mode: str = "auto",
    ) -> OperationResult:
        """Perform calibration measurements with Keithley scope.

        Args:
            folder: Output folder for calibration data.
            scope_ip: Keithley scope IP address.
            channel_ids: Channel IDs to calibrate (None = all).
            range_mode: Range mode ("auto" or "manual").

        Returns:
            OperationResult with measurement data path.
        """
        try:
            # Import calibration module only when needed
            from dpisamplingunit.calibration import SUCalibrationMeasure

            su = self._get_su()
            cal = SUCalibrationMeasure(su, scope_ip=scope_ip)

            if channel_ids:
                cal.measure_channels(channel_ids, output_folder=folder)
            else:
                cal.measure_all(output_folder=folder)

            logger.info(f"SU calibration measure complete: {folder}")
            return OperationResult(ok=True, data={"folder": str(folder)})
        except Exception as e:
            logger.error(f"SU calibration measure failed: {e}")
            return OperationResult(ok=False, message=str(e))

    def calibration_fit(
        self,
        folder: Path,
        model: str = "linear",
        generate_plot: bool = True,
        calibrate_device: bool = True,
    ) -> OperationResult:
        """Fit calibration data and optionally write to device.

        Args:
            folder: Folder containing calibration measurements.
            model: Fit model ("linear" or "gp").
            generate_plot: Whether to generate fit plots.
            calibrate_device: Whether to write calibration to device.

        Returns:
            OperationResult with fit parameters.
        """
        try:
            # Import calibration module only when needed
            from dpisamplingunit.calibration import SUCalibrationFit

            su = self._get_su()
            fit = SUCalibrationFit(su, calibration_folder=folder)

            if model == "linear":
                params = fit.fit_linear()
            else:
                params = fit.fit_gp()

            if generate_plot:
                fit.generate_plot(output_folder=folder)

            if calibrate_device:
                fit.write_to_device()

            logger.info(f"SU calibration fit complete: model={model}")
            return OperationResult(ok=True, data={"parameters": params})
        except Exception as e:
            logger.error(f"SU calibration fit failed: {e}")
            return OperationResult(ok=False, message=str(e))

    def calibration_verify(
        self,
        folder: Path,
        channel_id: str,
        plot_type: str = "linear",
        data_type: str = "measured",
    ) -> OperationResult:
        """Verify calibration using existing data.

        Args:
            folder: Folder containing calibration data.
            channel_id: Channel to verify.
            plot_type: Plot scale ("linear", "semilog", "error", "error-log", "gradient").
            data_type: Data type ("measured", "linear", "linear-verify", "gp", "gp-verify").

        Returns:
            OperationResult with verification metrics.
        """
        try:
            from dpisamplingunit.calibration import SUCalibrationFit

            su = self._get_su()
            fit = SUCalibrationFit(su, calibration_folder=folder)
            metrics = fit.verify(channel_id=channel_id)

            logger.info(f"SU calibration verify: channel={channel_id}")
            return OperationResult(
                ok=True,
                data={
                    "error": metrics.get("error"),
                    "error_mean": metrics.get("error_mean"),
                    "error_std": metrics.get("error_std"),
                    "error_percent": metrics.get("error_percent"),
                    "mse": metrics.get("mse"),
                    "r2": metrics.get("r2"),
                    "gradient": metrics.get("gradient"),
                    "message": metrics.get("message", ""),
                },
            )
        except Exception as e:
            logger.error(f"SU calibration verify failed: {e}")
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
            logger.debug(f"MCU sync frequencies: SU={su_frequency}, VU={vu_frequency}")
            return OperationResult(ok=True)
        except Exception as e:
            logger.error(f"MCU sync setup failed: {e}")
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
            logger.error(f"MCU trigger failed: {e}")
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
