"""HardwareGUI application entry point."""

import argparse
import sys

from PySide6.QtWidgets import QApplication

import qt_material  # isort: skip

import src.icons_rc as icons_rc  # noqa: F401  # Register Qt resources (:/icons/...)
from src.logging_config import get_logger, setup_logging


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="HardwareGUI Application")
    parser.add_argument(
        "--simulation",
        action="store_true",
        help="Run in simulation mode without real hardware",
    )
    return parser.parse_args()


def _create_simulation_services() -> dict:
    """Create simulated service instances for DI.

    Returns:
        Dict with keys 'vu', 'smu', 'su' mapping to simulated service instances.
    """
    from src.logic.simulation import (
        SimulatedSMUService,
        SimulatedSUService,
        SimulatedVoltageUnitService,
    )

    print("\033[1;36m" + "=" * 60 + "\033[0m")
    print("\033[1;36m  SIMULATION MODE ACTIVE - No hardware required\033[0m")
    print("\033[1;36m" + "=" * 60 + "\033[0m")

    return {
        "vu": SimulatedVoltageUnitService(),
        "smu": SimulatedSMUService(),
        "su": SimulatedSUService(),
    }


def main():
    """Initialize and run the application."""
    args = parse_args()

    setup_logging()
    logger = get_logger(__name__)

    services = None
    if args.simulation:
        logger.info("Starting in SIMULATION mode")
        services = _create_simulation_services()

    logger.info("Application starting")

    from src.gui.main_window import MainWindow

    app = QApplication(sys.argv)
    qt_material.apply_stylesheet(app, "dark_blue.xml")
    logger.debug("Qt Material stylesheet applied")

    window = MainWindow(services=services)
    window.show()
    logger.info("Main window displayed")

    exit_code = app.exec()
    logger.info(f"Application exiting with code {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
