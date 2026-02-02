from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock


def test_analyze_unpublished_npm_project(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    """Test analyzing a project that isn't published to npm."""
    from iceberg.sbom import analyze_from_manifest

    package_json = """
    {
      "name": "my-app",
      "version": "1.0.0",
      "dependencies": {
        "react": "^18.2.0",
        "lodash": "^4.17.21"
      }
    }
    """

    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/owner/my-app/main/package.json",
        text=package_json,
    )

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/react/versions/18.2.0",
        json={"lineCount": 10000},
    )

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/react/versions/18.2.0:dependencies",
        json={"dependencies": []},
    )

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/lodash/versions/4.17.21",
        json={"lineCount": 5000},
    )

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/lodash/versions/4.17.21:dependencies",
        json={"dependencies": []},
    )

    result = analyze_from_manifest("owner", "my-app", cache_dir=tmp_path)

    assert result is not None
    assert result["total_dependencies_loc"] == 15000
    assert len(result["dependencies"]) == 2


def test_analyze_unpublished_python_project(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    """Test analyzing a Python project that isn't published to PyPI."""
    from iceberg.sbom import analyze_from_manifest

    pyproject_toml = """
    [project]
    name = "my-tool"
    version = "0.1.0"
    dependencies = [
        "requests>=2.31.0",
        "click>=8.0.0"
    ]
    """

    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/owner/my-tool/main/package.json",
        status_code=404,
    )

    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/owner/my-tool/master/package.json",
        status_code=404,
    )

    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/owner/my-tool/main/pyproject.toml",
        text=pyproject_toml,
    )

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/pypi/packages/requests/versions/2.31.0",
        json={"lineCount": 3000},
    )

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/pypi/packages/requests/versions/2.31.0:dependencies",
        json={"dependencies": []},
    )

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/pypi/packages/click/versions/8.0.0",
        json={"lineCount": 2000},
    )

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/pypi/packages/click/versions/8.0.0:dependencies",
        json={"dependencies": []},
    )

    result = analyze_from_manifest("owner", "my-tool", cache_dir=tmp_path)

    assert result is not None
    assert result["total_dependencies_loc"] == 5000


def test_parse_npm_dependencies() -> None:
    """Test parsing dependencies from package.json."""
    from iceberg.sbom import parse_npm_dependencies

    package_json = """
    {
      "dependencies": {
        "react": "^18.2.0",
        "lodash": "~4.17.21",
        "@types/node": ">=20.0.0"
      },
      "devDependencies": {
        "jest": "^29.0.0"
      }
    }
    """

    deps = parse_npm_dependencies(package_json)

    # Now includes devDependencies too
    assert len(deps) == 4
    assert ("react", "18.2.0") in deps
    assert ("lodash", "4.17.21") in deps
    assert ("@types/node", "20.0.0") in deps
    assert ("jest", "29.0.0") in deps


def test_parse_python_dependencies() -> None:
    """Test parsing dependencies from pyproject.toml."""
    from iceberg.sbom import parse_python_dependencies

    pyproject_toml = """
    [project]
    dependencies = [
        "requests>=2.31.0",
        "click==8.0.0",
        "pydantic~=2.0.0"
    ]
    """

    deps = parse_python_dependencies(pyproject_toml)

    assert len(deps) == 3
    assert ("requests", "2.31.0") in deps
    assert ("click", "8.0.0") in deps
    assert ("pydantic", "2.0.0") in deps


def test_analyze_returns_none_when_no_manifest(httpx_mock: HTTPXMock) -> None:
    """Test that analysis returns None when no manifest is found."""
    from iceberg.sbom import analyze_from_manifest

    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/owner/repo/main/package.json",
        status_code=404,
    )

    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/owner/repo/master/package.json",
        status_code=404,
    )

    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/owner/repo/main/pyproject.toml",
        status_code=404,
    )

    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/owner/repo/master/pyproject.toml",
        status_code=404,
    )

    result = analyze_from_manifest("owner", "repo")

    assert result is None
