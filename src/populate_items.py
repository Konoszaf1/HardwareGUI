"""Static hardware and action descriptors used by the sample application."""

from src.logic.action_dataclass import ActionDescriptor
from src.logic.hardware_dataclass import HardwareDescriptor

HARDWARE: list[HardwareDescriptor] = [
    HardwareDescriptor(1, "Voltage Unit", ":/icons/keyboard.png", 0),
    HardwareDescriptor(3, "Source Measure Unit", ":/icons/scanner-image.png", 1),
    HardwareDescriptor(2, "Sampling Unit", ":/icons/screen.png", 2),
]

ACTIONS: list[ActionDescriptor] = [
    # Voltage Unit actions
    ActionDescriptor(
        id=1, hardware_id=1, label="Session & Coefficients", order=0, page_id="workbench"
    ),
    ActionDescriptor(2, 1, "Calibration", 1, "calibration"),
    ActionDescriptor(3, 1, "Test", 2, "test"),
    ActionDescriptor(4, 1, "Guard", 3, "guard"),
    # Source Measure Unit actions
    ActionDescriptor(6, 3, "Hardware Setup", 0, "smu_setup"),
    ActionDescriptor(7, 3, "Verify", 1, "smu_verify"),
    ActionDescriptor(8, 3, "Calibration Measure", 2, "smu_cal_measure"),
    ActionDescriptor(9, 3, "Calibration Fit", 3, "smu_cal_fit"),
    # Sampling Unit actions
    ActionDescriptor(10, 2, "Hardware Setup", 0, "su_setup"),
    ActionDescriptor(11, 2, "Verify", 1, "su_verify"),
    ActionDescriptor(12, 2, "Calibration Measure", 2, "su_cal_measure"),
    ActionDescriptor(13, 2, "Calibration Fit", 3, "su_cal_fit"),
]
