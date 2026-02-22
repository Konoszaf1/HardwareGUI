"""SourceMeasureUnitService for SMU hardware communication and task management.

This service owns connection lifecycle and coordinates threaded hardware operations
by delegating to SMUController for actual device interactions.
"""

from __future__ import annotations

from dataclasses import dataclass

import matplotlib
from dpi import DPISourceMeasureUnit

from src.logging_config import get_logger
from src.logic.controllers.smu_controller import SMUController
from src.logic.qt_workers import FunctionTask, make_task
from src.logic.services.base_service import BaseHardwareService

matplotlib.use("Agg")

logger = get_logger(__name__)


@dataclass
class SMUTargetIds:
    """Target identifiers for SMU and SU hardware."""

    smu_serial: int = 0
    smu_interface: int = 0
    su_serial: int = 0
    su_interface: int = 0


class SourceMeasureUnitService(BaseHardwareService):
    """Owns SMU hardware connections and runs script commands in worker threads.

    This service manages connection lifecycle and threading while delegating
    actual hardware operations to SMUController.
    """

    def __init__(self) -> None:
        super().__init__()
        logger.debug("SourceMeasureUnitService initializing")
        self._targets: SMUTargetIds = SMUTargetIds()
        self._smu: DPISourceMeasureUnit | None = None
        self._controller: SMUController | None = None
        self._calibration_folder: str = ""
        logger.info("SourceMeasureUnitService initialized")

    # ---- Configuration targets ----
    def set_targets(
        self,
        keithley_ip: str,
        smu_serial: int,
        smu_interface: int,
        su_serial: int,
        su_interface: int,
    ) -> None:
        """Set hardware connection targets.

        Args:
            keithley_ip: IP address of the Keithley instrument.
            smu_serial: SMU serial number.
            smu_interface: SMU interface number.
            su_serial: Sampling Unit serial number.
            su_interface: Sampling Unit interface number.
        """
        self._target_instrument_ip = keithley_ip or getattr(self, "_target_instrument_ip", "")
        self._targets = SMUTargetIds(smu_serial, smu_interface, su_serial, su_interface)

    # ---- Accessors ----
    @property
    def smu_serial(self) -> int | None:
        """Return the SMU serial number if connected."""
        return self._smu.get_serial() if self._smu else None

    @property
    def controller(self) -> SMUController:
        """Return the SMUController instance, creating if needed."""
        if self._controller is None:
            self._ensure_connected()
        return self._controller

    # ---- Internals ----
    def _ensure_connected(self) -> None:
        """Ensure SMU hardware is connected and controller is initialized."""
        if self._connected and self._smu and self._controller:
            return

        smu_serial = self._targets.smu_serial
        smu_if = self._targets.smu_interface

        if smu_serial == 0:
            # Autodetect SMU
            self._smu = DPISourceMeasureUnit(autoinit=True)
        else:
            self._smu = DPISourceMeasureUnit(serial=smu_serial, interface=smu_if)

        # Create controller with hardware instance
        self._controller = SMUController(smu=self._smu)

        self._connected = True
        logger.info("SMU connected: serial=%s", self._smu.get_serial())
        self.connectedChanged.emit(True)

    def _artifact_dir(self) -> str:
        """Returns the path to the directory where artifacts are saved."""
        serial = self._smu.get_serial() if self._smu else 0
        return f"calibration/smu_calibration_sn{serial}"

    # ---- Public operations (threaded) ----
    def run_hw_setup(
        self, serial: int, processor_type: str = "746", connector_type: str = "BNC"
    ) -> FunctionTask:
        """Initialize a new SMU device with the given parameters.

        Args:
            serial: New serial number for the device.
            processor_type: Processor type (e.g., "746").
            connector_type: Connector type ("BNC" or "TRIAX").

        Returns:
            FunctionTask that initializes the device.
        """

        def job():
            with self._hw_lock:
                # Create fresh controller for new device
                smu = DPISourceMeasureUnit(autoinit=True)
                controller = SMUController(smu=smu)
                result = controller.initialize_device(
                    serial=serial,
                    processor_type=processor_type,
                    connector_type=connector_type,
                )
                return {"serial": result.serial, "ok": result.ok, "message": result.message}

        return make_task("hw_setup", job)

    def run_verify(self) -> FunctionTask:
        """Run hardware verification (calibrate_eeprom).

        Returns:
            FunctionTask that verifies hardware configuration.
        """

        def job():
            with self._hw_lock:
                self._ensure_connected()
                result = self._controller.calibrate_eeprom()
                return {"ok": result.ok, "message": result.message}

        return make_task("verify", job)

    def run_temperature_read(self) -> FunctionTask:
        """Read SMU temperature.

        Returns:
            FunctionTask that reads temperature.
        """

        def job():
            with self._hw_lock:
                self._ensure_connected()
                result = self._controller.read_temperature()
                return {"ok": result.ok, "temperature": result.data.get("temperature")}

        return make_task("temperature", job)

    # ---- Relay Control Operations ----
    def run_set_iv_channel(
        self,
        channel: int,
        reference: str = "GND",
    ) -> FunctionTask:
        """Set IV-Converter channel.

        Args:
            channel: Channel number (0=disable, 1-9=enable).
            reference: Reference voltage ("GND" or "VSMU").

        Returns:
            FunctionTask that sets IV channel.
        """

        def job():
            with self._hw_lock:
                self._ensure_connected()
                result = self._controller.set_iv_channel(channel=channel, reference=reference)
                return {"ok": result.ok, "channel": result.data.get("channel")}

        return make_task("iv_channel", job)

    def run_set_pa_channel(self, channel: int) -> FunctionTask:
        """Set Post-Amplifier channel.

        Args:
            channel: Channel number (0=disable, 1-4=enable).

        Returns:
            FunctionTask that sets PA channel.
        """

        def job():
            with self._hw_lock:
                self._ensure_connected()
                result = self._controller.set_pa_channel(channel=channel)
                return {"ok": result.ok, "channel": result.data.get("channel")}

        return make_task("pa_channel", job)

    def run_set_highpass(self, enabled: bool) -> FunctionTask:
        """Enable/disable highpass filter.

        Args:
            enabled: Whether to enable highpass.

        Returns:
            FunctionTask that sets highpass state.
        """

        def job():
            with self._hw_lock:
                self._ensure_connected()
                result = self._controller.set_highpass(enabled=enabled)
                return {"ok": result.ok, "enabled": result.data.get("enabled")}

        return make_task("highpass", job)

    def run_set_input_routing(self, target: str) -> FunctionTask:
        """Set input routing.

        Args:
            target: Input routing target ("GND", "GUARD", "VSMU", "SU", "VSMU_AND_SU").

        Returns:
            FunctionTask that sets input routing.
        """

        def job():
            with self._hw_lock:
                self._ensure_connected()
                result = self._controller.set_input_routing(target=target)
                return {"ok": result.ok, "target": result.data.get("target")}

        return make_task("input_routing", job)

    def run_set_vguard(self, target: str) -> FunctionTask:
        """Set VGUARD routing.

        Args:
            target: VGUARD target ("GND" or "VSMU").

        Returns:
            FunctionTask that sets VGUARD routing.
        """

        def job():
            with self._hw_lock:
                self._ensure_connected()
                result = self._controller.set_vguard(target=target)
                return {"ok": result.ok, "target": result.data.get("target")}

        return make_task("vguard", job)

    @BaseHardwareService.require_instrument_ip
    def run_calibration_measure(
        self,
        vsmu_mode: bool | None = None,
        verify_calibration: bool = False,
    ) -> FunctionTask:
        """Run calibration measurement with Keithley.

        Delegates to SMUController.calibration_measure for the actual workflow.

        Args:
            vsmu_mode: True for VSMU mode, False for normal, None for both.
            verify_calibration: If True, also verify the calibration.

        Returns:
            FunctionTask that runs calibration measurements.
        """

        def job():
            serial = self._smu.get_serial() if self._smu else 0
            folder_path = f"calibration/smu_calibration_sn{serial}"
            self._calibration_folder = folder_path

            result = self._controller.calibration_measure(
                keithley_ip=self._target_instrument_ip,
                smu_serial=self._targets.smu_serial or None,
                smu_interface=self._targets.smu_interface or None,
                su_serial=self._targets.su_serial or None,
                su_interface=self._targets.su_interface or None,
                folder_path=folder_path,
                vsmu_mode=vsmu_mode,
                verify_calibration=verify_calibration,
            )
            return {
                "ok": result.ok,
                "message": result.message,
                "folder": folder_path,
                "artifacts": self._collect_artifacts(),
            }

        return make_task("calibration_measure", job)

    def run_calibration_fit(
        self, draw_plot: bool = True, auto_calibrate: bool = True
    ) -> FunctionTask:
        """Run calibration fit and optionally write to EEPROM.

        Delegates to SMUController.calibration_fit for the actual workflow.

        Args:
            draw_plot: If True, generate calibration plots.
            auto_calibrate: If True, write calibration to EEPROM.

        Returns:
            FunctionTask that fits calibration data.
        """

        def job():
            with self._hw_lock:
                self._ensure_connected()

                serial = self._smu.get_serial() if self._smu else 0
                folder_path = self._calibration_folder or f"calibration/smu_calibration_sn{serial}"

                result = self._controller.calibration_fit(
                    folder_path=folder_path,
                    draw_plot=draw_plot,
                    auto_calibrate=auto_calibrate,
                )
                return {
                    "ok": result.ok,
                    "message": result.message,
                    "artifacts": self._collect_artifacts(),
                }

        return make_task("calibration_fit", job)

    def run_measure(self, channel: str = "CH1") -> FunctionTask:
        """Run calibration measurement (called by calibration page Measure button).

        Args:
            channel: Channel to measure (currently unused — measures all ranges).

        Returns:
            FunctionTask that runs calibration measurement.
        """
        return self.run_calibration_measure()

    def run_calibrate(self, model: str = "linear") -> FunctionTask:
        """Run calibration fit (called by calibration page Run Calibration button).

        Args:
            model: Calibration model type ("linear" or "gp").

        Returns:
            FunctionTask that fits calibration data.
        """
        return self.run_calibration_fit(draw_plot=True, auto_calibrate=True)

    def run_calibration_verify(self, num_points: int = 10) -> FunctionTask:
        """Verify calibration by re-measuring (called by calibration page Verify button).

        Args:
            num_points: Number of verification points (informational).

        Returns:
            FunctionTask that verifies calibration.
        """
        return self.run_calibration_measure(verify_calibration=True)

    def run_program_relais(
        self,
        iv_channel: int,
        iv_reference: str,
        pa_channel: int,
        highpass: bool,
        dut_routing: str,
        vguard: str,
    ) -> FunctionTask:
        """Program all relay settings in a single operation.

        Args:
            iv_channel: IV-Converter channel number.
            iv_reference: IV reference ("GND" or "VSMU").
            pa_channel: Post-Amplifier channel number.
            highpass: Whether highpass is enabled.
            dut_routing: Input routing target.
            vguard: VGUARD target ("GND" or "VSMU").

        Returns:
            FunctionTask that programs all relays.
        """

        def job():
            with self._hw_lock:
                self._ensure_connected()
                results = []
                results.append(
                    self._controller.set_iv_channel(channel=iv_channel, reference=iv_reference)
                )
                results.append(self._controller.set_pa_channel(channel=pa_channel))
                results.append(self._controller.set_highpass(enabled=highpass))
                results.append(self._controller.set_input_routing(target=dut_routing))
                results.append(self._controller.set_vguard(target=vguard))
                all_ok = all(r.ok for r in results)
                return {"ok": all_ok}

        return make_task("program_relais", job)

    def run_save_config(self) -> FunctionTask:
        """Save current channel configuration to device EEPROM.

        Returns:
            FunctionTask that saves configuration.
        """

        def job():
            with self._hw_lock:
                self._ensure_connected()
                result = self._controller.save_channel_config()
                return {"ok": result.ok, "message": result.message}

        return make_task("save_config", job)

    def run_load_config(self) -> FunctionTask:
        """Load channel configuration from device EEPROM.

        Returns:
            FunctionTask that loads configuration.
        """

        def job():
            with self._hw_lock:
                self._ensure_connected()
                result = self._controller.load_channel_config()
                return {"ok": result.ok, "data": result.data, "message": result.message}

        return make_task("load_config", job)

    def connect_only(self) -> FunctionTask:
        """Connect to SMU hardware without additional operations.

        Returns:
            FunctionTask that establishes hardware connection.
        """

        def job():
            with self._hw_lock:
                self._ensure_connected()
                return {"serial": self._smu.get_serial() if self._smu else None, "ok": True}

        return make_task("connect", job)
