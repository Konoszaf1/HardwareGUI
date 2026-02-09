"""Base controller classes and result types for hardware operations.

This module defines the abstract interface and shared types for hardware controllers.
All unit-specific controllers inherit from HardwareController.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class OperationResult:
    """Immutable result of a hardware operation.

    Attributes:
        ok: Whether the operation was successful.
        serial: Device serial number if applicable.
        message: Human-readable message (error or success).
        data: Operation-specific data dictionary.
    """

    ok: bool
    serial: int | None = None
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ChannelConfig:
    """Configuration for an amplifier channel.

    Attributes:
        channel_id: Channel identifier (e.g., "AMP1", "AMP2").
        amplifier_type: Type of amplifier (e.g., "AMP").
        channel_type: Channel mode (e.g., "INPUT").
        opamp_type: Operational amplifier chip (e.g., "ADA4898").
        gain: Channel gain value.
        bandwidth: Channel bandwidth in Hz.
        range: Measurement range.
        unit: Measurement unit (e.g., "V", "A").
    """

    channel_id: str
    amplifier_type: str
    channel_type: str
    opamp_type: str
    gain: float
    bandwidth: float
    range: float
    unit: str


class HardwareController(ABC):
    """Abstract base class for hardware unit controllers.

    Controllers encapsulate hardware workflows and provide a clean interface
    for services to perform operations. Controllers use direct imports from
    the dpi package rather than symlinked scripts.
    """

    @abstractmethod
    def initialize_device(
        self,
        serial: int,
        processor_type: str = "746",
        connector_type: str = "BNC",
    ) -> OperationResult:
        """Initialize a new device after first flash.

        Args:
            serial: Device serial number (1-9999).
            processor_type: Processor type string.
            connector_type: Connector type ("BNC" or "SMA").

        Returns:
            OperationResult with success status and serial number.
        """
        ...

    @abstractmethod
    def read_temperature(self) -> OperationResult:
        """Read current device temperature.

        Returns:
            OperationResult with temperature in data["temperature"].
        """
        ...

    @abstractmethod
    def perform_autocalibration(self) -> OperationResult:
        """Run autocalibration on the device.

        Returns:
            OperationResult with success status.
        """
        ...
