"""Shared utilities for CLI commands."""

import logging
from pathlib import Path

from iceberg.cache import get_default_cache_dir
from iceberg.logging_config import setup_logging

logger = logging.getLogger(__name__)


def resolve_cache_dir(cache_dir: Path | None) -> Path:
    """Resolve cache directory, using default if not provided.

    Args:
        cache_dir: Optional cache directory path

    Returns:
        Resolved cache directory path
    """
    return cache_dir or get_default_cache_dir()


def setup_verbose_logging(verbose: int) -> None:
    """Setup logging based on verbosity level.

    Args:
        verbose: Verbosity level (0=WARNING, 1=INFO, 2+=DEBUG)
    """
    setup_logging(verbose)
