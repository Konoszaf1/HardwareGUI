"""Hardware exception hierarchy for structured error handling.

Replaces bare ``except Exception`` with specific types so callers can
distinguish connection failures from protocol errors, calibration issues,
and configuration mistakes.
"""


class HardwareError(Exception):
    """Base class for all hardware-related errors."""


class ConnectionError(HardwareError):
    """Failed to establish or maintain a hardware connection.

    Covers USB enumeration failures, VXI-11 link errors, and device
    not-found conditions.
    """


class DeviceNotFoundError(ConnectionError):
    """Specific device (serial/interface) was not found on the bus."""


class CommunicationError(HardwareError):
    """A connected device failed to respond or returned unexpected data.

    Covers SCPI timeouts, malformed responses, and protocol violations.
    """


class ScopeTimeoutError(CommunicationError):
    """Oscilloscope did not trigger or timed out waiting for acquisition."""


class CalibrationError(HardwareError):
    """Error during calibration measurement, fitting, or EEPROM write."""


class ConfigurationError(HardwareError):
    """Invalid device configuration (bad serial, unsupported connector, etc.)."""
