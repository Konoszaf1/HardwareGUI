"""VoltageUnitService for hardware communication and task management.

This service owns connection lifecycle and coordinates threaded hardware operations
by delegating to VUController for actual device interactions.
"""

from __future__ import annotations

import functools
import re
import subprocess
import threading
import warnings
from dataclasses import dataclass

import dpi  # noqa: F401 - required to avoid circular imports
import matplotlib
import vxi11
from dpimaincontrolunit.dpimaincontrolunit import DPIMainControlUnit
from dpivoltageunit.dpivoltageunit import DPIVoltageUnit
from PySide6.QtCore import QObject, Signal

from src.logging_config import get_logger
from src.logic.artifact_manager import ArtifactManager
from src.logic.controllers.vu_controller import VUController
from src.logic.qt_workers import FunctionTask, make_task

matplotlib.use("Agg")

logger = get_logger(__name__)


@dataclass
class TargetIds:
    vu_serial: int = 0
    vu_interface: int = 0
    mcu_serial: int = 0
    mcu_interface: int = 0


class VoltageUnitService(QObject):
    """Owns VU hardware connections and runs script commands in worker threads.

    This service manages connection lifecycle and threading while delegating
    actual hardware operations to VUController.
    """

    connectedChanged = Signal(bool)
    inputRequested = Signal(str)
    scopeVerified = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        logger.debug("VoltageUnitService initializing")
        self._target_scope_ip: str | None = None
        self._targets: TargetIds = TargetIds()
        self._vu: DPIVoltageUnit | None = None
        self._mcu: DPIMainControlUnit | None = None
        self._scope: vxi11.Instrument | None = None
        self._controller: VUController | None = None
        self._connected: bool = False
        self._scope_verified_state: bool = False
        self._hw_lock = threading.Lock()
        self._artifact_manager = ArtifactManager()

        # Input redirection
        self._input_event = threading.Event()
        self._input_value: str = ""
        logger.info("VoltageUnitService initialized")

    # ---- Configuration targets ----
    def set_targets(
        self,
        scope_ip: str,
        vu_serial: int,
        vu_interface: int,
        mcu_serial: int,
        mcu_interface: int,
    ) -> None:
        """Set hardware connection targets.

        Args:
            scope_ip: IP address of the oscilloscope.
            vu_serial: VoltageUnit serial number.
            vu_interface: VoltageUnit interface number.
            mcu_serial: MainControlUnit serial number.
            mcu_interface: MainControlUnit interface number.
        """
        self._target_scope_ip = scope_ip or getattr(self, "_target_scope_ip", "")
        self._targets = TargetIds(vu_serial, vu_interface, mcu_serial, mcu_interface)

    def set_scope_ip(self, ip: str) -> None:
        """Set the oscilloscope IP address.

        Resets verification state if the IP changes.

        Args:
            ip: New IP address for the oscilloscope.
        """
        if not self._target_scope_ip or self._target_scope_ip != ip:
            self._target_scope_ip = ip
            self.set_scope_verified(False)

    def set_scope_verified(self, verified: bool) -> None:
        """Update scope verification state and emit signal if changed.

        Args:
            verified: Whether the scope connection is verified.
        """
        if self._scope_verified_state != verified:
            self._scope_verified_state = verified
            self.scopeVerified.emit(verified)

    def require_scope_ip(func):
        """Decorator to check if scope IP is set before running a task.

        Returns None with a warning if scope IP is not configured.
        Callers should check for None return values.
        """

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if not getattr(self, "_target_scope_ip", ""):
                warnings.warn(
                    f"{func.__name__}() requires scope IP to be configured. "
                    "Call set_scope_ip() first.",
                    stacklevel=2,
                )
                return None
            with self._hw_lock:
                self._ensure_connected()
                return func(self, *args, **kwargs)

        return wrapper

    def ping_scope(self) -> bool:
        """Ping the scope IP address to verify connectivity.

        Returns:
            True if the scope is reachable, False otherwise.
        """
        logger.info(f"Pinging scope at {self._target_scope_ip}")
        try:
            subprocess.check_call(
                ["ping", "-c", "1", "-W", "1", self._target_scope_ip],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info("Scope ping successful")
            self.set_scope_verified(True)
            return True
        except subprocess.CalledProcessError:
            logger.warning(f"Scope ping failed for {self._target_scope_ip}")
            self.set_scope_verified(False)
            return False

    # ---- Accessors ----
    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def is_scope_verified(self) -> bool:
        return self._scope_verified_state

    @property
    def vu_serial(self) -> int | None:
        """Return the VU serial number if connected."""
        return self._vu.get_serial() if self._vu else None

    @property
    def controller(self) -> VUController | None:
        """Return the VUController instance, creating if needed."""
        if self._controller is None and self._vu and self._mcu and self._scope:
            self._controller = VUController(
                vu=self._vu,
                mcu=self._mcu,
                scope=self._scope,
                vu_serial=self._vu.get_serial(),
                artifact_dir=self._artifact_dir(),
            )
        return self._controller

    @property
    def coeffs(self) -> dict[str, list[float]]:
        if self._controller:
            return self._controller.coeffs
        return {"CH1": [1.0, 0.0], "CH2": [1.0, 0.0], "CH3": [1.0, 0.0]}

    # ---- Internals ----
    def _ensure_connected(self) -> None:
        """Ensure VU hardware is connected and controller is initialized."""
        if self._connected and self._vu and self._mcu and self._scope and self._controller:
            return

        # Resolve serials that are zero via lsusb as in the script
        vu_serial = self._targets.vu_serial
        vu_if = self._targets.vu_interface
        mcu_serial = self._targets.mcu_serial
        mcu_if = self._targets.mcu_interface

        if vu_serial == 0 or mcu_serial == 0:
            # Linux-specific discovery, mirrors script
            vu = subprocess.check_output(
                'lsusb -v | grep "Voltage Unit" -A1', shell=True, text=True
            )
            mu = subprocess.check_output(
                'lsusb -v | grep "Main Control Unit" -A1', shell=True, text=True
            )
            vu_serial, vu_if = map(int, re.findall(r"s(\d{4})i(\d{2})", vu)[0])
            mcu_serial, mcu_if = map(int, re.findall(r"s(\d{4})i(\d{2})", mu)[0])

        # Create device objects
        self._vu = DPIVoltageUnit(serial=vu_serial, interface=vu_if, busaddress=vu_if)
        self._mcu = DPIMainControlUnit(serial=mcu_serial, interface=mcu_if)
        self._scope = vxi11.Instrument(self._target_scope_ip)

        # Create controller with hardware instances
        self._controller = VUController(
            vu=self._vu,
            mcu=self._mcu,
            scope=self._scope,
            vu_serial=vu_serial,
            artifact_dir=self._artifact_dir(),
        )

        self._connected = True
        logger.info(f"VU connected: serial={vu_serial}")
        self.connectedChanged.emit(True)

    def _artifact_dir(self) -> str:
        """Returns the path to the directory where artifacts are saved."""
        serial = self._vu.get_serial() if self._vu else 0
        return self._artifact_manager.get_artifact_dir(serial)

    def _collect_artifacts(self) -> list[str]:
        """Collect all artifact files for the current voltage unit."""
        serial = self._vu.get_serial() if self._vu else 0
        return self._artifact_manager.collect_artifacts(serial)

    # ---- Public operations (threaded) ----
    def connect_only(self) -> FunctionTask:
        """Connect to VU hardware without additional operations.

        Returns:
            FunctionTask that establishes hardware connection.
        """

        def job():
            with self._hw_lock:
                self._ensure_connected()
                return {
                    "serial": self._vu.get_serial() if self._vu else None,
                    "ok": True,
                }

        return make_task("connect", job)

    @require_scope_ip
    def connect_and_read(self) -> FunctionTask:
        def job():
            self._ensure_connected()
            try:
                idn = self._scope.ask("*IDN?")
                logger.debug(f"Scope IDN: {idn}")
            except Exception as e:
                logger.warning(f"Failed to read scope IDN: {e}")
            return {"coeffs": self.coeffs}

        return make_task("connect_and_read", job)

    @require_scope_ip
    def read_coefficients(self) -> FunctionTask:
        def job():
            result = self._controller.read_coefficients()
            return {"coeffs": result.data.get("coeffs", {}), "ok": result.ok}

        return make_task("read_coefficients", job)

    @require_scope_ip
    def reset_coefficients_ram(self) -> FunctionTask:
        def job():
            result = self._controller.reset_coefficients()
            return {"coeffs": result.data.get("coeffs", {}), "ok": result.ok}

        return make_task("reset_coefficients_ram", job)

    @require_scope_ip
    def write_coefficients_eeprom(self) -> FunctionTask:
        def job():
            result = self._controller.write_coefficients()
            return {"coeffs": result.data.get("coeffs", {}), "ok": result.ok}

        return make_task("write_coefficients_eeprom", job)

    # ---- Guard ----
    @require_scope_ip
    def set_guard_signal(self) -> FunctionTask:
        def job():
            result = self._controller.set_guard_signal()
            return {"guard": "signal", "ok": result.ok}

        return make_task("guard_signal", job)

    @require_scope_ip
    def set_guard_ground(self) -> FunctionTask:
        def job():
            result = self._controller.set_guard_ground()
            return {"guard": "ground", "ok": result.ok}

        return make_task("guard_ground", job)

    # ---- Tests and calibration ----
    @require_scope_ip
    def test_outputs(self) -> FunctionTask:
        def job():
            result = self._controller.test_outputs()
            return {"ok": result.ok, "artifacts": self._collect_artifacts()}

        return make_task("test_outputs", job)

    @require_scope_ip
    def test_ramp(self) -> FunctionTask:
        def job():
            result = self._controller.test_ramp()
            return {"ok": result.ok, "artifacts": self._collect_artifacts()}

        return make_task("test_ramp", job)

    @require_scope_ip
    def test_transient(self) -> FunctionTask:
        def job():
            result = self._controller.test_transient()
            return {"ok": result.ok, "artifacts": self._collect_artifacts()}

        return make_task("test_transient", job)

    @require_scope_ip
    def test_all(self) -> FunctionTask:
        def job():
            result = self._controller.test_all()
            return {"ok": result.ok, "artifacts": self._collect_artifacts()}

        return make_task("test_all", job)

    @require_scope_ip
    def autocal_python(self) -> FunctionTask:
        def job():
            result = self._controller.auto_calibrate()
            return {
                "ok": result.ok,
                "artifacts": self._collect_artifacts(),
                "coeffs": self.coeffs,
            }

        return make_task("autocal_python", job)

    @require_scope_ip
    def autocal_onboard(self) -> FunctionTask:
        def job():
            result = self._controller.perform_autocalibration()
            return {
                "ok": result.ok,
                "coeffs": self.coeffs,
                "artifacts": self._collect_artifacts(),
            }

        return make_task("autocal_onboard", job)
