"""Static hardware and action descriptors used by the sample application."""

from src.logic.action_dataclass import ActionDescriptor
from src.logic.hardware_dataclass import HardwareDescriptor

HARDWARE: list[HardwareDescriptor] = [
    HardwareDescriptor(1, "Voltage Unit", ":/icons/keyboard.png", 0),
    HardwareDescriptor(3, "Source Measure Unit", ":/icons/scanner-image.png", 1),
    HardwareDescriptor(2, "Sampling Unit", ":/icons/screen.png", 2),
]

ACTIONS: list[ActionDescriptor] = [
    # Voltage Unit actions (5 pages)
    ActionDescriptor(id=1, hardware_id=1, label="Connection", order=0, page_id="vu_connection"),
    ActionDescriptor(2, 1, "Setup", 1, "vu_setup"),
    ActionDescriptor(3, 1, "Test", 2, "vu_test"),
    ActionDescriptor(4, 1, "Calibration", 3, "vu_calibration"),
    ActionDescriptor(5, 1, "Guard", 4, "vu_guard"),
    # Source Measure Unit actions (4 pages)
    ActionDescriptor(6, 3, "Connection", 0, "smu_connection"),
    ActionDescriptor(7, 3, "Setup", 1, "smu_setup"),
    ActionDescriptor(8, 3, "Test", 2, "smu_test"),
    ActionDescriptor(9, 3, "Calibration", 3, "smu_calibration"),
    # Sampling Unit actions (4 pages)
    ActionDescriptor(20, 2, "Connection", 0, "su_connection"),
    ActionDescriptor(21, 2, "Setup", 1, "su_setup"),
    ActionDescriptor(22, 2, "Test", 2, "su_test"),
    ActionDescriptor(23, 2, "Calibration", 3, "su_calibration"),
]
