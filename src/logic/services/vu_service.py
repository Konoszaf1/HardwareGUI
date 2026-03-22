"""VoltageUnitService for hardware communication and task management.

This service owns connection lifecycle and coordinates threaded hardware operations
by delegating to VUController for actual device interactions.
"""

from __future__ import annotations

import contextlib
import re
import subprocess
from dataclasses import dataclass

from PySide6.QtCore import Signal

import dpi  # noqa: F401 - required to avoid circular imports
import vxi11
from dpimaincontrolunit.dpimaincontrolunit import DPIMainControlUnit
from dpivoltageunit.dpivoltageunit import DPIVoltageUnit

from src.logging_config import get_logger
from src.logic.controllers.vu_controller import VUController
from src.logic.qt_workers import FunctionTask, make_task
from src.logic.services.base_service import BaseHardwareService

logger = get_logger(__name__)


@dataclass
class TargetIds:
    """Target identifiers for VU and MCU hardware.

    Attributes:
        vu_serial: VoltageUnit serial number (0 = autodetect).
        vu_interface: VoltageUnit interface number.
        mcu_serial: MainControlUnit serial number (0 = autodetect).
        mcu_interface: MainControlUnit interface number.
    """

    vu_serial: int = 0
    vu_interface: int = 0
    mcu_serial: int = 0
    mcu_interface: int = 0


