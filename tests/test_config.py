"""Tests for configuration loading."""

import json
from pathlib import Path


def test_load_discovery_config_reads_default_file() -> None:
    """Test loading discovery config from default location."""
    from iceberg.config import load_discovery_config

    config = load_discovery_config()

    assert "categories" in config
    assert "limits" in config
    assert isinstance(config["categories"], dict)


def test_load_discovery_config_reads_custom_path(tmp_path: Path) -> None:
    """Test loading discovery config from custom path."""
    from iceberg.config import load_discovery_config

    config_data = {
        "categories": {"trending-monthly": {"limit": 50}},
        "limits": {"default": 25},
        "languages": ["Python", "JavaScript"],
    }

    config_file = tmp_path / "discovery.json"
    config_file.write_text(json.dumps(config_data))

    config = load_discovery_config(config_file)

    assert config["categories"]["trending-monthly"]["limit"] == 50
    assert "Python" in config["languages"]


def test_load_discovery_config_returns_defaults_when_missing() -> None:
    """Test loading config returns defaults when file missing."""
    from iceberg.config import load_discovery_config

    config = load_discovery_config(Path("/nonexistent/discovery.json"))

    assert "categories" in config
    assert "limits" in config
    assert config["limits"]["default"] == 25


def test_load_discovery_config_validates_required_fields(tmp_path: Path) -> None:
    """Test loading config validates required fields."""
    from iceberg.config import load_discovery_config

    config_data = {"invalid": "config"}

    config_file = tmp_path / "discovery.json"
    config_file.write_text(json.dumps(config_data))

    # Should return defaults when validation fails
    config = load_discovery_config(config_file)

    assert "categories" in config
    assert "limits" in config


def test_get_category_limit_returns_category_specific_limit() -> None:
    """Test getting category-specific limit."""
    from iceberg.config import get_category_limit, load_discovery_config

    config = load_discovery_config()

    # Should return category-specific limit if defined
    limit = get_category_limit(config, "trending-monthly")

    assert isinstance(limit, int)
    assert limit > 0


def test_get_category_limit_returns_default_when_not_defined() -> None:
    """Test getting default limit when category not defined."""
    from iceberg.config import get_category_limit

    config = {"limits": {"default": 25}, "categories": {}}

    limit = get_category_limit(config, "unknown-category")

    assert limit == 25
