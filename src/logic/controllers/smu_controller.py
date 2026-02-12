"""Source Measure Unit controller for hardware operations.

This controller encapsulates all SMU hardware workflows including setup, test,
relay control, and calibration operations. Uses direct imports from dpi package.
"""

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
            smu = self._get_smu()
            logger.info("SMU channel configured: %s", config.channel_id)
            return OperationResult(ok=True, data={"channel_id": config.channel_id})
        except Exception as e:
            logger.error("SMU channel configuration failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def save_channel_config(self) -> OperationResult:
        """Save current channel configuration to EEPROM.

        Returns:
            OperationResult with success status.
        """
        try:
            smu = self._get_smu()
            logger.info("SMU channel config saved to EEPROM")
            return OperationResult(ok=True)
        except Exception as e:
            logger.error("SMU EEPROM save failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    def load_channel_config(self) -> OperationResult:
        """Load channel configuration from EEPROM.

        Returns:
            OperationResult with channel data.
        """
        try:
            smu = self._get_smu()
            logger.info("SMU channel config loaded from EEPROM")
            return OperationResult(ok=True, data={})
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
            serial = smu.get_serial()
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
    ) -> OperationResult:
        """Run the full calibration measurement workflow.

        Creates an SMUCalibrationMeasure instance with the given connection
        parameters, measures all ranges, and saves results to HDF5.

        Args:
            keithley_ip: Keithley instrument IP address.
            smu_serial: SMU serial number (None for autodetect).
            smu_interface: SMU interface number.
            su_serial: SU serial number (None for autodetect).
            su_interface: SU interface number.
            folder_path: Output folder for calibration data.
            vsmu_mode: True for VSMU mode, False for normal, None for both.
            verify_calibration: If True, also run verification measurements.

        Returns:
            OperationResult with folder path in data.
        """
        try:
            from dpi.utilities import DPILogger
            from dpisourcemeasureunit.calibration import SMUCalibrationMeasure

            scm = SMUCalibrationMeasure(
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
                scm.measure_all_ranges(
                    vsmu_mode=vsmu_mode,
                    verify_calibration=verify,
                    current_values=None,
                )
                filename = "raw_data_verify.h5" if verify else "raw_data.h5"
                scm.save_measurement(
                    folder_path=folder_path,
                    file_name=filename,
                    append_data=True,
                )

            scm.cleanup()
            logger.info("SMU calibration measure complete: %s", folder_path)
            return OperationResult(ok=True, data={"folder": folder_path})
        except Exception as e:
            logger.error("SMU calibration measure failed: %s", e)
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
            from dpi.utilities import DPILogger
            from dpisourcemeasureunit.calibration import SMUCalibrationFit

            smf = SMUCalibrationFit(
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
            smf.save_gp_model(script_dir=Path(folder_path))
            smf.analyze_ranges()

            if draw_plot:
                smf.plot_calibrated_overview()

            if auto_calibrate:
                smu = self._get_smu()
                smu.calibrate_eeprom(folder_path=Path(folder_path))
                logger.info("Calibration written to EEPROM")

            logger.info("SMU calibration fit complete: %s", folder_path)
            return OperationResult(ok=True)
        except Exception as e:
            logger.error("SMU calibration fit failed: %s", e)
            return OperationResult(ok=False, message=str(e))

    # =========================================================================
    # Private helpers
    # =========================================================================

    def _get_smu(self) -> "DPISourceMeasureUnit":
        """Get or create DPISourceMeasureUnit instance."""
        if self._smu is None:
            from dpi import DPISourceMeasureUnit

            self._smu = DPISourceMeasureUnit(autoinit=True)
        return self._smu
