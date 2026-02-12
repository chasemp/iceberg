"""Tests for logging configuration."""

import logging


def test_setup_logging_configures_root_logger() -> None:
    """Test setup_logging configures the root logger."""
    from iceberg.logging_config import setup_logging

    setup_logging(verbose=0)

    root_logger = logging.getLogger()
    assert root_logger.level == logging.WARNING


def test_setup_logging_verbose_1_sets_info_level() -> None:
    """Test verbose=1 sets INFO level."""
    from iceberg.logging_config import setup_logging

    setup_logging(verbose=1)

    root_logger = logging.getLogger()
    assert root_logger.level == logging.INFO


def test_setup_logging_verbose_2_sets_debug_level() -> None:
    """Test verbose=2 sets DEBUG level."""
    from iceberg.logging_config import setup_logging

    setup_logging(verbose=2)

    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG


def test_setup_logging_adds_handler() -> None:
    """Test setup_logging adds a console handler."""
    from iceberg.logging_config import setup_logging

    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    setup_logging(verbose=1)

    assert len(root_logger.handlers) > 0
    assert any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers)


def test_setup_logging_formats_messages() -> None:
    """Test setup_logging configures formatter."""
    from iceberg.logging_config import setup_logging

    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    setup_logging(verbose=1)

    handler = root_logger.handlers[0]
    assert handler.formatter is not None


def test_setup_logging_idempotent() -> None:
    """Test calling setup_logging multiple times doesn't add duplicate handlers."""
    from iceberg.logging_config import setup_logging

    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    setup_logging(verbose=1)
    initial_handler_count = len(root_logger.handlers)

    setup_logging(verbose=1)
    assert len(root_logger.handlers) == initial_handler_count
