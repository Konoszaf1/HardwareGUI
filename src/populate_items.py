"""Static hardware and action descriptors used by the sample application."""

from src.logic.hardware_dataclass import HardwareDescriptor
from src.logic.action_dataclass import ActionDescriptor

HARDWARE: list[HardwareDescriptor] = [
    HardwareDescriptor(1, "Voltage Unit", ":/icons/keyboard.png", 0),
    HardwareDescriptor(3, "Scanner", ":/icons/scanner-image.png", 1),
    HardwareDescriptor(2, "Screen", ":/icons/screen.png", 2),
]

ACTIONS: list[ActionDescriptor] = [
    ActionDescriptor(id=1, hardware_id=1, label="Calibration", order=0),
    ActionDescriptor(2, 1, "Flash", 1),
    ActionDescriptor(3, 1, "Setup", 2),
    ActionDescriptor(4, 2, "Initialize", 0),
    ActionDescriptor(5, 2, "Calibrate", 1),
    ActionDescriptor(6, 3, "Install", 0),
]
