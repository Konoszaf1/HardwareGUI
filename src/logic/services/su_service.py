"""SamplingUnitService for SU hardware communication and task management.

This service owns connection lifecycle and coordinates threaded hardware operations
by delegating to SUController for actual device interactions.
"""

from __future__ import annotations

from dataclasses import dataclass

import matplotlib
from dpi import DPIMainControlUnit, DPISamplingUnit

from src.logging_config import get_logger
from src.logic.controllers.su_controller import SUController
from src.logic.qt_workers import FunctionTask, make_task
from src.logic.services.base_service import BaseHardwareService

matplotlib.use("Agg")

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
        return self._controller

    def _get_serial(self) -> int:
        """Get the actual SU serial, preferring _serial over serial."""
        if self._su is None:
            return 0
        return getattr(self._su, "_serial", None) or self._su.serial or 0

    # ---- Internals ----
    def _ensure_connected(self) -> None:
        """Ensure SU hardware is connected and controller is initialized."""
        if self._connected and self._su and self._controller:
            return

        su_serial = self._targets.su_serial
        su_if = self._targets.su_interface

        if su_serial == 0:
            # Autodetect SU
            self._su = DPISamplingUnit(autoinit=True)
        else:
            self._su = DPISamplingUnit(serial=su_serial, interface=su_if)

        # Initialize MCU for synchronized operations
        try:
            self._mcu = DPIMainControlUnit(autoinit=True)
        except Exception as e:
            logger.warning("MCU not available: %s", e)
            self._mcu = None

        # Create controller with hardware instances
        self._controller = SUController(su=self._su, mcu=self._mcu)

        self._connected = True
        logger.info("SU connected: serial=%s", self._get_serial())
        self.connectedChanged.emit(True)

    def _disconnect(self) -> None:
        """Tear down SU hardware connections."""
        if self._su:
            try:
                self._su.disconnect()
            except Exception:
                pass
            self._su = None
        if self._mcu:
            try:
                self._mcu.disconnect()
            except Exception:
                pass
            self._mcu = None
        self._controller = None

    def _artifact_dir(self) -> str:
        """Returns the path to the directory where artifacts are saved."""
        return f"calibration/su_calibration_sn{self._get_serial()}"

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
            with self._hw_lock:
                self._ensure_connected()
                result = self._controller.perform_autocalibration()
                return {"ok": result.ok, "serial": result.serial, "message": result.message}

        return make_task("Verify", job)

    def run_temperature_read(self) -> FunctionTask:
        """Read SU temperature.

        Returns:
            FunctionTask that reads temperature.
        """

        def job():
            with self._hw_lock:
                self._ensure_connected()
                result = self._controller.read_temperature()
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
            with self._hw_lock:
                self._ensure_connected()
                result = self._controller.single_shot_measure(
                    dac_voltage=dac_voltage,
                    source=source,
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
            with self._hw_lock:
                self._ensure_connected()
                result = self._controller.transient_measure(
                    measurement_time=measurement_time,
                    sampling_rate=sampling_rate,
                    trigger=trigger,
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
            with self._hw_lock:
                self._ensure_connected()
                result = self._controller.pulse_measure(
                    num_samples=num_samples,
                    sampling_rate=sampling_rate,
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
    ) -> FunctionTask:
        """Run calibration measurement with Keithley.

        Delegates to SUController.calibration_measure for the actual workflow.
        Does NOT pre-connect to SU — SUCalibrationMeasure creates its own
        connections to SMU, SU, and Keithley internally.

        Args:
            verify_calibration: If True, also verify the calibration.

        Returns:
            FunctionTask that runs calibration measurements, or None if
            Keithley IP is not configured.
        """
        if not self._target_instrument_ip:
            return None

        def job():
            serial = self._targets.su_serial or self._get_serial() or "auto"
            folder_path = f"calibration/su_calibration_sn{serial}"
            self._calibration_folder = folder_path

            def on_point(data: dict) -> None:
                task.signals.data_chunk.emit(data)

            # Keep a local controller ref, then release USB so
            # SUCalibrationMeasure can claim the devices itself
            with self._hw_lock:
                controller = self._controller or SUController()
                if self._su is not None:
                    try:
                        self._su.disconnect()
                    except Exception:
                        pass
                if self._mcu is not None:
                    try:
                        self._mcu.disconnect()
                    except Exception:
                        pass
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
                on_point_measured=on_point,
            )
            return {
                "ok": result.ok,
                "message": result.message,
                "folder": folder_path,
                "artifacts": self._safe_collect_artifacts(),
            }

        task = make_task("Calibration: Measure", job)
        return task

    def run_calibration_fit(
        self,
        draw_plot: bool = True,
        auto_calibrate: bool = True,
        model_type: str = "linear",
    ) -> FunctionTask:
        """Run calibration fit and optionally write to EEPROM.

        Delegates to SUController.calibration_fit for the actual workflow.

        Args:
            draw_plot: If True, generate calibration plots.
            auto_calibrate: If True, write calibration to EEPROM.
            model_type: Model to save ("linear" or "gp").

        Returns:
            FunctionTask that fits calibration data.
        """

        def job():
            with self._hw_lock:
                self._ensure_connected()

                serial = self._get_serial()
                folder_path = self._calibration_folder or f"calibration/su_calibration_sn{serial}"

                result = self._controller.calibration_fit(
                    folder_path=folder_path,
                    draw_plot=draw_plot,
                    auto_calibrate=auto_calibrate,
                    model_type=model_type,
                )
                return {
                    "ok": result.ok,
                    "message": result.message,
                    "artifacts": self._safe_collect_artifacts(),
                }

        return make_task("Calibration: Fit", job)

    def run_calibrate(self, model: str = "linear") -> FunctionTask:
        """Run calibration fit (called by calibration page Run Calibration button).

        Args:
            model: Calibration model type ("linear" or "gp").

        Returns:
            FunctionTask that fits calibration data.
        """
        return self.run_calibration_fit(draw_plot=True, auto_calibrate=True, model_type=model)

    def run_calibration_verify(self, num_points: int = 10) -> FunctionTask:
        """Verify calibration by re-measuring (called by calibration page Verify button).

        Args:
            num_points: Number of verification points (informational).

        Returns:
            FunctionTask that verifies calibration.
        """
        return self.run_calibration_measure(verify_calibration=True)

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
