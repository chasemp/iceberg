"""Logging configuration for Iceberg.

Provides centralized logging setup with configurable verbosity levels.
"""

import logging
import sys


def setup_logging(verbose: int = 0) -> None:
    """Configure logging for the application.

    Args:
        verbose: Verbosity level
            0 = WARNING (default)
            1 = INFO
            2+ = DEBUG

    The function is idempotent - calling it multiple times won't add duplicate handlers.
    """
    root_logger = logging.getLogger()

    # Set log level based on verbosity
    if verbose == 0:
        level = logging.WARNING
    elif verbose == 1:
        level = logging.INFO
    else:
        level = logging.DEBUG

    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Add console handler
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)

    # Set formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    root_logger.addHandler(handler)
