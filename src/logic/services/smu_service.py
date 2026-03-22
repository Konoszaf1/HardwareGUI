"""SourceMeasureUnitService for SMU hardware communication and task management.

This service owns connection lifecycle and coordinates threaded hardware operations
by delegating to SMUController for actual device interactions.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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
        """Return the SMU serial number if connected.

        Note: DPIUnit.serial stays None when autoinit=True because only
        DPIIO_Legacy._serial is updated during autodetect.  We read
        _serial (the IO layer's copy) to get the actual value.
        """
        if self._smu is None:
            return None
        return getattr(self._smu, "_serial", None) or self._smu.serial

    @property
    def controller(self) -> SMUController:
        """Return the SMUController instance, creating if needed."""
        if self._controller is None:
            self._ensure_connected()
        return self._controller

    def _get_serial(self) -> int:
        """Get the actual SMU serial, preferring _serial over serial."""
        if self._smu is None:
            return 0
        return getattr(self._smu, "_serial", None) or self._smu.serial or 0

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
        logger.info("SMU connected: serial=%s", self._get_serial())
        self.connectedChanged.emit(True)

    def _resolve_calibration_folder(self) -> str:
        """Resolve the calibration folder path.

        Priority: stored folder > serial-based > scan for existing folder.
        Updates ``_calibration_folder`` when a valid folder is found.
        """
        if self._calibration_folder and Path(self._calibration_folder).exists():
            return self._calibration_folder

        serial = self._targets.smu_serial or self._get_serial() or 0
        if serial:
            candidate = str(Path(f"calibration/smu_calibration_sn{serial}").resolve())
            if Path(candidate).exists():
                self._calibration_folder = candidate
                return candidate

        # Scan for existing calibration folders
        cal_dir = Path("calibration")
        if cal_dir.exists():
            folders = sorted(
                cal_dir.glob("smu_calibration_sn*"),
                key=lambda p: p.stat().st_mtime,
            )
            if folders:
                self._calibration_folder = str(folders[-1].resolve())
                return self._calibration_folder

        # Fallback: construct path (may not exist yet, e.g. before first measurement)
        folder = str(Path(f"calibration/smu_calibration_sn{serial or 'auto'}").resolve())
        return folder

    def _disconnect(self) -> None:
        """Tear down SMU hardware connections."""
        if self._smu:
            try:
                self._smu.disconnect()
            except Exception:
                pass
            self._smu = None
        self._controller = None

    def _artifact_dir(self) -> str:
        """Returns the path to the directory where artifacts are saved."""
        return f"calibration/smu_calibration_sn{self._get_serial()}"

    def _safe_collect_artifacts(self) -> list[str]:
        """Collect artifacts without crashing if directory is missing."""
        try:
            return self._collect_artifacts()
        except Exception as e:
            logger.warning("Artifact collection failed: %s", e)
            return []

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

        return make_task("Hardware Setup", job)

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

        return make_task("Verify", job)

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

        return make_task("Read Temperature", job)

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

        return make_task("Set IV Channel", job)

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

        return make_task("Set PA Channel", job)

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

        return make_task("Set Highpass", job)

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

        return make_task("Set Input Routing", job)

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

        return make_task("Set VGUARD", job)

    def run_calibration_measure(
        self,
        vsmu_mode: bool | None = None,
        verify_calibration: bool = False,
        pa_channels: list[str] | None = None,
        speed_preset: str = "normal",
        single_range: tuple[str, str] | None = None,
    ) -> FunctionTask | None:
        """Run calibration measurement with Keithley.

        Delegates to SMUController.calibration_measure for the actual workflow.
        Does NOT pre-connect to SMU — SMUCalibrationMeasure creates its own
        connections to SMU, SU, and Keithley internally.

        Emits data_chunk signals for live progress:
        - {"type": "cal_range", ...} when a range starts/finishes
        - {"type": "cal_point", ...} for each measured point

        Args:
            vsmu_mode: True for VSMU mode, False for normal, None for both.
            verify_calibration: If True, also verify the calibration.
            pa_channels: PA channels to measure.
            speed_preset: "fast", "normal", or "precise".
            single_range: If set, (pa_channel, iv_channel) for single range.

        Returns:
            FunctionTask that runs calibration measurements, or None if
            Keithley IP is not configured.
        """
        if not self._target_instrument_ip:
            return None

        def job():
            smu_serial = self._targets.smu_serial or None
            su_serial = self._targets.su_serial or None
            serial = self._targets.smu_serial or self._get_serial() or "auto"
            folder_path = str(
                Path(f"calibration/smu_calibration_sn{serial}").resolve()
            )
            self._calibration_folder = folder_path

            # Release USB so SMUCalibrationMeasure can claim devices
            with self._hw_lock:
                controller = self._controller or SMUController()
                if self._smu is not None:
                    try:
                        self._smu.disconnect()
                    except Exception:
                        pass
                controller._smu = None
                self._smu = None
                self._controller = None
                self._connected = False

            result = controller.calibration_measure(
                keithley_ip=self._target_instrument_ip,
                smu_serial=smu_serial,
                smu_interface=self._targets.smu_interface or None,
                su_serial=su_serial,
                su_interface=self._targets.su_interface or None,
                folder_path=folder_path,
                vsmu_mode=vsmu_mode,
                verify_calibration=verify_calibration,
                pa_channels=pa_channels,
                speed_preset=speed_preset,
                single_range=single_range,
                on_point_measured=lambda d: task.signals.data_chunk.emit(d),
                on_range_started=lambda d: task.signals.data_chunk.emit(d),
                cancel_event=task.cancel_event,
            )
            # Reconnect so buttons stay enabled after measurement
            try:
                with self._hw_lock:
                    self._ensure_connected()
            except Exception as e:
                logger.warning("Failed to reconnect after calibration: %s", e)

            data = result.data or {}
            return {
                "ok": result.ok,
                "message": result.message,
                "folder": folder_path,
                "cancelled": data.get("cancelled", False),
                "completed_ranges": data.get("completed_ranges"),
                "total_ranges": data.get("total_ranges"),
                "artifacts": self._safe_collect_artifacts(),
            }

        task = make_task("Calibration: Measure", job)
        return task

    def run_calibration_fit(
        self,
        draw_plot: bool = True,
        auto_calibrate: bool = False,
        model_type: str = "linear",
        verify_calibration: bool = True,
    ) -> FunctionTask:
        """Run calibration fit and optionally write to EEPROM.

        Delegates to SMUController.calibration_fit for the actual workflow.

        Args:
            draw_plot: If True, generate calibration plots.
            auto_calibrate: If True, write calibration to EEPROM.
            model_type: Model to save ("linear" or "gp").
            verify_calibration: If True, load verification data too.

        Returns:
            FunctionTask that fits calibration data.
        """

        def job():
            with self._hw_lock:
                self._ensure_connected()

                folder_path = self._resolve_calibration_folder()

                result = self._controller.calibration_fit(
                    folder_path=folder_path,
                    draw_plot=draw_plot,
                    auto_calibrate=auto_calibrate,
                    model_type=model_type,
                    verify_calibration=verify_calibration,
                )
                data = result.data or {}
                return {
                    "ok": result.ok,
                    "message": result.message,
                    "analysis_plots": data.get("analysis_plots", []),
                    "calibrated_ranges": data.get("calibrated_ranges", []),
                    "artifacts": self._safe_collect_artifacts(),
                }

        return make_task("Calibration: Fit", job)

    def run_load_calibration_status(self) -> FunctionTask | None:
        """Load calibration status by scanning the calibration folder.

        Returns:
            FunctionTask with calibration_status list, or None if no folder.
        """
        folder = self._resolve_calibration_folder()
        if not folder or not Path(folder).exists():
            return None

        def job():
            controller = self._controller or SMUController()
            status = controller.get_calibration_status(folder)
            return {"ok": True, "calibration_status": status}

        return make_task("Load Cal Status", job)

    def run_calibrate(self, model: str = "linear") -> FunctionTask:
        """Run calibration fit (called by calibration page Run Calibration button)."""
        return self.run_calibration_fit(
            draw_plot=True, auto_calibrate=False, model_type=model,
        )

    def run_calibration_verify(self, num_points: int = 10) -> FunctionTask | None:
        """Verify calibration by re-measuring."""
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

        return make_task("Program Relays", job)

    def run_set_pa_clip(self, channel: int, enabled: bool) -> FunctionTask:
        """Set Post-Amplifier clip detection for a channel.

        Args:
            channel: PA channel number (1-4).
            enabled: Whether to enable clip detection.

        Returns:
            FunctionTask that sets PA clip state.
        """

        def job():
            with self._hw_lock:
                self._ensure_connected()
                result = self._controller.set_pa_clip(channel=channel, enabled=enabled)
                return {"ok": result.ok}

        return make_task("Set PA Clip", job)

    def run_get_saturation_state(self) -> FunctionTask:
        """Read saturation detection state.

        Returns:
            FunctionTask with iv_saturated and pa_saturated in data.
        """

        def job():
            with self._hw_lock:
                self._ensure_connected()
                result = self._controller.get_saturation_state()
                return result.data if result.ok else {"ok": False}

        return make_task("Read Saturation", job)

    def run_clear_saturation(self) -> FunctionTask:
        """Clear saturation detection flags.

        Returns:
            FunctionTask that clears saturation.
        """

        def job():
            with self._hw_lock:
                self._ensure_connected()
                result = self._controller.clear_saturation()
                return {"ok": result.ok}

        return make_task("Clear Saturation", job)

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

        return make_task("Save Config", job)

    def run_load_config(self) -> FunctionTask:
        """Load channel configuration from device EEPROM.

        Returns:
            FunctionTask that loads configuration.
        """

        def job():
            with self._hw_lock:
                self._ensure_connected()
                result = self._controller.load_channel_config()
                channels = result.data.get("channels", []) if result.data else []
                return {
                    "ok": result.ok, "data": result.data,
                    "channels": channels, "message": result.message,
                }

        return make_task("Load Config", job)

    def connect_only(self) -> FunctionTask:
        """Connect to SMU hardware without additional operations.

        Returns:
            FunctionTask that establishes hardware connection.
        """

        def job():
            with self._hw_lock:
                self._ensure_connected()
                return {"serial": self._get_serial(), "ok": True}

        return make_task("Connect", job)
