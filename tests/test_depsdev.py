import pytest
from pytest_httpx import HTTPXMock

from tests.factories import create_package_identifier


def test_get_project_loc_fetches_from_api(httpx_mock: HTTPXMock) -> None:
    from iceberg.depsdev import get_project_loc

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/projects/github.com%2Fowner%2Frepo",
        json={"lineCount": 10000},
    )

    loc = get_project_loc("owner", "repo")

    assert loc == 10000


def test_get_project_loc_returns_none_when_missing(httpx_mock: HTTPXMock) -> None:
    from iceberg.depsdev import get_project_loc

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/projects/github.com%2Fowner%2Frepo",
        json={},
    )

    loc = get_project_loc("owner", "repo")

    assert loc is None


def test_get_project_loc_handles_network_error(httpx_mock: HTTPXMock) -> None:
    from iceberg.depsdev import DepsDevError, get_project_loc

    httpx_mock.add_exception(Exception("Network error"))

    with pytest.raises(DepsDevError) as exc_info:
        get_project_loc("owner", "repo")

    assert "Failed to fetch project LoC" in str(exc_info.value)


def test_get_dependencies_fetches_from_api(httpx_mock: HTTPXMock) -> None:
    from iceberg.depsdev import get_dependencies

    pkg = create_package_identifier(system="npm", name="react", version="18.2.0")

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/react/versions/18.2.0:dependencies",
        json={
            "dependencies": [
                {
                    "requirement": "^1.0.0",
                    "package": {
                        "system": "npm",
                        "name": "loose-envify",
                    },
                    "version": "1.4.0",
                }
            ]
        },
    )

    deps = get_dependencies(pkg)

    assert len(deps) == 1
    assert deps[0].system == "npm"
    assert deps[0].name == "loose-envify"
    assert deps[0].version == "1.4.0"


def test_get_dependencies_returns_empty_when_none(httpx_mock: HTTPXMock) -> None:
    from iceberg.depsdev import get_dependencies

    pkg = create_package_identifier(system="npm", name="react", version="18.2.0")

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/react/versions/18.2.0:dependencies",
        json={},
    )

    deps = get_dependencies(pkg)

    assert deps == []


def test_get_dependencies_handles_network_error(httpx_mock: HTTPXMock) -> None:
    from iceberg.depsdev import DepsDevError, get_dependencies

    pkg = create_package_identifier(system="npm", name="react", version="18.2.0")

    httpx_mock.add_exception(Exception("Network error"))

    with pytest.raises(DepsDevError) as exc_info:
        get_dependencies(pkg)

    assert "Failed to fetch dependencies" in str(exc_info.value)


def test_get_package_loc_fetches_from_api(httpx_mock: HTTPXMock) -> None:
    from iceberg.depsdev import get_package_loc

    pkg = create_package_identifier(system="npm", name="react", version="18.2.0")

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/react/versions/18.2.0",
        json={"lineCount": 5000},
    )

    loc = get_package_loc(pkg)

    assert loc == 5000


def test_get_package_loc_returns_none_when_missing(httpx_mock: HTTPXMock) -> None:
    from iceberg.depsdev import get_package_loc

    pkg = create_package_identifier(system="npm", name="react", version="18.2.0")

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/react/versions/18.2.0",
        json={},
    )

    loc = get_package_loc(pkg)

    assert loc is None


def test_get_package_loc_handles_network_error(httpx_mock: HTTPXMock) -> None:
    from iceberg.depsdev import DepsDevError, get_package_loc

    pkg = create_package_identifier(system="npm", name="react", version="18.2.0")

    httpx_mock.add_exception(Exception("Network error"))

    with pytest.raises(DepsDevError) as exc_info:
        get_package_loc(pkg)

    assert "Failed to fetch package LoC" in str(exc_info.value)
