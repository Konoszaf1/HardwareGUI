"""Base class for hardware services with shared lifecycle management.

Provides the common infrastructure used by all hardware services:
signal declarations, instrument IP verification, ping, connection guard
decorator, threading lock, and artifact management.
"""

from __future__ import annotations

import functools
import subprocess
import threading
import warnings
from abc import abstractmethod

from PySide6.QtCore import QObject, Signal

from src.logging_config import get_logger
from src.logic.artifact_manager import ArtifactManager
from src.logic.network_discovery import discover_instruments
from src.logic.qt_workers import FunctionTask, make_task

logger = get_logger(__name__)


class BaseHardwareService(QObject):
    """Abstract base for hardware services.

    Subclasses must implement ``_ensure_connected`` to establish
    hardware-specific connections.

    Signals:
        connectedChanged: Emitted when connection state changes.
        instrumentVerified: Emitted when instrument (scope/keithley) ping state changes.
    """

    connectedChanged = Signal(bool)
    instrumentVerified = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        self._target_instrument_ip: str | None = None
        self._connected: bool = False
        self._instrument_verified_state: bool = False
        self._hw_lock = threading.RLock()
        self._artifact_manager = ArtifactManager()

    # ---- Simulation Helper ----

    def _simulate_work(self, name: str, duration: float = 0.5) -> None:
        """Simulate a hardware operation with console output.

        Intended for use by simulation subclasses.  Production services
        should never call this method.

        Args:
            name: Human-readable operation name.
            duration: Simulated delay in seconds.
        """
        import time

        print(f"\033[33m[SIMULATION] Starting {name}...\033[0m")
        time.sleep(duration)
        print(f"\033[32m[SIMULATION] {name} completed.\033[0m")

    # ---- Instrument IP / Verification ----

    def set_instrument_ip(self, ip: str) -> None:
        """Set the instrument IP address, resetting verification on change.

        Args:
            ip: New IP address for the instrument.
        """
        if not self._target_instrument_ip or self._target_instrument_ip != ip:
            self._target_instrument_ip = ip
            self.set_instrument_verified(False)

    def set_instrument_verified(self, verified: bool) -> None:
        """Update instrument verification state and emit signal if changed.

        Args:
            verified: Whether the instrument is verified.
        """
        if self._instrument_verified_state != verified:
            self._instrument_verified_state = verified
            self.instrumentVerified.emit(verified)

    def search_instruments(self, instrument_type: str = "scpi") -> FunctionTask:
        """Scan the local network for instruments in a worker thread.

        Args:
            instrument_type: ``"keithley"``, ``"scope"``, or ``"scpi"``.

        Returns:
            FunctionTask whose result contains ``{"instruments": [...]}``.
        """

        def job():
            print(f"Searching for {instrument_type} instruments on local network...")
            found = discover_instruments(
                instrument_type=instrument_type,
                progress_callback=lambda msg: print(msg),
            )
            for instr in found:
                print(f"  Found: {instr.display_name}")
            if not found:
                print("No instruments found.")
            return {
                "instruments": [
                    {"ip": i.ip, "identity": i.identity, "display": i.display_name} for i in found
                ]
            }

        return make_task("search_instruments", job)

    def ping_instrument(self) -> FunctionTask:
        """Ping the instrument IP in a worker thread.

        Returns:
            FunctionTask that performs the ping and updates verification state.
        """
        ip = self._target_instrument_ip

        def job():
            logger.info("Pinging instrument at %s", ip)
            try:
                subprocess.check_call(
                    ["ping", "-c", "1", "-W", "1", ip],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                logger.info("Instrument ping successful")
                print(f"Ping {ip}: OK")
                self.set_instrument_verified(True)
                return {"ok": True}
            except subprocess.CalledProcessError:
                logger.warning("Instrument ping failed for %s", ip)
                print(f"Ping {ip}: FAILED")
                self.set_instrument_verified(False)
                return {"ok": False}

        return make_task("ping", job)

    @staticmethod
    def require_instrument_ip(func):
        """Decorator: guard that instrument IP is configured before execution.

        Wraps the decorated method in a FunctionTask so that both the
        IP check and ``_ensure_connected()`` run inside the worker thread,
        preventing GUI freezes.
        """

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if not getattr(self, "_target_instrument_ip", ""):
                warnings.warn(
                    f"{func.__name__}() requires instrument IP to be configured. "
                    "Call set_instrument_ip() first.",
                    stacklevel=2,
                )
                return None

            # The original method must return a FunctionTask. We intercept its
            # internal job and prepend _ensure_connected inside the task.
            task = func(self, *args, **kwargs)
            if task is None:
                return None

            original_fn = task.fn

            def guarded_fn():
                with self._hw_lock:
                    self._ensure_connected()
                return original_fn()

            task.fn = guarded_fn
            return task

        return wrapper

    # ---- Properties ----

    @property
    def connected(self) -> bool:
        """Whether hardware is currently connected."""
        return self._connected

    @property
    def is_instrument_verified(self) -> bool:
        """Whether the instrument IP has been verified via ping."""
        return self._instrument_verified_state

    # ---- Common Operations ----

    @property
    def artifact_dir(self) -> str:
        """Return the absolute path to the calibration artifact directory.

        Subclasses must implement ``_artifact_dir()`` to return the relative path.
        """
        return self._artifact_manager.get_artifact_dir(self._artifact_dir())

    def _collect_artifacts(self) -> list[str]:
        """Collect all artifact files from the artifact directory.

        Returns:
            List of artifact file paths.
        """
        return self._artifact_manager.collect_artifacts(self._artifact_dir())

    def connect_only(self) -> FunctionTask:
        """Connect to hardware without additional operations.

        Returns:
            FunctionTask that establishes hardware connection.
        """

        def job():
            with self._hw_lock:
                self._ensure_connected()
            return {"serial": getattr(self, "_serial", 0), "ok": True}

        return make_task("connect", job)

    def disconnect_hardware(self) -> FunctionTask:
        """Disconnect from hardware in a worker thread.

        Returns:
            FunctionTask that tears down the hardware connection.
        """

        def job():
            with self._hw_lock:
                self._disconnect()
                self._connected = False
            self.connectedChanged.emit(False)
            logger.info("Disconnected successfully")
            return {"ok": True}

        return make_task("disconnect", job)

    # ---- Abstract ----

    @abstractmethod
    def _ensure_connected(self) -> None:
        """Establish hardware connections.  Called under ``_hw_lock``."""
        ...

    @abstractmethod
    def _disconnect(self) -> None:
        """Tear down hardware connections.  Called under ``_hw_lock``."""
        ...

    @abstractmethod
    def _artifact_dir(self) -> str:
        """Return the relative path to the artifact directory."""
        ...
