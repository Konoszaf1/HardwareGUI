"""Dataclass representing the domain object of a specific action that
a specific hardware device does, hardware and actions are linked by the hardware id number
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ActionDescriptor:
    """Metadata describing a single hardware action.

    Attributes:
        id: Unique identifier for this action.
        hardware_id: Identifier of the hardware device this action belongs to.
        label: Human-readable name of the action.
        order: Display and execution ordering for the action.
    """

    id: int
    hardware_id: int
    label: str
    order: int
    page_id: str
