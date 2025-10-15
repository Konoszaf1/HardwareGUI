"""Dataclass representing the domain object of a specific hardware that
needs to be calibrated
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HardwareDescriptor:
    """Metadata describing a single hardware.

    Attributes:
        id: Unique identifier for this hardware.
        label: Human-readable name of the hardware.
        icon_path: The relative path of the image resource to be loaded.
        order: Display ordering for the action.
    """

    id: int
    label: str
    icon_path: str
    order: int
