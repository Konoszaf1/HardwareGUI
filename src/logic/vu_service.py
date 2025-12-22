from __future__ import annotations

import glob
import os
import re
import subprocess
import threading
from dataclasses import dataclass
from typing import Dict, List, Optional
from PySide6.QtCore import QObject, Signal

from src.logic.qt_workers import make_task, FunctionTask
# noinspection PyUnusedImports
import dpi # required to avoid circular imports
from dpivoltageunit.dpivoltageunit import DPIVoltageUnit
from dpimaincontrolunit.dpimaincontrolunit import DPIMainControlUnit
import vxi11

import matplotlib
matplotlib.use("Agg")
import setup_cal


@dataclass
class TargetIds:
    vu_serial: int = 0
    vu_interface: int = 0
    mcu_serial: int = 0
    mcu_interface: int = 0

class VoltageUnitService(QObject):
    """Owns hardware connections and runs script commands in worker threads.

    This service mirrors the original script behavior and exposes thread-friendly
    methods that return FunctionTask. Each method ensures the hardware is connected
    (autodetecting if needed) and routes log output to the returned signals.
    """

    connectedChanged = Signal(bool)
    inputRequested = Signal(str)
    scopeVerified = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        self._target_scope_ip: str | None = None
        self._targets: TargetIds = TargetIds()
        self._vu: Optional[DPIVoltageUnit] = None
        self._mcu: Optional[DPIMainControlUnit] = None
        self._scope: Optional[vxi11.Instrument] = None
        # Local coeffs dict; we alias the script module's global to this dict
        self._coeffs: Dict[str, List[float]] = {"CH1": [1.0, 0.0], "CH2": [1.0, 0.0], "CH3": [1.0, 0.0]}
        self._connected: bool = False
        self._scope_verified_state: bool = False
        self._hw_lock = threading.Lock()
        
        # Input redirection
        self._input_event = threading.Event()
        self._input_value: str = ""

    # ---- Configuration targets ----
    def set_targets(self, scope_ip: str, vu_serial: int, vu_interface: int, mcu_serial: int, mcu_interface: int) -> None:
        self._target_scope_ip = scope_ip or getattr(self, "_target_scope_ip", "")
        self._targets = TargetIds(vu_serial, vu_interface, mcu_serial, mcu_interface)

    def set_scope_ip(self, ip: str) -> None:
        if not self._target_scope_ip or self._target_scope_ip != ip:
            self._target_scope_ip = ip
            self.set_scope_verified(False)

    def set_scope_verified(self, verified: bool) -> None:
        if self._scope_verified_state != verified:
            self._scope_verified_state = verified
            self.scopeVerified.emit(verified)

    def require_scope_ip(func):
        """Decorator to check if scope IP is set before running a task."""
        def wrapper(self, *args, **kwargs):
            if not getattr(self, "_target_scope_ip", ""):
                return None
            with self._hw_lock:
                self._ensure_connected()
                return func(self, *args, **kwargs)
        return wrapper

    def ping_scope(self) -> bool:
        """Pings the scope IP address. Returns True if reachable."""
        try:
            # -c 1: send 1 packet
            # -W 1: wait 1 second for response
            subprocess.check_call(
                ["ping", "-c", "1", "-W", "1", self._target_scope_ip],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.set_scope_verified(True)
            return True
        except subprocess.CalledProcessError:
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
    def coeffs(self) -> Dict[str, List[float]]:
        return self._coeffs

    # ---- Internals ----
    def _ensure_connected(self) -> None:
        """Mirror the box connection of the script."""
        if self._connected and self._vu and self._mcu and self._scope:
            return

        # Resolve serials that are zero via lsusb as in the script
        vu_serial = self._targets.vu_serial
        vu_if = self._targets.vu_interface
        mcu_serial = self._targets.mcu_serial
        mcu_if = self._targets.mcu_interface

        if vu_serial == 0 or mcu_serial == 0:
            # Linux-specific discovery, mirrors script
            vu = subprocess.check_output('lsusb -v | grep "Voltage Unit" -A1', shell=True, text=True)
            mu = subprocess.check_output('lsusb -v | grep "Main Control Unit" -A1', shell=True, text=True)
            vu_serial, vu_if = map(int, re.findall(r"s(\d{4})i(\d{2})", vu)[0])
            mcu_serial, mcu_if = map(int, re.findall(r"s(\d{4})i(\d{2})", mu)[0])

        # Create device objects
        self._vu = DPIVoltageUnit(serial=vu_serial, interface=vu_if, busaddress=vu_if)
        self._mcu = DPIMainControlUnit(serial=mcu_serial, interface=mcu_if)
        self._scope = vxi11.Instrument(self._target_scope_ip)

        # Sync script module globals and coeffs alias
        setup_cal.SCOPE_IP = self._target_scope_ip
        setup_cal.VU_SERIAL = vu_serial
        setup_cal.VU_INTERF = vu_if
        setup_cal.MU_SERIAL = mcu_serial
        setup_cal.MU_INTERF = mcu_if
        setup_cal.mcu = self._mcu
        setup_cal.scope = self._scope

        # Read baseline coefficients from the hardware
        self._coeffs = {}
        for ch in ("CH1", "CH2", "CH3"):
            self._coeffs[ch] = list(self._vu.get_correctionvalues(ch))
        setup_cal.coeffs = self._coeffs
        self._connected = True
        self.connectedChanged.emit(True)

    def _artifact_dir(self) -> str:
        """Returns the path to the directory where artifacts are saved."""
        return os.path.abspath(f"calibration_vu{setup_cal.VU_SERIAL}")  

    def _collect_artifacts(self) -> List[str]:
        paths: List[str] = []
        d = self._artifact_dir()
        for name in ("output.png", "ramp.png", "transient.png"):
            p = os.path.join(d, name)
            if os.path.exists(p):
                paths.append(p)
        # Also include any other PNGs the user might have produced
        paths.extend(sorted(glob.glob(os.path.join(d, "*.png"))))
        # Deduplicate while preserving order
        seen = set()
        unique: List[str] = []
        for p in paths:
            if p not in seen:
                unique.append(p)
                seen.add(p)
        return unique

    # ---- Public operations (threaded) ----
    @require_scope_ip
    def connect_and_read(self) -> FunctionTask:
        def job():
            self._ensure_connected()
            # Touch scope to read IDN (side effect: prints to log via worker capture)
            try:
                _ = self._scope.ask("*IDN?")
            except Exception:
                pass
            return {"coeffs": self._coeffs}

        return make_task("connect_and_read", job)

    @require_scope_ip
    def read_coefficients(self) -> FunctionTask:
        def job():
            self._ensure_connected()
            for ch in ("CH1", "CH2", "CH3"):
                self._coeffs[ch] = list(self._vu.get_correctionvalues(ch))
            return {"coeffs": self._coeffs}

        return make_task("read_coefficients", job)

    @require_scope_ip
    def reset_coefficients_ram(self) -> FunctionTask:
        def job():
            setup_cal.reset_coefficients(self._vu, self._scope, wait_input=False)
            return {"coeffs": self._coeffs}

        return make_task("reset_coefficients_ram", job)

    @require_scope_ip
    def write_coefficients_eeprom(self) -> FunctionTask:
        def job():
            self._ensure_connected()
            # Use the script function to persist current self._coeffs
            setup_cal.write_coefficients(self._vu, self._scope, wait_input=False)
            return {"coeffs": self._coeffs}

        return make_task("write_coefficients_eeprom", job)

    # ---- Guard ----
    @require_scope_ip
    def set_guard_signal(self) -> FunctionTask:
        def job():
            self._ensure_connected()
            self._vu.setOutputsGuardToSignal()
            return {"guard": "signal"}

        return make_task("guard_signal", job)

    @require_scope_ip
    def set_guard_ground(self) -> FunctionTask:
        def job():
            self._ensure_connected()
            self._vu.setOutputsGuardToGND()
            return {"guard": "ground"}

        return make_task("guard_ground", job)

    # ---- Tests and calibration ----
    @require_scope_ip
    def test_outputs(self) -> FunctionTask:
        def job():
            self._ensure_connected()
            ok = setup_cal.test_outputs(self._vu, self._scope)
            return {"ok": ok, "artifacts": self._collect_artifacts()}

        return make_task("test_outputs", job)

    @require_scope_ip
    def test_ramp(self) -> FunctionTask:
        def job():
            self._ensure_connected()
            ok = setup_cal.test_ramp(self._vu, self._scope)
            return {"ok": ok, "artifacts": self._collect_artifacts()}

        return make_task("test_ramp", job)

    @require_scope_ip
    def test_transient(self) -> FunctionTask:
        def job():
            self._ensure_connected()
            setup_cal.test_transient(self._vu, self._scope)
            return {"ok": True, "artifacts": self._collect_artifacts()}

        return make_task("test_transient", job)

    @require_scope_ip
    def test_all(self) -> FunctionTask:
        def job():
            self._ensure_connected()
            setup_cal.test_all(self._vu, self._scope)
            return {"ok": True, "artifacts": self._collect_artifacts()}

        return make_task("test_all", job)

    @require_scope_ip
    def autocal_python(self) -> FunctionTask:
        def job():
            self._ensure_connected()
            setup_cal.auto_calibrate(self._vu, self._scope)
            return {"ok": True, "artifacts": self._collect_artifacts(), "coeffs": self._coeffs}

        return make_task("autocal_python", job)

    @require_scope_ip
    def autocal_onboard(self) -> FunctionTask:
        def job():
            self._ensure_connected()
            setup_cal.autocal(self._vu, self._scope)
            # After onboard autocal, re-read coeffs
            for ch in ("CH1", "CH2", "CH3"):
                self._coeffs[ch] = list(self._vu.get_correctionvalues(ch))
            setup_cal.coeffs = self._coeffs
            return {"ok": True, "coeffs": self._coeffs, "artifacts": self._collect_artifacts()}

        return make_task("autocal_onboard", job)
