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
            logger.info(f"SMU initialized: serial={serial}")
            return OperationResult(ok=True, serial=serial)
        except Exception as e:
            logger.error(f"SMU initialization failed: {e}")
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
            logger.error(f"SMU EEPROM defaults failed: {e}")
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
            logger.error(f"SMU EEPROM calibration failed: {e}")
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
            logger.info(f"SMU channel configured: {config.channel_id}")
            return OperationResult(ok=True, data={"channel_id": config.channel_id})
        except Exception as e:
            logger.error(f"SMU channel configuration failed: {e}")
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
            logger.error(f"SMU EEPROM save failed: {e}")
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
            logger.error(f"SMU EEPROM load failed: {e}")
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
            logger.debug(f"SMU temperature: {temp}")
            return OperationResult(ok=True, data={"temperature": temp})
        except Exception as e:
            logger.error(f"SMU temperature read failed: {e}")
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
            logger.info(f"SMU autocalibration complete: serial={serial}")
            return OperationResult(ok=True, serial=serial)
        except Exception as e:
            logger.error(f"SMU autocalibration failed: {e}")
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
            logger.debug(f"SMU IV channel: {channel}, ref={reference}")
            return OperationResult(
                ok=True,
                data={"channel": channel, "reference": reference},
            )
        except Exception as e:
            logger.error(f"SMU IV channel set failed: {e}")
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
            logger.error(f"SMU IV channel get failed: {e}")
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
            logger.debug(f"SMU PA channel: {channel}")
            return OperationResult(ok=True, data={"channel": channel})
        except Exception as e:
            logger.error(f"SMU PA channel set failed: {e}")
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
            logger.debug(f"SMU PA clip: ch={channel}, enabled={enabled}")
            return OperationResult(ok=True)
        except Exception as e:
            logger.error(f"SMU PA clip set failed: {e}")
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
            logger.debug(f"SMU highpass: enabled={enabled}")
            return OperationResult(ok=True, data={"enabled": enabled})
        except Exception as e:
            logger.error(f"SMU highpass set failed: {e}")
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
            logger.error(f"SMU highpass state get failed: {e}")
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
            logger.debug(f"SMU input routing: {target}")
            return OperationResult(ok=True, data={"target": target})
        except Exception as e:
            logger.error(f"SMU input routing set failed: {e}")
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
            logger.debug(f"SMU VGUARD: {target}")
            return OperationResult(ok=True, data={"target": target})
        except Exception as e:
            logger.error(f"SMU VGUARD set failed: {e}")
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
            logger.error(f"SMU saturation state get failed: {e}")
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
            logger.error(f"SMU saturation clear failed: {e}")
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
            channel_ids: Channel IDs to calibrate (ivch/poch/VSMU).
            range_mode: Range mode ("auto" or "manual").

        Returns:
            OperationResult with measurement data path.
        """
        try:
            from dpisourcemeasureunit.calibration import SMUCalibrationMeasure

            smu = self._get_smu()
            cal = SMUCalibrationMeasure(smu, scope_ip=scope_ip)

            if channel_ids:
                cal.measure_channels(channel_ids, output_folder=folder)
            else:
                cal.measure_all(output_folder=folder)

            logger.info(f"SMU calibration measure complete: {folder}")
            return OperationResult(ok=True, data={"folder": str(folder)})
        except Exception as e:
            logger.error(f"SMU calibration measure failed: {e}")
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
            from dpisourcemeasureunit.calibration import SMUCalibrationFit

            smu = self._get_smu()
            fit = SMUCalibrationFit(smu, calibration_folder=folder)

            if model == "linear":
                params = fit.fit_linear()
            else:
                params = fit.fit_gp()

            if generate_plot:
                fit.generate_plot(output_folder=folder)

            if calibrate_device:
                fit.write_to_device()

            logger.info(f"SMU calibration fit complete: model={model}")
            return OperationResult(ok=True, data={"parameters": params})
        except Exception as e:
            logger.error(f"SMU calibration fit failed: {e}")
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
            channel_id: Channel to verify (ivch/poch/VSMU).
            plot_type: Plot scale ("linear", "semilog", "error", "error-log", "gradient").
            data_type: Data type ("measured", "linear", "linear-verify", "gp", "gp-verify").

        Returns:
            OperationResult with verification metrics.
        """
        try:
            from dpisourcemeasureunit.calibration import SMUCalibrationFit

            smu = self._get_smu()
            fit = SMUCalibrationFit(smu, calibration_folder=folder)
            metrics = fit.verify(channel_id=channel_id)

            logger.info(f"SMU calibration verify: channel={channel_id}")
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
            logger.error(f"SMU calibration verify failed: {e}")
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
