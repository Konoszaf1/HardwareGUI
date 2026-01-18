"""HardwareGUI application entry point."""

import argparse
import sys


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="HardwareGUI Application")
    parser.add_argument(
        "--simulation",
        action="store_true",
        help="Run in simulation mode without real hardware",
    )
    return parser.parse_args()


def _install_simulation_services():
    """Replace real service modules with simulated ones in sys.modules.

    This must run BEFORE any imports that would trigger loading the real
    service modules. We replace the entire module entries in sys.modules
    so that any subsequent imports get the simulated versions.
    """
    from types import ModuleType

    # Import simulation classes
    from logic.simulation import (
        SimulatedSMUService,
        SimulatedSUService,
        SimulatedVoltageUnitService,
    )

    # Create fake modules that expose the simulated classes under the real names
    fake_vu_module = ModuleType("src.logic.services.vu_service")
    fake_vu_module.VoltageUnitService = SimulatedVoltageUnitService

    fake_smu_module = ModuleType("src.logic.services.smu_service")
    fake_smu_module.SourceMeasureUnitService = SimulatedSMUService

    fake_su_module = ModuleType("src.logic.services.su_service")
    fake_su_module.SamplingUnitService = SimulatedSUService

    # Install fake modules BEFORE anything imports the real ones
    sys.modules["src.logic.services.vu_service"] = fake_vu_module
    sys.modules["src.logic.services.smu_service"] = fake_smu_module
    sys.modules["src.logic.services.su_service"] = fake_su_module

    print("\033[1;36m" + "=" * 60 + "\033[0m")
    print("\033[1;36m  SIMULATION MODE ACTIVE - No hardware required\033[0m")
    print("\033[1;36m" + "=" * 60 + "\033[0m")


def main():
    """Initialize and run the application."""
    args = parse_args()

    # Import logging FIRST (no dependency on services)
    from logging_config import get_logger, setup_logging

    setup_logging()
    logger = get_logger(__name__)

    if args.simulation:
        logger.info("Starting in SIMULATION mode")
        # CRITICAL: Install simulation services BEFORE any imports that load services
        _install_simulation_services()
    else:
        logger.info("Application starting")

    # NOW import Qt and MainWindow (after sys.modules patching)
    from PySide6.QtWidgets import QApplication

    import qt_material  # isort: skip
    import icons_rc  # noqa: F401
    from gui.main_window import MainWindow

    app = QApplication(sys.argv)
    qt_material.apply_stylesheet(app, "dark_blue.xml")
    logger.debug("Qt Material stylesheet applied")

    window = MainWindow()
    window.show()
    logger.info("Main window displayed")

    exit_code = app.exec()
    logger.info(f"Application exiting with code {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
