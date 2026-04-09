"""SamplingUnitService for SU hardware communication and task management.

This service owns connection lifecycle and coordinates threaded hardware operations
by delegating to SUController for actual device interactions.
"""

from __future__ import annotations

import contextlib
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from dpi import DPIMainControlUnit, DPISamplingUnit

from src.logging_config import get_logger
from src.logic.controllers.su_controller import OperationResult, SUController
from src.logic.qt_workers import FunctionTask, make_task
from src.logic.services.base_service import BaseHardwareService

logger = get_logger(__name__)


@dataclass
class SUTargetIds:
    """Target identifiers for SU and SMU hardware."""

    su_serial: int = 0
    su_interface: int = 0
    smu_serial: int = 0
    smu_interface: int = 0


class SamplingUnitService(BaseHardwareService):
    """Owns SU hardware connections and runs script commands in worker threads.

    This service manages connection lifecycle and threading while delegating
    actual hardware operations to SUController.
    """

    def __init__(self) -> None:
        super().__init__()
        logger.debug("SamplingUnitService initializing")
        self._targets: SUTargetIds = SUTargetIds()
        self._su: DPISamplingUnit | None = None
        self._mcu: DPIMainControlUnit | None = None
        self._controller: SUController | None = None
        self._calibration_folder: str = ""
        logger.info("SamplingUnitService initialized")

    # ---- Configuration targets ----
    def set_targets(
        self,
        keithley_ip: str,
        su_serial: int,
        su_interface: int,
        smu_serial: int,
        smu_interface: int,
    ) -> None:
        """Set hardware connection targets.

        Args:
            keithley_ip: IP address of the Keithley instrument.
            su_serial: SU serial number.
            su_interface: SU interface number.
            smu_serial: SMU serial number (used for calibration).
            smu_interface: SMU interface number.
        """
        self._target_instrument_ip = keithley_ip or getattr(self, "_target_instrument_ip", "")
        self._targets = SUTargetIds(su_serial, su_interface, smu_serial, smu_interface)

    # ---- Accessors ----
    @property
    def su_serial(self) -> int | None:
        """Return the SU serial number if connected.

        Note: DPIUnit.serial stays None when autoinit=True because only
        DPIIO_Legacy._serial is updated during autodetect.  We read
        _serial (the IO layer's copy) to get the actual value.
        """
        if self._su is None:
            return None
        return getattr(self._su, "_serial", None) or self._su.serial

    @property
    def controller(self) -> SUController:
        """Return the SUController instance, creating if needed."""
        if self._controller is None:
            self._ensure_connected()
        assert self._controller is not None
        return self._controller

    def _get_serial(self) -> int:
        """Get the actual SU serial, preferring _serial over serial."""
        if self._su is None:
            return 0
        return getattr(self._su, "_serial", None) or self._su.serial or 0

    # ---- Internals ----
    _CONNECT_MAX_ATTEMPTS = 3
    _CONNECT_RETRY_DELAY = 1.0  # seconds

    def _ensure_connected(self) -> None:
        """Ensure SU hardware is connected and controller is initialized.

        On the fast path (already connected), probes the device with a
        lightweight USB read to verify it is still responsive.  If the
        probe fails the connection is torn down and a full reconnect is
        attempted.

        Connection attempts are retried up to ``_CONNECT_MAX_ATTEMPTS``
        times with a short delay between each attempt to cover transient
        USB enumeration failures.
        """
        if self._connected and self._su and self._controller:
            # Health check: verify USB link is still alive
            try:
                self._su.get_temperature()
            except (OSError, RuntimeError) as e:
                logger.warning("SU health check failed, forcing reconnect: %s", e)
                self._invalidate_connection()
                # Fall through to full reconnect below
            else:
                return

        for attempt in range(1, self._CONNECT_MAX_ATTEMPTS + 1):
            try:
                su_serial = self._targets.su_serial
                su_if = self._targets.su_interface

                if su_serial == 0:
                    self._su = DPISamplingUnit(autoinit=True)
                else:
                    self._su = DPISamplingUnit(serial=su_serial, interface=su_if)

                # Initialize MCU for synchronized operations (optional)
                try:
                    self._mcu = DPIMainControlUnit(autoinit=True)
                except (OSError, RuntimeError) as e:
                    logger.warning("MCU not available: %s", e)
                    self._mcu = None

                # Create controller with hardware instances
                self._controller = SUController(su=self._su, mcu=self._mcu)
                break  # Connection succeeded
            except (OSError, RuntimeError) as e:
                # Clean up any partially-created handles
                self._disconnect()
                if attempt < self._CONNECT_MAX_ATTEMPTS:
                    logger.warning(
                        "SU connect attempt %d/%d failed: %s — retrying in %.0fs",
                        attempt,
                        self._CONNECT_MAX_ATTEMPTS,
                        e,
                        self._CONNECT_RETRY_DELAY,
                    )
                    time.sleep(self._CONNECT_RETRY_DELAY)
                else:
                    logger.error(
                        "SU connect failed after %d attempts: %s",
                        self._CONNECT_MAX_ATTEMPTS,
                        e,
                    )
                    raise

        self._connected = True
        logger.info("SU connected: serial=%s", self._get_serial())
        self.connectedChanged.emit(True)

    def _invalidate_connection(self) -> None:
        """Tear down hardware and mark as disconnected."""
        self._disconnect()
        self._connected = False
        self.connectedChanged.emit(False)

    def _run_hw_operation(
        self,
        operation: Callable[[SUController], OperationResult],
    ) -> OperationResult:
        """Execute a hardware operation with auto-disconnect on failure.

        If the controller operation returns ``ok=False`` or raises an
        exception, the connection is invalidated so the next call forces
        a fresh reconnect attempt.
        """
        with self._hw_lock:
            self._ensure_connected()
            assert self._controller is not None
            try:
                result = operation(self._controller)
            except (OSError, RuntimeError):
                logger.error("Hardware operation raised, disconnecting for safety")
                self._invalidate_connection()
                raise

            if not result.ok:
                logger.warning(
                    "Hardware operation failed: %s — disconnecting for safety",
                    result.message,
                )
                self._invalidate_connection()

            return result

    def _disconnect(self) -> None:
        """Tear down SU hardware connections."""
        if self._su:
            with contextlib.suppress(OSError, RuntimeError):
                self._su.disconnect()
            self._su = None
        if self._mcu:
            with contextlib.suppress(OSError, RuntimeError):
                self._mcu.disconnect()
            self._mcu = None
        self._controller = None

    def _artifact_dir(self) -> str:
        """Returns the path to the directory where artifacts are saved."""
        return f"calibration/su_calibration_sn{self._get_serial()}"

    def _resolve_calibration_folder(self) -> str:
        """Resolve the calibration folder path.

        Priority: stored folder > serial-based > scan for existing folder.
        Updates ``_calibration_folder`` when a valid folder is found.
        """
        if self._calibration_folder and Path(self._calibration_folder).exists():
            return self._calibration_folder

        serial = self._targets.su_serial or self._get_serial() or 0
        if serial:
            candidate = str(Path(f"calibration/su_calibration_sn{serial}").resolve())
            if Path(candidate).exists():
                self._calibration_folder = candidate
                return candidate

        # Scan for existing calibration folders
        cal_dir = Path("calibration")
        if cal_dir.exists():
            folders = sorted(
                cal_dir.glob("su_calibration_sn*"),
                key=lambda p: p.stat().st_mtime,
            )
            if folders:
                self._calibration_folder = str(folders[-1].resolve())
                return self._calibration_folder

        # Fallback to constructed path
        return str(Path(f"calibration/su_calibration_sn{serial or 'auto'}").resolve())

    # ---- Public operations (threaded) ----
    def run_hw_setup(
        self, serial: int, processor_type: str = "746", connector_type: str = "BNC"
    ) -> FunctionTask:
        """Initialize a new SU device with the given parameters.

        Args:
            serial: New serial number for the device.
            processor_type: Processor type (e.g., "746").
            connector_type: Connector type ("BNC" or "SMA").

        Returns:
            FunctionTask that initializes the device.
        """

        def job():
            with self._hw_lock:
                # Create fresh controller for new device
                su = DPISamplingUnit(autoinit=True)
                controller = SUController(su=su)
                result = controller.initialize_device(
                    serial=serial,
                    processor_type=processor_type,
                    connector_type=connector_type,
                )
                return {"serial": result.serial, "ok": result.ok, "message": result.message}

        return make_task("Hardware Setup", job)

    def run_verify(self) -> FunctionTask:
        """Run hardware verification (performautocalibration).

        Returns:
            FunctionTask that verifies hardware configuration.
        """

        def job():
            result = self._run_hw_operation(lambda c: c.perform_autocalibration())
            return {"ok": result.ok, "serial": result.serial, "message": result.message}

        return make_task("Verify", job)

    def run_temperature_read(self) -> FunctionTask:
        """Read SU temperature.

        Returns:
            FunctionTask that reads temperature.
        """

        def job():
            result = self._run_hw_operation(lambda c: c.read_temperature())
            return {"ok": result.ok, "temperature": result.data.get("temperature")}

        return make_task("Read Temperature", job)

    def run_single_shot(
        self,
        dac_voltage: float = 0.0,
        source: str = "VCAL",
    ) -> FunctionTask:
        """Run single-shot voltage measurement.

        Args:
            dac_voltage: DAC output voltage.
            source: Signal source path.

        Returns:
            FunctionTask that performs measurement.
        """

        def job():
            result = self._run_hw_operation(
                lambda c: c.single_shot_measure(dac_voltage=dac_voltage, source=source)
            )
            return {"ok": result.ok, "voltage": result.data.get("voltage")}

        return make_task("Single Shot Measure", job)

    def run_transient_measure(
        self,
        measurement_time: float,
        sampling_rate: float = 1e-6,
        trigger: str = "none",
    ) -> FunctionTask:
        """Run transient measurement.

        Args:
            measurement_time: Total measurement time in seconds.
            sampling_rate: Sampling period in seconds.
            trigger: Trigger mode.

        Returns:
            FunctionTask that performs transient measurement.
        """

        def job():
            result = self._run_hw_operation(
                lambda c: c.transient_measure(
                    measurement_time=measurement_time,
                    sampling_rate=sampling_rate,
                    trigger=trigger,
                )
            )
            return {
                "ok": result.ok,
                "time": result.data.get("time"),
                "values": result.data.get("values"),
            }

        return make_task("Transient Measure", job)

    def run_pulse_measure(
        self,
        num_samples: int,
        sampling_rate: float = 1e6,
    ) -> FunctionTask:
        """Run pulse measurement.

        Args:
            num_samples: Number of samples to acquire.
            sampling_rate: Sampling frequency in Hz.

        Returns:
            FunctionTask that performs pulse measurement.
        """

        def job():
            result = self._run_hw_operation(
                lambda c: c.pulse_measure(num_samples=num_samples, sampling_rate=sampling_rate)
            )
            return {
                "ok": result.ok,
                "time": result.data.get("time"),
                "values": result.data.get("values"),
            }

        return make_task("Pulse Measure", job)

    def run_calibration_measure(
        self,
        verify_calibration: bool = False,
        verify_only: bool = False,
        amp_channels: list[str] | None = None,
        speed_preset: str = "normal",
        single_range: str | None = None,
    ) -> FunctionTask | None:
        """Run calibration measurement with Keithley.

        Delegates to SUController.calibration_measure for the actual workflow.
        Does NOT pre-connect to SU - SUCalibrationMeasure creates its own
        connections to SMU, SU, and Keithley internally.

        Emits data_chunk signals for live progress:
        - {"type": "cal_range", ...} when a range starts/finishes
        - {"type": "cal_point", ...} for each measured point

        Args:
            verify_calibration: If True, also verify the calibration.
            verify_only: If True, skip raw measurement and only run
                the verification pass (writes to raw_data_verify.h5).
            amp_channels: AMP channels to measure (default: all from device).
            speed_preset: "fast", "normal", or "precise".
            single_range: If set, amp_channel for single range measurement.

        Returns:
            FunctionTask that runs calibration measurements, or None if
            Keithley IP is not configured.
        """
        if not self._target_instrument_ip:
            return None

        def job():
            serial = self._targets.su_serial or self._get_serial() or "auto"
            folder_path = str(Path(f"calibration/su_calibration_sn{serial}").resolve())
            self._calibration_folder = folder_path

            # Keep a local controller ref, then release USB so
            # SUCalibrationMeasure can claim the devices itself
            with self._hw_lock:
                controller = self._controller or SUController()
                if self._su is not None:
                    with contextlib.suppress(OSError, RuntimeError):
                        self._su.disconnect()
                if self._mcu is not None:
                    with contextlib.suppress(OSError, RuntimeError):
                        self._mcu.disconnect()
                controller._su = None
                controller._mcu = None
                self._su = None
                self._mcu = None
                self._controller = None
                self._connected = False

            result = controller.calibration_measure(
                keithley_ip=self._target_instrument_ip,
                smu_serial=self._targets.smu_serial or None,
                smu_interface=self._targets.smu_interface or None,
                su_serial=self._targets.su_serial or None,
                su_interface=self._targets.su_interface or None,
                folder_path=folder_path,
                verify_calibration=verify_calibration,
                verify_only=verify_only,
                amp_channels=amp_channels,
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
            except (OSError, RuntimeError) as e:
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
        single_range: str | None = None,
    ) -> FunctionTask:
        """Run calibration fit and optionally write to EEPROM.

        Delegates to SUController.calibration_fit for the actual workflow.

        Args:
            draw_plot: If True, generate calibration plots.
            auto_calibrate: If True, write calibration to EEPROM.
            model_type: Model to save ("linear" or "gp").
            verify_calibration: If True, load verification data too.
            single_range: If set, amp_channel to fit only that range
                while preserving other ranges.

        Returns:
            FunctionTask that fits calibration data.
        """

        def job():
            folder_path = self._resolve_calibration_folder()
            result = self._run_hw_operation(
                lambda c: c.calibration_fit(
                    folder_path=folder_path,
                    draw_plot=draw_plot,
                    auto_calibrate=auto_calibrate,
                    model_type=model_type,
                    verify_calibration=verify_calibration,
                    single_range=single_range,
                )
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
            controller = self._controller or SUController()
            status = controller.get_calibration_status(folder)
            return {"ok": True, "calibration_status": status}

        return make_task("Load Cal Status", job)

    def run_delete_calibration_ranges(
        self,
        ranges: list[str],
        target: str = "raw",
    ) -> FunctionTask | None:
        """Delete specific ranges from calibration HDF5 files.

        Args:
            ranges: List of amp_channel names to delete.
            target: "raw", "verify", or "both".

        Returns:
            FunctionTask, or None if no calibration folder.
        """
        folder = self._resolve_calibration_folder()
        if not folder or not Path(folder).exists():
            return None

        def job():
            controller = self._controller or SUController()
            result = controller.delete_calibration_ranges(folder, ranges, target)
            return {"ok": result.ok, "deleted": (result.data or {}).get("deleted", 0)}

        return make_task("Delete Cal Data", job)

    def run_clear_calibration_file(self, target: str = "raw") -> FunctionTask | None:
        """Delete an entire calibration HDF5 file.

        Args:
            target: "raw" or "verify".

        Returns:
            FunctionTask, or None if no calibration folder.
        """
        folder = self._resolve_calibration_folder()
        if not folder or not Path(folder).exists():
            return None

        def job():
            controller = self._controller or SUController()
            result = controller.clear_calibration_file(folder, target)
            return {"ok": result.ok, "file": (result.data or {}).get("file", "")}

        return make_task("Clear Cal File", job)

    def run_clear_fitted_data(self) -> FunctionTask | None:
        """Delete fitted/analysis calibration artifacts.

        Removes aggregated HDF5 files, model files, and figures directory.

        Returns:
            FunctionTask, or None if no calibration folder.
        """
        folder = self._resolve_calibration_folder()
        if not folder or not Path(folder).exists():
            return None

        def job():
            controller = self._controller or SUController()
            result = controller.clear_fitted_data(folder)
            return {
                "ok": result.ok,
                "deleted": (result.data or {}).get("deleted", []),
            }

        return make_task("Clear Fitted Data", job)

    def run_calibrate(self, model: str = "linear") -> FunctionTask:
        """Run calibration fit (called by calibration page Run Calibration button)."""
        return self.run_calibration_fit(
            draw_plot=True,
            auto_calibrate=False,
            model_type=model,
        )

    def run_calibration_verify(self, num_points: int = 10) -> FunctionTask | None:
        """Verify calibration by re-measuring (verification pass only)."""
        return self.run_calibration_measure(verify_only=True)

    def run_save_config(self) -> FunctionTask:
        """Save current channel configuration to device EEPROM.

        Returns:
            FunctionTask that saves configuration.
        """

        def job():
            result = self._run_hw_operation(lambda c: c.save_channel_config())
            return {"ok": result.ok, "message": result.message}

        return make_task("Save Config", job)

    def run_load_config(self) -> FunctionTask:
        """Load channel configuration from device EEPROM.

        Returns:
            FunctionTask that loads configuration.
        """

        def job():
            result = self._run_hw_operation(lambda c: c.load_channel_config())
            return {"ok": result.ok, "data": result.data, "message": result.message}

        return make_task("Load Config", job)

    def connect_only(self) -> FunctionTask:
        """Connect to SU hardware without additional operations.

        Returns:
            FunctionTask that establishes hardware connection.
        """

        def job():
            with self._hw_lock:
                self._ensure_connected()
                return {"serial": self._get_serial(), "ok": True}

        return make_task("Connect", job)
