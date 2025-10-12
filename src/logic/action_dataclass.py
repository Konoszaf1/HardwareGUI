"""Dataclass representing the domain object of a specific action that
a hardware does, hardware and actions are linked by the hardware id number
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ActionDescriptor:
    id: int
    hardware_id: int
    label: str
    order: int
