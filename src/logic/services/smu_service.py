"""SourceMeasureUnitService for SMU hardware communication and task management."""

from __future__ import annotations

import functools
import subprocess
import threading
import warnings
from dataclasses import dataclass
from pathlib import Path

import matplotlib
from dpi import DPISourceMeasureUnit
from PySide6.QtCore import QObject, Signal

from src.logging_config import get_logger
from src.logic.artifact_manager import ArtifactManager
from src.logic.qt_workers import FunctionTask, make_task

matplotlib.use("Agg")

logger = get_logger(__name__)


@dataclass
class SMUTargetIds:
    """Target identifiers for SMU and SU hardware."""

    smu_serial: int = 0
    smu_interface: int = 0
    su_serial: int = 0
    su_interface: int = 0


class SourceMeasureUnitService(QObject):
    """Owns SMU hardware connections and runs script commands in worker threads.

    This service mirrors the original script behavior and exposes thread-friendly
    methods that return FunctionTask. Each method ensures the hardware is connected
    (autodetecting if needed) and routes log output to the returned signals.
    """

    connectedChanged = Signal(bool)
    inputRequested = Signal(str)
    keithleyVerified = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        logger.debug("SourceMeasureUnitService initializing")
        self._target_keithley_ip: str | None = None
        self._targets: SMUTargetIds = SMUTargetIds()
        self._smu: DPISourceMeasureUnit | None = None
        self._connected: bool = False
        self._keithley_verified_state: bool = False
        self._hw_lock = threading.Lock()
        self._artifact_manager = ArtifactManager()
        self._calibration_folder: str = ""

        # Input redirection
        self._input_event = threading.Event()
        self._input_value: str = ""
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
        self._target_keithley_ip = keithley_ip or getattr(self, "_target_keithley_ip", "")
        self._targets = SMUTargetIds(smu_serial, smu_interface, su_serial, su_interface)

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
    def smu_serial(self) -> int | None:
        """Return the SMU serial number if connected."""
        return self._smu.get_serial() if self._smu else None

    # ---- Internals ----
    def _ensure_connected(self) -> None:
        """Ensure SMU hardware is connected."""
        if self._connected and self._smu:
            return

        smu_serial = self._targets.smu_serial
        smu_if = self._targets.smu_interface

        if smu_serial == 0:
            # Autodetect SMU
            self._smu = DPISourceMeasureUnit(autoinit=True)
        else:
            self._smu = DPISourceMeasureUnit(serial=smu_serial, interface=smu_if)

        self._connected = True
        logger.info(f"SMU connected: serial={self._smu.get_serial()}")
        self.connectedChanged.emit(True)

    def _artifact_dir(self) -> str:
        """Returns the path to the directory where artifacts are saved."""
        serial = self._smu.get_serial() if self._smu else 0
        return self._artifact_manager.get_artifact_dir(serial)

    def _collect_artifacts(self) -> list[str]:
        """Collect all artifact files for the current SMU."""
        serial = self._smu.get_serial() if self._smu else 0
        return self._artifact_manager.collect_artifacts(serial)

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
                # Create SMU with autoinit for fresh device
                smu = DPISourceMeasureUnit(autoinit=True)
                smu.set_eeprom_default_values()
                smu.initNewDevice(
                    serial=serial,
                    processorType=processor_type,
                    connectorType=connector_type,
                )
                logger.info(f"SMU initialized with serial={serial}")
                return {"serial": serial, "ok": True}

        return make_task("hw_setup", job)

    def run_verify(self) -> FunctionTask:
        """Run hardware verification (calibrate_eeprom).

        Returns:
            FunctionTask that verifies hardware configuration.
        """

        def job():
            with self._hw_lock:
                self._ensure_connected()
                self._smu.calibrate_eeprom()
                logger.info("SMU EEPROM calibration complete")
                return {"ok": True}

        return make_task("verify", job)

    @require_keithley_ip
    def run_calibration_measure(
        self,
        vsmu_mode: bool | None = None,
        verify_calibration: bool = False,
    ) -> FunctionTask:
        """Run calibration measurement with Keithley.

        Args:
            vsmu_mode: True for VSMU mode, False for normal, None for both.
            verify_calibration: If True, also verify the calibration.

        Returns:
            FunctionTask that runs calibration measurements.
        """
        # Import here to avoid issues if symlink doesn't exist yet
        from dpi.utilities import DPILogger
        from dpisourcemeasureunit.calibration import SMUCalibrationMeasure

        def job():
            serial = self._smu.get_serial() if self._smu else 0
            folder_path = f"calibration/smu_calibration_sn{serial}"
            self._calibration_folder = folder_path

            scm = SMUCalibrationMeasure(
                self._target_keithley_ip,
                self._targets.smu_serial or None,
                self._targets.smu_interface or None,
                self._targets.su_serial or None,
                self._targets.su_interface or None,
                DPILogger.VERBOSE,
            )

            verify_list = [False, True] if verify_calibration else [False]

            for verify in verify_list:
                scm.data = []
                scm.measure_all_ranges(
                    vsmu_mode=vsmu_mode, verify_calibration=verify, current_values=None
                )
                filename = "raw_data_verify.h5" if verify else "raw_data.h5"
                scm.save_measurement(folder_path=folder_path, file_name=filename, append_data=True)

            scm.cleanup()
            logger.info(f"Calibration measurement complete: {folder_path}")
            return {"ok": True, "folder": folder_path, "artifacts": self._collect_artifacts()}

        return make_task("calibration_measure", job)

    def run_calibration_fit(
        self, draw_plot: bool = True, auto_calibrate: bool = True
    ) -> FunctionTask:
        """Run calibration fit and optionally write to EEPROM.

        Args:
            draw_plot: If True, generate calibration plots.
            auto_calibrate: If True, write calibration to EEPROM.

        Returns:
            FunctionTask that fits calibration data.
        """
        from dpi.utilities import DPILogger
        from dpisourcemeasureunit.calibration import SMUCalibrationFit

        def job():
            with self._hw_lock:
                self._ensure_connected()

                serial = self._smu.get_serial() if self._smu else 0
                folder_path = self._calibration_folder or f"calibration/smu_calibration_sn{serial}"

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
                    self._smu.calibrate_eeprom(folder_path=Path(folder_path))
                    logger.info("Calibration written to EEPROM")

                logger.info(f"Calibration fit complete: {folder_path}")
                return {"ok": True, "artifacts": self._collect_artifacts()}

        return make_task("calibration_fit", job)

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
