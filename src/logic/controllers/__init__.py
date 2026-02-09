"""Hardware controllers for device operations.

This module provides controller classes that encapsulate hardware workflows:
- SUController: Sampling Unit operations (setup, test, calibration)
- SMUController: Source Measure Unit operations (setup, test, relay control, calibration)
- VUController: Voltage Unit operations (setup, test, calibration, guard)

Controllers use direct imports from the dpi package and follow SOLID principles.
"""

from src.logic.controllers.base_controller import (
    ChannelConfig,
    HardwareController,
    OperationResult,
)
from src.logic.controllers.smu_controller import SMUController
from src.logic.controllers.su_controller import SUController
from src.logic.controllers.vu_controller import VUController

__all__ = [
    "ChannelConfig",
    "HardwareController",
    "OperationResult",
    "SMUController",
    "SUController",
    "VUController",
]
