"""HardwareGUI application entry point."""

import sys

from PySide6.QtWidgets import QApplication

import qt_material  # isort: skip
import icons_rc  # noqa: F401
from gui.main_window import MainWindow
from logging_config import get_logger, setup_logging


def main():
    """Initialize and run the application."""
    setup_logging()
    logger = get_logger(__name__)
    logger.info("Application starting")

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
