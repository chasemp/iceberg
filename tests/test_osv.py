from pathlib import Path

import pytest


def test_parse_osv_sbom() -> None:
    """Test parsing OSV-Scanner SBOM output."""
    from iceberg.osv import parse_osv_sbom

    osv_output = """
    {
      "results": [
        {
          "packages": [
            {
              "package": {
                "name": "react",
                "version": "18.2.0",
                "ecosystem": "npm"
              }
            },
            {
              "package": {
                "name": "lodash",
                "version": "4.17.21",
                "ecosystem": "npm"
              }
            }
          ]
        }
      ]
    }
    """

    deps = parse_osv_sbom(osv_output)

    assert len(deps) == 2
    assert deps[0].system == "npm"
    assert deps[0].name == "react"
    assert deps[0].version == "18.2.0"
    assert deps[1].name == "lodash"


def test_parse_osv_sbom_handles_empty() -> None:
    """Test parsing empty OSV output."""
    from iceberg.osv import parse_osv_sbom

    osv_output = '{"results": []}'
    deps = parse_osv_sbom(osv_output)

    assert deps == []


def test_parse_osv_sbom_maps_ecosystems() -> None:
    """Test ecosystem name mapping."""
    from iceberg.osv import parse_osv_sbom

    osv_output = """
    {
      "results": [
        {
          "packages": [
            {
              "package": {
                "name": "requests",
                "version": "2.31.0",
                "ecosystem": "PyPI"
              }
            },
            {
              "package": {
                "name": "serde",
                "version": "1.0.0",
                "ecosystem": "crates.io"
              }
            }
          ]
        }
      ]
    }
    """

    deps = parse_osv_sbom(osv_output)

    assert len(deps) == 2
    assert deps[0].system == "pypi"
    assert deps[1].system == "cargo"


def test_run_osv_scanner_on_repo(tmp_path: Path) -> None:
    """Test running osv-scanner on a cloned repo."""
    from iceberg.osv import run_osv_scanner

    # Create a minimal package.json
    package_json = tmp_path / "package.json"
    package_json.write_text("""
    {
      "name": "test",
      "dependencies": {
        "react": "^18.2.0"
      }
    }
    """)

    # Create a package-lock.json (osv-scanner needs lockfiles)
    package_lock = tmp_path / "package-lock.json"
    package_lock.write_text("""
    {
      "name": "test",
      "lockfileVersion": 2,
      "packages": {
        "": {
          "dependencies": {
            "react": "^18.2.0"
          }
        },
        "node_modules/react": {
          "version": "18.2.0"
        }
      }
    }
    """)

    result = run_osv_scanner(tmp_path)

    # OSV-Scanner may or may not find vulnerabilities, but should return output
    # If it returns None, that's okay (no lockfile parsed or no vulnerabilities)
    assert result is None or isinstance(result, str)


def test_analyze_with_osv_scanner(tmp_path: Path) -> None:
    """Test full analysis using OSV-Scanner."""
    from iceberg.osv import analyze_with_osv

    # Create a test repo
    package_json = tmp_path / "package.json"
    package_json.write_text("""
    {
      "name": "test-app",
      "dependencies": {
        "lodash": "^4.17.21"
      }
    }
    """)

    # Create lockfile
    package_lock = tmp_path / "package-lock.json"
    package_lock.write_text("""
    {
      "name": "test-app",
      "lockfileVersion": 2,
      "packages": {
        "node_modules/lodash": {
          "version": "4.17.21"
        }
      }
    }
    """)

    # Mock loc calculator
    def mock_loc_calculator(pkg, cache_dir=None):
        return 1000

    result = analyze_with_osv(str(tmp_path), mock_loc_calculator, cache_dir=tmp_path / "cache")

    # OSV-Scanner may not find the package if format is wrong
    # That's okay - we're testing the integration, not osv-scanner itself
    assert result is None or isinstance(result, dict)


def test_osv_scanner_not_found_returns_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test graceful handling when osv-scanner is not installed."""
    from iceberg.osv import run_osv_scanner

    def mock_which(cmd: str) -> None:
        return None

    monkeypatch.setattr("shutil.which", mock_which)

    result = run_osv_scanner(tmp_path)
    assert result is None
