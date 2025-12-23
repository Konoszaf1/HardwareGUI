"""Application logging configuration.

This module sets up Python's logging framework for internal application
diagnostics. This is separate from the console widget which displays
user-facing task output redirected from script execution.

Usage:
    from src.logging_config import setup_logging, get_logger

    # In main.py (once at startup)
    setup_logging()

    # In any module
    logger = get_logger(__name__)
    logger.info("Something happened")
    logger.debug("Detailed info for debugging")
    logger.warning("Something unexpected")
    logger.error("Something failed")
"""

import logging
import sys
from pathlib import Path

from src.config import config


def setup_logging(
    level: str | None = None,
    log_file: str | None = None,
) -> logging.Logger:
    """Configure application-wide logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR). Defaults to config value.
        log_file: Optional file path for log output. Defaults to config value.

    Returns:
        Root application logger.
    """
    level = level or config.log_level
    log_file = log_file or config.log_file

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Root logger for the application
    root_logger = logging.getLogger("hardwaregui")
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Avoid adding duplicate handlers if called multiple times
    if root_logger.handlers:
        return root_logger

    # Console handler (stderr for diagnostics, separate from Qt console widget)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)

    # Optional file handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)
        root_logger.info(f"Logging to file: {log_path}")

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a child logger for a specific module.

    Args:
        name: Module name (typically __name__).

    Returns:
        Logger instance.

    Example:
        logger = get_logger(__name__)
        logger.info("Page initialized")
    """
    # Strip 'src.' prefix for cleaner log output
    if name.startswith("src."):
        name = name[4:]
    return logging.getLogger(f"hardwaregui.{name}")
