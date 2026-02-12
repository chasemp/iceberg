"""Configuration loading for Iceberg.

Loads configuration from JSON files with sensible defaults.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default configuration
_DEFAULT_CONFIG = {
    "categories": {
        "trending-monthly": {"limit": 25},
        "github-ranking": {"limit": 100},
        "search": {"limit": 50},
    },
    "limits": {
        "default": 25,
        "max": 200,
    },
    "languages": ["Python", "JavaScript", "TypeScript", "Go", "Rust", "Java"],
}


def load_discovery_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load discovery configuration from JSON file.

    Args:
        config_path: Path to config file. Uses default if not provided.

    Returns:
        Configuration dictionary with defaults if file not found
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "discovery.json"

    if not config_path.exists():
        logger.debug(f"Config file not found at {config_path}, using defaults")
        return _DEFAULT_CONFIG.copy()

    try:
        config = json.loads(config_path.read_text())

        # Validate required fields
        if not isinstance(config.get("categories"), dict):
            logger.warning("Invalid config: missing or invalid 'categories' field, using defaults")
            return _DEFAULT_CONFIG.copy()

        if not isinstance(config.get("limits"), dict):
            logger.warning("Invalid config: missing or invalid 'limits' field, using defaults")
            return _DEFAULT_CONFIG.copy()

        logger.debug(f"Loaded discovery config from {config_path}")
        return config

    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Failed to load config from {config_path}: {e}, using defaults")
        return _DEFAULT_CONFIG.copy()


def get_category_limit(config: dict[str, Any], category: str) -> int:
    """Get limit for a specific category.

    Args:
        config: Configuration dictionary
        category: Category name

    Returns:
        Limit for the category, or default limit if not defined
    """
    categories = config.get("categories", {})
    category_config = categories.get(category, {})

    if "limit" in category_config:
        return int(category_config["limit"])

    limits = config.get("limits", {})
    return int(limits.get("default", 25))
