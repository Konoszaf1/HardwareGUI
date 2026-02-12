"""Simulated hardware services for running the application without real hardware.

These classes inherit from the real services and override hardware-facing methods
to produce simulated console output and artifacts instead of accessing real devices.

Usage:
    python src/main.py --simulation
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

from src.logging_config import get_logger
from src.logic.qt_workers import FunctionTask, make_task

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)

# =============================================================================
# SIMULATION ARTIFACT GENERATOR
# =============================================================================


class SimulationArtifactGenerator:
    """Generates fake calibration artifacts (matplotlib graphs) for simulation mode."""

    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def generate_artifacts(self, prefix: str, names: list[str]) -> list[str]:
        """Create matplotlib graph PNGs and return their paths."""
        import matplotlib.pyplot as plt
        import numpy as np

        plt.switch_backend("Agg")  # Switch to non-interactive backend for simulation

        artifact_dir = self.base_dir / f"calibration_{prefix}1"
        artifact_dir.mkdir(exist_ok=True)

        paths = []
        for name in names:
            path = artifact_dir / name
            fig, ax = plt.subplots(figsize=(8, 5))

            # Generate different graph types based on filename
            x = np.linspace(0, 10, 100)
            if "output" in name:
                # Step response / output test
                y1 = np.sin(x) + np.random.normal(0, 0.05, 100)
                y2 = np.sin(x + 0.5) + np.random.normal(0, 0.05, 100)
                y3 = np.sin(x + 1.0) + np.random.normal(0, 0.05, 100)
                ax.plot(x, y1, label="CH1", linewidth=1.5)
                ax.plot(x, y2, label="CH2", linewidth=1.5)
                ax.plot(x, y3, label="CH3", linewidth=1.5)
                ax.set_title("Output Test - Channel Response")
                ax.set_xlabel("Time (s)")
                ax.set_ylabel("Voltage (V)")
            elif "ramp" in name:
                # Ramp signal
                y = np.clip(x * 0.2, 0, 1.5) + np.random.normal(0, 0.02, 100)
                ax.plot(x, y, "b-", linewidth=2, label="Measured")
                ax.plot(x, np.clip(x * 0.2, 0, 1.5), "r--", linewidth=1, label="Ideal")
                ax.set_title("Ramp Test - Voltage Sweep")
                ax.set_xlabel("Time (s)")
                ax.set_ylabel("Voltage (V)")
            elif "transient" in name:
                # Transient response with overshoot
                y = 1 - np.exp(-x * 2) + 0.15 * np.exp(-x * 5) * np.sin(x * 10)
                y += np.random.normal(0, 0.01, 100)
                ax.plot(x, y, "g-", linewidth=1.5)
                ax.axhline(y=1.0, color="r", linestyle="--", alpha=0.5, label="Target")
                ax.set_title("Transient Response - Settling")
                ax.set_xlabel("Time (μs)")
                ax.set_ylabel("Normalized Amplitude")
            elif "calibration" in name or "fit" in name:
                # Calibration scatter with fit line
                x_pts = np.linspace(-1, 1, 20)
                y_pts = 1.02 * x_pts + 0.015 + np.random.normal(0, 0.02, 20)
                ax.scatter(x_pts, y_pts, alpha=0.7, label="Measured")
                ax.plot(x_pts, x_pts, "r-", linewidth=1.5, label="Ideal")
                ax.plot(x_pts, 1.02 * x_pts + 0.015, "g--", label="Fit")
                ax.set_title("Calibration - Input vs Output")
                ax.set_xlabel("Input Voltage (V)")
                ax.set_ylabel("Output Voltage (V)")
            else:
                # Generic sine wave
                y = np.sin(x) + np.random.normal(0, 0.05, 100)
                ax.plot(x, y)
                ax.set_title(f"Simulated: {name}")

            ax.legend(loc="best", fontsize=9)
            ax.grid(True, alpha=0.3)
            fig.tight_layout()
            fig.savefig(path, dpi=100, facecolor="white")
            plt.close(fig)

            paths.append(str(path))
        return paths


# Global artifact generator for simulation mode
_artifact_gen = SimulationArtifactGenerator()


# =============================================================================
# SIMULATED VOLTAGE UNIT SERVICE
# =============================================================================


class SimulatedVoltageUnitService(QObject):
    """Simulated VoltageUnitService that produces fake output without hardware."""

    connectedChanged = Signal(bool)
    inputRequested = Signal(str)
    scopeVerified = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        logger.info("[SIMULATION] VoltageUnitService initialized")
        self._target_scope_ip: str | None = None
        self._connected: bool = False
        self._scope_verified_state: bool = False
        self._coeffs: dict[str, list[float]] = {
            "CH1": [1.0, 0.0],
            "CH2": [1.0, 0.0],
            "CH3": [1.0, 0.0],
        }

    # ---- Configuration (same as real service) ----
    def set_targets(
        self,
        scope_ip: str,
        vu_serial: int,
        vu_interface: int,
        mcu_serial: int,
        mcu_interface: int,
    ) -> None:
        self._target_scope_ip = scope_ip
        logger.info(f"[SIMULATION] VU targets set: scope={scope_ip}, vu={vu_serial}")

    def set_scope_ip(self, ip: str) -> None:
        if self._target_scope_ip != ip:
            self._target_scope_ip = ip
            self.set_scope_verified(False)

    def set_scope_verified(self, verified: bool) -> None:
        if self._scope_verified_state != verified:
            self._scope_verified_state = verified
            self.scopeVerified.emit(verified)

    def ping_scope(self) -> bool:
        """Simulate successful ping."""
        logger.info(f"[SIMULATION] Ping scope at {self._target_scope_ip} - SUCCESS")
        print(f"Pinging {self._target_scope_ip}... OK (simulated)")
        self.set_scope_verified(True)
        return True

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def is_scope_verified(self) -> bool:
        return self._scope_verified_state

    @property
    def coeffs(self) -> dict[str, list[float]]:
        return self._coeffs

    @property
    def artifact_dir(self) -> str:
        return os.path.abspath("calibration_vu1")

    # ---- Simulated operations ----
    def _simulate_work(self, name: str, duration: float = 0.5) -> None:
        """Simulate work with console output."""
        print(f"\033[33m[SIMULATION] Starting {name}...\033[0m")
        time.sleep(duration)
        print(f"\033[32m[SIMULATION] {name} completed.\033[0m")

    def connect_and_read(self) -> FunctionTask:
        def job():
            self._simulate_work("connect_and_read", 0.3)
            self._connected = True
            self.connectedChanged.emit(True)
            print(f"Coefficients: {self._coeffs}")
            return {"coeffs": self._coeffs}

        return make_task("connect_and_read", job)

    def read_coefficients(self) -> FunctionTask:
        def job():
            self._simulate_work("read_coefficients", 0.2)
            return {"coeffs": self._coeffs}

        return make_task("read_coefficients", job)

    def reset_coefficients_ram(self) -> FunctionTask:
        def job():
            self._simulate_work("reset_coefficients_ram", 0.3)
            self._coeffs = {"CH1": [1.0, 0.0], "CH2": [1.0, 0.0], "CH3": [1.0, 0.0]}
            return {"coeffs": self._coeffs}

        return make_task("reset_coefficients_ram", job)

    def write_coefficients_eeprom(self) -> FunctionTask:
        def job():
            self._simulate_work("write_coefficients_eeprom", 0.5)
            print("Writing to EEPROM... Done")
            return {"coeffs": self._coeffs}

        return make_task("write_coefficients_eeprom", job)

    def set_guard_signal(self) -> FunctionTask:
        def job():
            self._simulate_work("guard_signal", 0.2)
            return {"guard": "signal"}

        return make_task("guard_signal", job)

    def set_guard_ground(self) -> FunctionTask:
        def job():
            self._simulate_work("guard_ground", 0.2)
            return {"guard": "ground"}

        return make_task("guard_ground", job)

    def test_outputs(self) -> FunctionTask:
        def job():
            self._simulate_work("test_outputs", 1.0)
            print("Testing outputs at: -0.75V, -0.5V, -0.25V, 0V, 0.25V, 0.5V, 0.75V")
            for v in [-0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75]:
                print(f"  Applied {v}V - Channel 1: OK, Channel 2: OK, Channel 3: OK")
            artifacts = _artifact_gen.generate_artifacts("vu", ["output.png"])
            return {"ok": True, "artifacts": artifacts}

        return make_task("test_outputs", job)

    def test_ramp(self) -> FunctionTask:
        def job():
            self._simulate_work("test_ramp", 1.5)
            print("Generating ramp signal...")
            print("  Channel 1: slope=20.0V/s, error=0.05%")
            print("  Channel 2: slope=-20.0V/s, error=0.08%")
            print("  Channel 3: slope=20.0V/s, error=0.03%")
            artifacts = _artifact_gen.generate_artifacts("vu", ["ramp.png"])
            return {"ok": True, "artifacts": artifacts}

        return make_task("test_ramp", job)

    def test_transient(self) -> FunctionTask:
        def job():
            self._simulate_work("test_transient", 1.0)
            print("Generating transient signal...")
            print("  Stress time: 10.0us, Recovery time: 10.0us")
            print("  Overshoot: 2.5%")
            artifacts = _artifact_gen.generate_artifacts("vu", ["transient.png"])
            return {"ok": True, "artifacts": artifacts}

        return make_task("test_transient", job)

    def test_all(self) -> FunctionTask:
        def job():
            self._simulate_work("test_all", 3.0)
            print("Running full test suite...")
            artifacts = _artifact_gen.generate_artifacts(
                "vu", ["output.png", "ramp.png", "transient.png"]
            )
            return {"ok": True, "artifacts": artifacts}

        return make_task("test_all", job)

    def autocal_python(self) -> FunctionTask:
        def job():
            self._simulate_work("autocal_python", 2.0)
            print("Running Python auto-calibration...")
            for i in range(5):
                print(f"  Iteration {i + 1}: offset error < 2mV")
            artifacts = _artifact_gen.generate_artifacts(
                "vu", ["output.png", "ramp.png", "transient.png"]
            )
            return {"ok": True, "artifacts": artifacts, "coeffs": self._coeffs}

        return make_task("autocal_python", job)

    def autocal_onboard(self) -> FunctionTask:
        def job():
            self._simulate_work("autocal_onboard", 2.0)
            print("Running onboard auto-calibration...")
            artifacts = _artifact_gen.generate_artifacts("vu", ["output.png"])
            return {"ok": True, "coeffs": self._coeffs, "artifacts": artifacts}

        return make_task("autocal_onboard", job)

    def connect_only(self) -> FunctionTask:
        def job():
            self._simulate_work("connect", 0.3)
            self._connected = True
            self.connectedChanged.emit(True)
            return {"serial": 0, "ok": True}

        return make_task("connect", job)


# =============================================================================
# SIMULATED SOURCE MEASURE UNIT SERVICE
# =============================================================================


class SimulatedSMUService(QObject):
    """Simulated SourceMeasureUnitService."""

    connectedChanged = Signal(bool)
    inputRequested = Signal(str)
    keithleyVerified = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        logger.info("[SIMULATION] SourceMeasureUnitService initialized")
        self._target_keithley_ip: str | None = None
        self._connected: bool = False
        self._keithley_verified_state: bool = False

    def set_targets(
        self,
        keithley_ip: str,
        smu_serial: int,
        smu_interface: int,
        su_serial: int,
        su_interface: int,
    ) -> None:
        self._target_keithley_ip = keithley_ip
        logger.info(f"[SIMULATION] SMU targets set: keithley={keithley_ip}")

    def set_keithley_ip(self, ip: str) -> None:
        if self._target_keithley_ip != ip:
            self._target_keithley_ip = ip
            self.set_keithley_verified(False)

    def set_keithley_verified(self, verified: bool) -> None:
        if self._keithley_verified_state != verified:
            self._keithley_verified_state = verified
            self.keithleyVerified.emit(verified)

    def ping_keithley(self) -> bool:
        logger.info(f"[SIMULATION] Ping Keithley at {self._target_keithley_ip} - SUCCESS")
        print(f"Pinging {self._target_keithley_ip}... OK (simulated)")
        self.set_keithley_verified(True)
        return True

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def is_keithley_verified(self) -> bool:
        return self._keithley_verified_state

    @property
    def smu_serial(self) -> int:
        return 1

    @property
    def artifact_dir(self) -> str:
        return os.path.abspath("calibration/smu_calibration_sn1")

    def _simulate_work(self, name: str, duration: float = 0.5) -> None:
        print(f"\033[33m[SIMULATION] Starting {name}...\033[0m")
        time.sleep(duration)
        print(f"\033[32m[SIMULATION] {name} completed.\033[0m")

    def run_hw_setup(
        self, serial: int, processor_type: str = "746", connector_type: str = "BNC"
    ) -> FunctionTask:
        def job():
            self._simulate_work("hw_setup", 1.0)
            print(f"Initializing SMU with serial={serial}")
            return {"serial": serial, "ok": True}

        return make_task("hw_setup", job)

    def run_verify(self) -> FunctionTask:
        def job():
            self._simulate_work("verify", 0.5)
            return {"ok": True}

        return make_task("verify", job)

    def run_calibration_measure(
        self, vsmu_mode: bool | None = None, verify_calibration: bool = False
    ) -> FunctionTask:
        def job():
            self._simulate_work("calibration_measure", 2.0)
            print("Measuring calibration data...")
            artifacts = _artifact_gen.generate_artifacts("smu", ["calibration.png"])
            return {"ok": True, "folder": "calibration/smu_1", "artifacts": artifacts}

        return make_task("calibration_measure", job)

    def run_calibration_fit(
        self, draw_plot: bool = True, auto_calibrate: bool = True
    ) -> FunctionTask:
        def job():
            self._simulate_work("calibration_fit", 1.5)
            print("Fitting calibration model...")
            artifacts = _artifact_gen.generate_artifacts("smu", ["fit_results.png"])
            return {"ok": True, "artifacts": artifacts}

        return make_task("calibration_fit", job)

    def run_measure(self, channel: str = "CH1") -> FunctionTask:
        return self.run_calibration_measure()

    def run_calibrate(self, model: str = "linear") -> FunctionTask:
        return self.run_calibration_fit(draw_plot=True, auto_calibrate=True)

    def run_calibration_verify(self, num_points: int = 10) -> FunctionTask:
        return self.run_calibration_measure(verify_calibration=True)

    def run_program_relais(self, **kwargs) -> FunctionTask:
        def job():
            self._simulate_work("program_relais", 0.5)
            print(f"Programming relais: {kwargs}")
            return {"ok": True}

        return make_task("program_relais", job)

    def connect_only(self) -> FunctionTask:
        def job():
            self._simulate_work("connect", 0.3)
            self._connected = True
            self.connectedChanged.emit(True)
            return {"serial": 1, "ok": True}

        return make_task("connect", job)


# =============================================================================
# SIMULATED SAMPLING UNIT SERVICE
# =============================================================================


class SimulatedSUService(QObject):
    """Simulated SamplingUnitService."""

    connectedChanged = Signal(bool)
    inputRequested = Signal(str)
    keithleyVerified = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        logger.info("[SIMULATION] SamplingUnitService initialized")
        self._target_keithley_ip: str | None = None
        self._connected: bool = False
        self._keithley_verified_state: bool = False

    def set_targets(
        self,
        keithley_ip: str,
        su_serial: int,
        su_interface: int,
        smu_serial: int,
        smu_interface: int,
    ) -> None:
        self._target_keithley_ip = keithley_ip
        logger.info(f"[SIMULATION] SU targets set: keithley={keithley_ip}")

    def set_keithley_ip(self, ip: str) -> None:
        if self._target_keithley_ip != ip:
            self._target_keithley_ip = ip
            self.set_keithley_verified(False)

    def set_keithley_verified(self, verified: bool) -> None:
        if self._keithley_verified_state != verified:
            self._keithley_verified_state = verified
            self.keithleyVerified.emit(verified)

    def ping_keithley(self) -> bool:
        logger.info(f"[SIMULATION] Ping Keithley at {self._target_keithley_ip} - SUCCESS")
        print(f"Pinging {self._target_keithley_ip}... OK (simulated)")
        self.set_keithley_verified(True)
        return True

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def is_keithley_verified(self) -> bool:
        return self._keithley_verified_state

    @property
    def su_serial(self) -> int:
        return 1

    @property
    def artifact_dir(self) -> str:
        return os.path.abspath("calibration/su_calibration_sn1")

    def _simulate_work(self, name: str, duration: float = 0.5) -> None:
        print(f"\033[33m[SIMULATION] Starting {name}...\033[0m")
        time.sleep(duration)
        print(f"\033[32m[SIMULATION] {name} completed.\033[0m")

    def run_hw_setup(
        self, serial: int, processor_type: str = "746", connector_type: str = "BNC"
    ) -> FunctionTask:
        def job():
            self._simulate_work("hw_setup", 1.0)
            print(f"Initializing SU with serial={serial}")
            return {"serial": serial, "ok": True}

        return make_task("hw_setup", job)

    def run_verify(self) -> FunctionTask:
        def job():
            self._simulate_work("verify", 0.5)
            return {"ok": True}

        return make_task("verify", job)

    def run_calibration_measure(self, verify_calibration: bool = False) -> FunctionTask:
        def job():
            self._simulate_work("calibration_measure", 2.0)
            print("Measuring calibration data...")
            artifacts = _artifact_gen.generate_artifacts("su", ["calibration.png"])
            return {"ok": True, "folder": "calibration/su_1", "artifacts": artifacts}

        return make_task("calibration_measure", job)

    def run_calibration_fit(
        self, draw_plot: bool = True, auto_calibrate: bool = True
    ) -> FunctionTask:
        def job():
            self._simulate_work("calibration_fit", 1.5)
            print("Fitting calibration model...")
            artifacts = _artifact_gen.generate_artifacts("su", ["fit_results.png"])
            return {"ok": True, "artifacts": artifacts}

        return make_task("calibration_fit", job)

    def run_calibrate(self, model: str = "linear") -> FunctionTask:
        return self.run_calibration_fit(draw_plot=True, auto_calibrate=True)

    def run_calibration_verify(self, num_points: int = 10) -> FunctionTask:
        return self.run_calibration_measure(verify_calibration=True)

    def connect_only(self) -> FunctionTask:
        def job():
            self._simulate_work("connect", 0.3)
            self._connected = True
            self.connectedChanged.emit(True)
            return {"serial": 1, "ok": True}

        return make_task("connect", job)
