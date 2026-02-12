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

logger = get_logger(__name__)


class BaseHardwareService(QObject):
    """Abstract base for hardware services.

    Subclasses must implement ``_ensure_connected`` to establish
    hardware-specific connections.

    Signals:
        connectedChanged: Emitted when connection state changes.
        inputRequested: Emitted when user input is needed from the GUI.
        instrumentVerified: Emitted when instrument (scope/keithley) ping state changes.
    """

    connectedChanged = Signal(bool)
    inputRequested = Signal(str)
    instrumentVerified = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        self._target_instrument_ip: str | None = None
        self._connected: bool = False
        self._instrument_verified_state: bool = False
        self._hw_lock = threading.Lock()
        self._artifact_manager = ArtifactManager()

        # Input redirection for blocking hardware prompts
        self._input_event = threading.Event()
        self._input_value: str = ""

    # ---- Input Redirection ----

    def provide_input(self, text: str) -> None:
        """Provide user input to a blocking hardware operation.

        Called from the GUI thread when the user submits text via the
        shared input field.  Unblocks any worker thread waiting on
        ``_input_event``.

        Args:
            text: The text entered by the user.
        """
        self._input_value = text
        self._input_event.set()

    def wait_for_input(self, prompt: str) -> str:
        """Block the calling (worker) thread until the user provides input.

        Emits ``inputRequested`` to trigger the GUI input field, then
        blocks until ``provide_input`` is called.

        Args:
            prompt: Prompt text shown to the user.

        Returns:
            The text entered by the user.
        """
        self._input_event.clear()
        self._input_value = ""
        self.inputRequested.emit(prompt)
        self._input_event.wait()
        return self._input_value

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

    def ping_instrument(self) -> bool:
        """Ping the instrument IP address to verify connectivity.

        Returns:
            True if the instrument is reachable, False otherwise.
        """
        logger.info("Pinging instrument at %s", self._target_instrument_ip)
        try:
            subprocess.check_call(
                ["ping", "-c", "1", "-W", "1", self._target_instrument_ip],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info("Instrument ping successful")
            self.set_instrument_verified(True)
            return True
        except subprocess.CalledProcessError:
            logger.warning("Instrument ping failed for %s", self._target_instrument_ip)
            self.set_instrument_verified(False)
            return False

    @staticmethod
    def require_instrument_ip(func):
        """Decorator: guard that instrument IP is configured before execution.

        Acquires ``_hw_lock`` and calls ``_ensure_connected`` before
        delegating to the wrapped method.  Returns ``None`` with a
        ``UserWarning`` when the IP is missing.
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
            with self._hw_lock:
                self._ensure_connected()
                return func(self, *args, **kwargs)

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

    # ---- Abstract ----

    @abstractmethod
    def _ensure_connected(self) -> None:
        """Establish hardware connections.  Called under ``_hw_lock``."""
        ...
