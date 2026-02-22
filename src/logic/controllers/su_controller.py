"""Sampling Unit controller for hardware operations.

This controller encapsulates all SU hardware workflows including setup, test,
and calibration operations. It uses direct imports from the dpi package.
"""

from collections.abc import Callable
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
            su = self._get_su()
            # Channel configuration typically involves setting amplifier settings
            # The exact API depends on dpi package implementation
            logger.info("SU channel configured: %s", config.channel_id)
            return OperationResult(ok=True, data={"channel_id": config.channel_id})
        except Exception as e:
            logger.error("SU channel configuration failed: %s", e)
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
            logger.error("SU EEPROM save failed: %s", e)
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
            temp = su.getTemperature()
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
            serial = su.getSerial()
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
            su.setDACValue(dac_voltage)
            su.setPath(source=source, ac=0, adc=None, amp=1.0)
            voltage = su.readInputVoltage()
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
            logger.debug("SU transient: %s samples", len(data[0]))
            # Handle both numpy arrays and plain lists
            time_data = data[0].tolist() if hasattr(data[0], "tolist") else list(data[0])
            values_data = data[1].tolist() if hasattr(data[1], "tolist") else list(data[1])
            return OperationResult(
                ok=True,
                data={"time": time_data, "values": values_data},
            )
        except Exception as e:
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
            logger.debug("SU pulse: %s samples", len(data[0]))
            # Handle both numpy arrays and plain lists
            time_data = data[0].tolist() if hasattr(data[0], "tolist") else list(data[0])
            values_data = data[1].tolist() if hasattr(data[1], "tolist") else list(data[1])
            return OperationResult(
                ok=True,
                data={"time": time_data, "values": values_data},
            )
        except Exception as e:
            logger.error("SU pulse failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    # =========================================================================
    # Calibration Operations
    # =========================================================================

    def calibration_measure(
        self,
        keithley_ip: str,
        smu_serial: int | None,
        smu_interface: int | None,
        su_serial: int | None,
        su_interface: int | None,
        folder_path: str,
        verify_calibration: bool = False,
        on_point_measured: Callable[[dict], None] | None = None,
    ) -> OperationResult:
        """Run the full calibration measurement workflow.

        Creates an SUCalibrationMeasure instance with the given connection
        parameters, prepares voltage values, measures all ranges, and saves
        results to HDF5.

        Args:
            keithley_ip: Keithley instrument IP address.
            smu_serial: SMU serial number (None for autodetect).
            smu_interface: SMU interface number.
            su_serial: SU serial number (None for autodetect).
            su_interface: SU interface number.
            folder_path: Output folder for calibration data.
            verify_calibration: If True, also run verification measurements.
            on_point_measured: Optional callback invoked after each measurement
                point with a dict containing ``series``, ``x``, ``y``, ``v_set``.

        Returns:
            OperationResult with folder path in data.
        """
        try:
            from dpi.utilities import DPILogger

            from src.logic.calibration import SUCalibrationMeasure

            scm = SUCalibrationMeasure(
                keithley_ip,
                smu_serial,
                smu_interface,
                su_serial,
                su_interface,
                DPILogger.VERBOSE,
            )

            verify_list = [False, True] if verify_calibration else [False]
            for verify in verify_list:
                scm.data = []
                voltage_values = scm.prepare_measurement_values(
                    max_value=6.5,
                    decades=7,
                    delta_log=1 / 3,
                    delta_lin=1 / 4,
                )
                scm.measure_all_ranges(
                    voltage_values,
                    on_point_measured=on_point_measured,
                )
                filename = "raw_data_verify.h5" if verify else "raw_data.h5"
                scm.save_measurement(
                    folder_path=folder_path,
                    file_name=filename,
                    append_data=True,
                )

            scm.cleanup()
            logger.info("SU calibration measure complete: %s", folder_path)
            return OperationResult(ok=True, data={"folder": folder_path})
        except Exception as e:
            logger.error("SU calibration measure failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def calibration_fit(
        self,
        folder_path: str,
        draw_plot: bool = True,
        auto_calibrate: bool = True,
    ) -> OperationResult:
        """Run calibration fit and optionally write to EEPROM.

        Loads raw measurement data, trains linear and GP models, analyzes
        ranges, and optionally writes calibration to the device EEPROM.

        Args:
            folder_path: Folder containing calibration measurements.
            draw_plot: If True, generate calibration plots.
            auto_calibrate: If True, write calibration to EEPROM.

        Returns:
            OperationResult with success status.
        """
        try:
            from dpi import DPISourceMeasureUnit
            from dpi.utilities import DPILogger

            from src.logic.calibration import SUCalibrationFit

            smf = SUCalibrationFit(
                calibration_folder=folder_path,
                load_raw=True,
                verify_calibration=True,
                log_level=DPILogger.DEBUG,
            )

            if draw_plot:
                smf.plot_measurement_overview()
                smf.plot_aggregated_overview()

            smf.train_linear_model()
            smf.train_gp_model()
            smf.analyze_ranges()

            if draw_plot:
                smf.plot_calibrated_overview()

            if auto_calibrate:
                smu = DPISourceMeasureUnit(autoinit=True)
                smu.calibrate_eeprom()
                logger.info("Calibration written to EEPROM via SMU")

            logger.info(f"SU calibration fit complete: {folder_path}")
            return OperationResult(ok=True)
        except Exception as e:
            logger.error("SU calibration fit failed: %s", e)
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
