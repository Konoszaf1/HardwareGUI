"""Dataclass representing the domain object of a specific hardware that
needs to be calibrated
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HardwareDescriptor:
    id: int
    label: str
    icon_path: str