class VoltageUnitService(BaseHardwareService):
    """Owns VU hardware connections and runs script commands in worker threads.

    This service manages connection lifecycle and threading while delegating
    actual hardware operations to VUController.
    """

    coeffsChanged = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        logger.debug("VoltageUnitService initializing")
        self._targets: TargetIds = TargetIds()
        self._vu: DPIVoltageUnit | None = None
        self._mcu: DPIMainControlUnit | None = None
        self._scope: vxi11.Instrument | None = None
        self._controller: VUController | None = None
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
        self._target_instrument_ip = scope_ip or getattr(self, "_target_instrument_ip", "")
        self._targets = TargetIds(vu_serial, vu_interface, mcu_serial, mcu_interface)

    # ---- Accessors ----
    @property
    def vu_serial(self) -> int | None:
        """Return the VU serial number if connected."""
        return self._vu.serial if self._vu else None

    @property
    def controller(self) -> VUController | None:
        """Return the VUController instance, creating if needed."""
        if self._controller is None and self._vu and self._mcu and self._scope:
            self._controller = VUController(
                vu=self._vu,
                mcu=self._mcu,
                scope=self._scope,
                vu_serial=self._vu.serial,
                artifact_dir=self._artifact_dir(),
            )
        return self._controller

    @property
    def coeffs(self) -> dict[str, list[float]]:
        if self._controller:
            return self._controller.coeffs
        return {"CH1": [1.0, 0.0], "CH2": [1.0, 0.0], "CH3": [1.0, 0.0]}

    # ---- Internals ----
    def _reconnect_scope(self) -> None:
        """Recreate the scope connection and update the controller reference.

        Mirrors setup_cal.py: create instrument + query *IDN? to open link.
        No custom timeout - use vxi11 default, same as the reference script.
        """
        old = self._scope
        self._scope = vxi11.Instrument(self._target_instrument_ip)
        self._scope.ask("*IDN?")
        if self._controller:
            self._controller._scope = self._scope
        if old:
            try:
                old.close()
            except Exception:
                try:
                    if old.client is not None:
                        old.client.close()
                except Exception:
                    pass
            finally:
                old.link = None
                old.client = None

    def _ensure_connected(self) -> None:
        """Ensure VU hardware is connected and controller is initialized."""
        if self._connected and self._vu and self._mcu and self._scope and self._controller:
            # Reuse existing connection - just like setup_cal.py does.
            # Each test sends *RST which resets the scope to a clean state.
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

        # Create device objects - wrap so partial failures clean up handles
        try:
            self._vu = DPIVoltageUnit(serial=vu_serial, interface=vu_if, busaddress=vu_if)
            self._mcu = DPIMainControlUnit(serial=mcu_serial, interface=mcu_if)
            self._scope = vxi11.Instrument(self._target_instrument_ip)
            # Immediately query *IDN? to open the VXI11 link and verify the
            # scope is responsive - mirrors setup_cal.py connection sequence.
            idn = self._scope.ask("*IDN?")
            print(f"Scope: {idn}")

            # Initialize DAC hardware (required after power glitch or firmware reset)
            self._vu.dacInit()

            # Create controller with hardware instances
            self._controller = VUController(
                vu=self._vu,
                mcu=self._mcu,
                scope=self._scope,
                vu_serial=vu_serial,
                artifact_dir=self._artifact_dir(),
            )
        except Exception:
            # Clean up any partially-created handles to avoid USB resource leaks
            self._disconnect()
            raise

        self._connected = True
        logger.info("VU connected: serial=%s", vu_serial)
        self.connectedChanged.emit(True)
        self._emit_coeffs()

        # Print connection summary
        self._print_connection_summary(vu_serial, vu_if, mcu_serial, mcu_if)

    def _print_connection_summary(
        self, vu_serial: int, vu_if: int, mcu_serial: int, mcu_if: int
    ) -> None:
        """Print a readable connection summary to stdout (captured by worker)."""
        assert self._vu is not None
        lines = [
            "",
            "\033[1m── Connection Summary ──\033[0m",
            f"  VU   s{vu_serial} i{vu_if}    MCU  s{mcu_serial} i{mcu_if}",
            f"  Scope  {self._target_instrument_ip}",
        ]
        # Channel info
        for ch in ("CH1", "CH2", "CH3"):
            try:
                amp = self._vu.get_Vout_Amplification(ch)
                coeffs = list(self._vu.get_correctionvalues(ch))
                k, d = coeffs[0], coeffs[1]
                lines.append(f"  {ch}  amp={amp:+.1f}  k={k:.6f}  d={d:.6f}")
            except Exception:
                lines.append(f"  {ch}  (could not read)")
        lines.append("")
        print("\n".join(lines))

    def _disconnect(self) -> None:
        """Tear down VU hardware connections."""
        if self._scope:
            try:
                self._scope.close()
            except Exception:
                try:
                    if self._scope.client is not None:
                        self._scope.client.close()
                except Exception:
                    pass
            self._scope = None
        if self._vu:
            with contextlib.suppress(Exception):
                self._vu.disconnect()
            self._vu = None
        if self._mcu:
            with contextlib.suppress(Exception):
                self._mcu.disconnect()
            self._mcu = None
        self._controller = None

    def _artifact_dir(self) -> str:
        """Returns the path to the directory where artifacts are saved."""
        serial = self._vu.serial if self._vu else 0
        return f"calibration_vu{serial}"

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
                    "serial": self._vu.serial if self._vu else None,
                    "ok": True,
                }

        return make_task("Connect", job)

    @BaseHardwareService.require_instrument_ip
    def connect_and_read(self) -> FunctionTask:
        def job():
            # _ensure_connected() already called by @require_instrument_ip
            assert self._scope is not None
            try:
                idn = self._scope.ask("*IDN?")
                print(f"Scope: {idn}")
            except Exception as e:
                print(f"Scope IDN query failed: {e}")
            return {"coeffs": self.coeffs}

        return make_task("Connect & Read Coefficients", job)

    def _emit_coeffs(self) -> None:
        """Emit coeffsChanged signal with current coefficients."""
        self.coeffsChanged.emit(self.coeffs)

    @BaseHardwareService.require_instrument_ip
    def read_coefficients(self) -> FunctionTask:
        def job():
            assert self._controller is not None
            result = self._controller.read_coefficients()
            self._emit_coeffs()
            return {"coeffs": result.data.get("coeffs", {}), "ok": result.ok}

        return make_task("Read Coefficients", job)

    @BaseHardwareService.require_instrument_ip
    def reset_coefficients_ram(self) -> FunctionTask:
        def job():
            assert self._controller is not None
            result = self._controller.reset_coefficients()
            self._emit_coeffs()
            return {"coeffs": result.data.get("coeffs", {}), "ok": result.ok}

        return make_task("Reset Coefficients (RAM)", job)

    @BaseHardwareService.require_instrument_ip
    def write_coefficients_eeprom(self) -> FunctionTask:
        def job():
            assert self._controller is not None
            result = self._controller.write_coefficients()
            self._emit_coeffs()
            return {"coeffs": result.data.get("coeffs", {}), "ok": result.ok}

        return make_task("Write Coefficients (EEPROM)", job)

    # ---- Guard ----
    @BaseHardwareService.require_instrument_ip
    def set_guard_signal(self) -> FunctionTask:
        def job():
            assert self._controller is not None
            result = self._controller.set_guard_signal()
            return {"guard": "signal", "ok": result.ok}

        return make_task("Set Guard → Signal", job)

    @BaseHardwareService.require_instrument_ip
    def set_guard_ground(self) -> FunctionTask:
        def job():
            assert self._controller is not None
            result = self._controller.set_guard_ground()
            return {"guard": "ground", "ok": result.ok}

        return make_task("Set Guard → Ground", job)

    # ---- Tests and calibration ----
    def _safe_collect_artifacts(self) -> list[str]:
        """Collect artifacts without crashing the job if directory is missing."""
        try:
            return self._collect_artifacts()
        except Exception as e:
            logger.warning("Artifact collection failed: %s", e)
            return []

    @BaseHardwareService.require_instrument_ip
    def test_outputs(self) -> FunctionTask:
        task = FunctionTask("Test: Outputs", lambda: None)

        def emit_chunk(data):
            task.signals.data_chunk.emit(data)

        def job():
            assert self._controller is not None
            result = self._controller.test_outputs(on_point_measured=emit_chunk)
            self._emit_coeffs()
            return {
                "ok": result.ok,
                "artifacts": self._safe_collect_artifacts(),
                "plot": result.data.get("plot") if result.data else None,
            }

        task.fn = job
        return task

    @BaseHardwareService.require_instrument_ip
    def test_ramp(self) -> FunctionTask:
        task = FunctionTask("Test: Ramp", lambda: None)

        def emit_chunk(data):
            task.signals.data_chunk.emit(data)

        def job():
            assert self._controller is not None
            result = self._controller.test_ramp(on_waveform=emit_chunk)
            self._emit_coeffs()
            return {
                "ok": result.ok,
                "artifacts": self._safe_collect_artifacts(),
                "plot": result.data.get("plot") if result.data else None,
            }

        task.fn = job
        return task

    @BaseHardwareService.require_instrument_ip
    def test_transient(self) -> FunctionTask:
        task = FunctionTask("Test: Transient", lambda: None)

        def emit_chunk(data):
            task.signals.data_chunk.emit(data)

        def job():
            assert self._controller is not None
            result = self._controller.test_transient(on_waveform=emit_chunk)
            return {
                "ok": result.ok,
                "artifacts": self._safe_collect_artifacts(),
                "plot": result.data.get("plot") if result.data else None,
            }

        task.fn = job
        return task

    @BaseHardwareService.require_instrument_ip
    def test_all(self) -> FunctionTask:
        task = FunctionTask("Test: All", lambda: None)

        def emit_chunk(data):
            task.signals.data_chunk.emit(data)

        def job():
            assert self._controller is not None
            result = self._controller.test_all(
                on_point_measured=emit_chunk,
                on_waveform=emit_chunk,
            )
            self._emit_coeffs()
            return {
                "ok": result.ok,
                "artifacts": self._safe_collect_artifacts(),
                "plots": result.data.get("plots") if result.data else None,
            }

        task.fn = job
        return task

    @BaseHardwareService.require_instrument_ip
    def autocal_python(self, max_iterations: int = 10) -> FunctionTask:
        task = FunctionTask("Autocalibration (Python)", lambda: None)

        def emit_chunk(data):
            task.signals.data_chunk.emit(data)

        def job():
            assert self._controller is not None
            result = self._controller.auto_calibrate(
                max_iterations=max_iterations,
                on_iteration=emit_chunk,
                on_point_measured=emit_chunk,
                on_waveform=emit_chunk,
            )
            self._emit_coeffs()
            return {
                "ok": result.ok,
                "artifacts": self._safe_collect_artifacts(),
                "coeffs": self.coeffs,
                "plot": result.data.get("plot") if result.data else None,
            }

        task.fn = job
        return task
