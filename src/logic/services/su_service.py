"""SamplingUnitService for SU hardware communication and task management.

This service owns connection lifecycle and coordinates threaded hardware operations
by delegating to SUController for actual device interactions.
"""

from __future__ import annotations

import functools
import subprocess
import threading
import warnings
from dataclasses import dataclass

import matplotlib
from dpi import DPIMainControlUnit, DPISamplingUnit
from PySide6.QtCore import QObject, Signal

from src.logging_config import get_logger
from src.logic.artifact_manager import ArtifactManager
from src.logic.controllers.su_controller import SUController
from src.logic.qt_workers import FunctionTask, make_task

matplotlib.use("Agg")

logger = get_logger(__name__)


@dataclass
class SUTargetIds:
    """Target identifiers for SU and SMU hardware."""

    su_serial: int = 0
    su_interface: int = 0
    smu_serial: int = 0
    smu_interface: int = 0


class SamplingUnitService(QObject):
    """Owns SU hardware connections and runs script commands in worker threads.

    This service manages connection lifecycle and threading while delegating
    actual hardware operations to SUController.
    """

    connectedChanged = Signal(bool)
    inputRequested = Signal(str)
    keithleyVerified = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        logger.debug("SamplingUnitService initializing")
        self._target_keithley_ip: str | None = None
        self._targets: SUTargetIds = SUTargetIds()
        self._su: DPISamplingUnit | None = None
        self._mcu: DPIMainControlUnit | None = None
        self._controller: SUController | None = None
        self._connected: bool = False
        self._keithley_verified_state: bool = False
        self._hw_lock = threading.Lock()
        self._artifact_manager = ArtifactManager()
        self._calibration_folder: str = ""

        # Input redirection
        self._input_event = threading.Event()
        self._input_value: str = ""
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
        self._target_keithley_ip = keithley_ip or getattr(self, "_target_keithley_ip", "")
        self._targets = SUTargetIds(su_serial, su_interface, smu_serial, smu_interface)

    def set_keithley_ip(self, ip: str) -> None:
        """Set the Keithley IP address.

        Resets verification state if the IP changes.

        Args:
            ip: New IP address for the Keithley.
        """
        if not self._target_keithley_ip or self._target_keithley_ip != ip:
            self._target_keithley_ip = ip
            self.set_keithley_verified(False)

    def set_keithley_verified(self, verified: bool) -> None:
        """Update Keithley verification state and emit signal if changed.

        Args:
            verified: Whether the Keithley connection is verified.
        """
        if self._keithley_verified_state != verified:
            self._keithley_verified_state = verified
            self.keithleyVerified.emit(verified)

    def require_keithley_ip(func):
        """Decorator to check if Keithley IP is set before running a task.

        Returns None with a warning if Keithley IP is not configured.
        Callers should check for None return values.
        """

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if not getattr(self, "_target_keithley_ip", ""):
                warnings.warn(
                    f"{func.__name__}() requires Keithley IP to be configured. "
                    "Call set_keithley_ip() first.",
                    stacklevel=2,
                )
                return None
            with self._hw_lock:
                self._ensure_connected()
                return func(self, *args, **kwargs)

        return wrapper

    def ping_keithley(self) -> bool:
        """Ping the Keithley IP address to verify connectivity.

        Returns:
            True if the Keithley is reachable, False otherwise.
        """
        logger.info(f"Pinging Keithley at {self._target_keithley_ip}")
        try:
            subprocess.check_call(
                ["ping", "-c", "1", "-W", "1", self._target_keithley_ip],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info("Keithley ping successful")
            self.set_keithley_verified(True)
            return True
        except subprocess.CalledProcessError:
            logger.warning(f"Keithley ping failed for {self._target_keithley_ip}")
            self.set_keithley_verified(False)
            return False

    # ---- Accessors ----
    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def is_keithley_verified(self) -> bool:
        return self._keithley_verified_state

    @property
    def su_serial(self) -> int | None:
        """Return the SU serial number if connected."""
        return self._su.getSerial() if self._su else None

    @property
    def controller(self) -> SUController:
        """Return the SUController instance, creating if needed."""
        if self._controller is None:
            self._ensure_connected()
        return self._controller

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
            logger.warning(f"MCU not available: {e}")
            self._mcu = None

        # Create controller with hardware instances
        self._controller = SUController(su=self._su, mcu=self._mcu)

        self._connected = True
        logger.info(f"SU connected: serial={self._su.getSerial()}")
        self.connectedChanged.emit(True)

    @property
    def artifact_dir(self) -> str:
        """Return the absolute path to the calibration artifact directory."""
        serial = self._su.getSerial() if self._su else 0
        return self._artifact_manager.get_artifact_dir(
            f"calibration/su_calibration_sn{serial}"
        )

    def _artifact_dir(self) -> str:
        """Returns the path to the directory where artifacts are saved."""
        return self.artifact_dir

    def _collect_artifacts(self) -> list[str]:
        """Collect all artifact files for the current SU."""
        serial = self._su.getSerial() if self._su else 0
        return self._artifact_manager.collect_artifacts(
            f"calibration/su_calibration_sn{serial}"
        )

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

        return make_task("hw_setup", job)

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

        return make_task("verify", job)

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

        return make_task("temperature", job)

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

        return make_task("single_shot", job)

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

        return make_task("transient", job)

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

        return make_task("pulse", job)

    @require_keithley_ip
    def run_calibration_measure(
        self,
        verify_calibration: bool = False,
    ) -> FunctionTask:
        """Run calibration measurement with Keithley.

        Delegates to SUController.calibration_measure for the actual workflow.

        Args:
            verify_calibration: If True, also verify the calibration.

        Returns:
            FunctionTask that runs calibration measurements.
        """

        def job():
            serial = self._su.getSerial() if self._su else 0
            folder_path = f"calibration/su_calibration_sn{serial}"
            self._calibration_folder = folder_path

            result = self._controller.calibration_measure(
                keithley_ip=self._target_keithley_ip,
                smu_serial=self._targets.smu_serial or None,
                smu_interface=self._targets.smu_interface or None,
                su_serial=self._targets.su_serial or None,
                su_interface=self._targets.su_interface or None,
                folder_path=folder_path,
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

        Delegates to SUController.calibration_fit for the actual workflow.

        Args:
            draw_plot: If True, generate calibration plots.
            auto_calibrate: If True, write calibration to EEPROM.

        Returns:
            FunctionTask that fits calibration data.
        """

        def job():
            with self._hw_lock:
                self._ensure_connected()

                serial = self._su.getSerial() if self._su else 0
                folder_path = self._calibration_folder or f"calibration/su_calibration_sn{serial}"

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

    def connect_only(self) -> FunctionTask:
        """Connect to SU hardware without additional operations.

        Returns:
            FunctionTask that establishes hardware connection.
        """

        def job():
            with self._hw_lock:
                self._ensure_connected()
                return {"serial": self._su.getSerial() if self._su else None, "ok": True}

        return make_task("connect", job)
