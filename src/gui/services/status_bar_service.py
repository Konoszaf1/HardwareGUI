"""Status bar service with multi-section display and hardware state persistence.

This module provides a singleton service to manage the application's status bar
with multiple sections: app status (left) and instrument connection status (right).

Each hardware unit can have its own connection state that persists when switching
between hardware selections.

States:
    App Status:
        - READY: Idle (animated dots)
        - BUSY: Running a task

    Instrument Status (per hardware):
        - CONNECTED: Instrument verified
        - DISCONNECTED: Instrument not connected/verified

Usage:
    StatusBarService.init(statusbar)
    StatusBarService.instance().set_busy("Running calibration...")
    StatusBarService.instance().set_ready()
    StatusBarService.instance().set_instrument_connected(hardware_id, True)
    StatusBarService.instance().set_active_hardware(hardware_id)
"""

from __future__ import annotations

from enum import Enum, auto

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel, QStatusBar

from src.config import config
from src.gui.styles import Colors, Styles
from src.logging_config import get_logger

logger = get_logger(__name__)


class AppStatus(Enum):
    """Application status states."""

    READY = auto()
    BUSY = auto()


class StatusBarService:
    """Singleton service for multi-section status bar with hardware state persistence."""

    _instance: StatusBarService | None = None
    _statusbar: QStatusBar | None = None

    def __init__(self) -> None:
        """Private constructor. Use StatusBarService.instance() instead."""
        if StatusBarService._instance is not None:
            raise RuntimeError("Use StatusBarService.instance() instead")

        self._app_status = AppStatus.READY
        self._busy_message = ""
        self._dot_count = 1

        # Hardware-specific scope states: {hardware_id: is_connected}
        self._hardware_scope_states: dict[int, bool] = {}
        self._active_hardware_id: int | None = None

        self._app_label: QLabel | None = None
        self._scope_label: QLabel | None = None
        self._animation_timer: QTimer = QTimer()

    @classmethod
    def init(cls, statusbar: QStatusBar) -> None:
        """Initialize the service with the status bar widget.

        Args:
            statusbar (QStatusBar): The status bar widget.
        """
        cls._statusbar = statusbar
        instance = cls.__new__(cls)
        # Manually call __init__-like setup since __new__ bypasses it
        # or we could just instantiate normally if we adjusted the pattern.
        # But to stick to the existing pattern:

        instance._app_status = AppStatus.READY
        instance._busy_message = ""
        instance._dot_count = 1

        instance._hardware_scope_states = {}
        instance._active_hardware_id = None

        # Create status labels
        instance._app_label = QLabel()
        instance._app_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; padding: 0 8px;")

        instance._scope_label = QLabel()
        instance._scope_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; padding: 0 8px;")

        # Add widgets
        # app_label on the left, scope_label as permanent on the right
        statusbar.insertWidget(0, instance._app_label)
        statusbar.addPermanentWidget(instance._scope_label)

        # Animation timer
        instance._animation_timer = QTimer()
        instance._animation_timer.timeout.connect(instance._animate_dots)
        instance._animation_timer.setInterval(config.status_bar.animation_interval_ms)

        cls._instance = instance
        logger.info("StatusBarService initialized with multi-section display")
        instance._start_ready_animation()
        instance._update_scope_display()

    @classmethod
    def instance(cls) -> StatusBarService:
        """Get the singleton instance.

        Returns:
            StatusBarService: The singleton instance.

        Raises:
            RuntimeError: If init() has not been called.
        """
        if cls._instance is None:
            raise RuntimeError("StatusBarService.init() must be called first")
        return cls._instance

    # ---- App Status ----

    def set_ready(self) -> None:
        """Set app status to ready (idle, animated)."""
        self._app_status = AppStatus.READY
        self._start_ready_animation()
        logger.info("Status: Ready")

    def set_busy(self, message: str) -> None:
        """Set app status to busy with a task message.

        Args:
            message (str): Busy message.
        """
        self._app_status = AppStatus.BUSY
        self._busy_message = message
        self._stop_animation()
        self._update_app_display()
        logger.info("Status: Busy - %s", message)

    # ---- Scope Status (per hardware) ----

    def set_active_hardware(self, hardware_id: int) -> None:
        """Set the currently active hardware unit.

        This restores the scope connection state for the selected hardware.

        Args:
            hardware_id (int): Hardware ID.
        """
        self._active_hardware_id = hardware_id
        # Initialize state if not exists
        if hardware_id not in self._hardware_scope_states:
            self._hardware_scope_states[hardware_id] = False
        self._update_scope_display()
        logger.debug(
            "Active hardware: %s, scope: %s",
            hardware_id, self._hardware_scope_states.get(hardware_id),
        )

    def set_instrument_connected(
        self, hardware_id: int | None = None, connected: bool = True
    ) -> None:
        """Set the instrument connection state for a hardware unit.

        Args:
            hardware_id (int | None): Hardware ID (defaults to active hardware).
            connected (bool): Whether instrument is connected/verified.
        """
        if hardware_id is None:
            hardware_id = self._active_hardware_id
        if hardware_id is None:
            return

        self._hardware_scope_states[hardware_id] = connected
        self._update_scope_display()
        logger.info(
            "Scope %s for hardware %s", "connected" if connected else "disconnected", hardware_id
        )

    def set_disconnected(self) -> None:
        """Set instrument as disconnected for active hardware (backward compat)."""
        self.set_instrument_connected(connected=False)

    # ---- Temporary messages ----

    def show_temporary(self, message: str, timeout_ms: int | None = None) -> None:
        """Show a temporary message in the main status area.

        Args:
            message (str): Message to show.
            timeout_ms (int | None): Timeout in ms.
        """
        if self._statusbar is None or self._app_label is None:
            return
        if timeout_ms is None:
            timeout_ms = config.status_bar.default_timeout_ms

        was_animating = self._animation_timer.isActive()
        self._stop_animation()

        self._app_label.setText(message)

        if was_animating:
            QTimer.singleShot(timeout_ms, self._restore_state)

    def _restore_state(self) -> None:
        """Restore display after temporary message."""
        if self._app_status == AppStatus.READY:
            self._start_ready_animation()
        else:
            self._update_app_display()

    # ---- Display updates ----

    def _update_app_display(self) -> None:
        """Update the app status display (left side)."""
        if self._app_label is None:
            return

        if self._app_status == AppStatus.BUSY:
            self._app_label.setText(f"{self._busy_message}")
        elif self._app_status == AppStatus.READY:
            dots = "." * self._dot_count
            self._app_label.setText(f"Ready {dots}")

    def _update_scope_display(self) -> None:
        """Update the instrument connection display (right side)."""
        if self._scope_label is None:
            return

        if self._active_hardware_id is None:
            self._scope_label.setText("")
            return

        is_connected = self._hardware_scope_states.get(self._active_hardware_id, False)
        if is_connected:
            self._scope_label.setText("Instrument: Connected")
            self._scope_label.setStyleSheet(Styles.SCOPE_CONNECTED)
        else:
            self._scope_label.setText("Instrument: Disconnected")
            self._scope_label.setStyleSheet(Styles.SCOPE_DISCONNECTED)

    # ---- Animation ----

    def _start_ready_animation(self) -> None:
        """Start the ready dots animation."""
        self._dot_count = 1
        self._update_app_display()
        self._animation_timer.start()

    def _stop_animation(self) -> None:
        """Stop the dots animation."""
        self._animation_timer.stop()

    def _animate_dots(self) -> None:
        """Cycle through dot animation."""
        if self._app_status != AppStatus.READY:
            self._stop_animation()
            return
        self._dot_count = (self._dot_count % 3) + 1
        self._update_app_display()
