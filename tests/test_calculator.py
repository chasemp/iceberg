from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock

from tests.factories import create_package_identifier


def test_calculate_package_loc_fetches_from_api(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    from iceberg.calculator import calculate_package_loc

    pkg = create_package_identifier(system="npm", name="react", version="18.2.0")

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/react/versions/18.2.0",
        json={"lineCount": 5000},
    )

    loc = calculate_package_loc(pkg, cache_dir=tmp_path)

    assert loc == 5000


def test_calculate_package_loc_uses_cache(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    from iceberg.cache import save_loc_metrics
    from iceberg.calculator import calculate_package_loc
    from iceberg.models import LocMetrics

    pkg = create_package_identifier(system="npm", name="react", version="18.2.0")

    metrics = LocMetrics(
        package=pkg,
        total_lines=5000,
        source="depsdev",
        cached_at="2026-01-30T12:00:00Z",
    )
    save_loc_metrics(metrics, cache_dir=tmp_path)

    loc = calculate_package_loc(pkg, cache_dir=tmp_path)

    assert loc == 5000
    assert len(httpx_mock.get_requests()) == 0


def test_calculate_package_loc_caches_result(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    from iceberg.cache import load_loc_metrics
    from iceberg.calculator import calculate_package_loc

    pkg = create_package_identifier(system="npm", name="react", version="18.2.0")

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/react/versions/18.2.0",
        json={"lineCount": 5000},
    )

    calculate_package_loc(pkg, cache_dir=tmp_path)

    cached_metrics = load_loc_metrics(pkg, cache_dir=tmp_path)
    assert cached_metrics is not None
    assert cached_metrics.total_lines == 5000


def test_calculate_package_loc_returns_zero_when_missing(
    httpx_mock: HTTPXMock, tmp_path: Path
) -> None:
    from iceberg.calculator import calculate_package_loc

    pkg = create_package_identifier(system="npm", name="react", version="18.2.0")

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/react/versions/18.2.0",
        json={},
    )

    # Mock npm registry fallback to also fail
    httpx_mock.add_response(
        url="https://registry.npmjs.org/react/18.2.0",
        status_code=404,
    )

    loc = calculate_package_loc(pkg, cache_dir=tmp_path)

    assert loc == 0


def test_calculate_transitive_loc_single_package(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    from iceberg.calculator import calculate_transitive_loc

    pkg = create_package_identifier(system="npm", name="react", version="18.2.0")

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/react/versions/18.2.0",
        json={"lineCount": 5000},
    )

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/react/versions/18.2.0:dependencies",
        json={"dependencies": []},
    )

    total_loc = calculate_transitive_loc(pkg, cache_dir=tmp_path)

    assert total_loc == 5000


def test_calculate_transitive_loc_with_dependencies(
    httpx_mock: HTTPXMock, tmp_path: Path
) -> None:
    from iceberg.calculator import calculate_transitive_loc

    pkg = create_package_identifier(system="npm", name="react", version="18.2.0")

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/react/versions/18.2.0",
        json={"lineCount": 5000},
    )

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/react/versions/18.2.0:dependencies",
        json={
            "dependencies": [
                {
                    "requirement": "^1.0.0",
                    "package": {"system": "npm", "name": "loose-envify"},
                    "version": "1.4.0",
                }
            ]
        },
    )

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/loose-envify/versions/1.4.0",
        json={"lineCount": 100},
    )

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/loose-envify/versions/1.4.0:dependencies",
        json={"dependencies": []},
    )

    total_loc = calculate_transitive_loc(pkg, cache_dir=tmp_path)

    assert total_loc == 5100


def test_calculate_transitive_loc_handles_circular_deps(
    httpx_mock: HTTPXMock, tmp_path: Path
) -> None:
    from iceberg.calculator import calculate_transitive_loc

    pkg_a = create_package_identifier(system="npm", name="pkg-a", version="1.0.0")

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/pkg-a/versions/1.0.0",
        json={"lineCount": 1000},
    )

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/pkg-a/versions/1.0.0:dependencies",
        json={
            "dependencies": [
                {
                    "requirement": "^1.0.0",
                    "package": {"system": "npm", "name": "pkg-b"},
                    "version": "1.0.0",
                }
            ]
        },
    )

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/pkg-b/versions/1.0.0",
        json={"lineCount": 2000},
    )

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/pkg-b/versions/1.0.0:dependencies",
        json={
            "dependencies": [
                {
                    "requirement": "^1.0.0",
                    "package": {"system": "npm", "name": "pkg-a"},
                    "version": "1.0.0",
                }
            ]
        },
    )

    total_loc = calculate_transitive_loc(pkg_a, cache_dir=tmp_path)

    assert total_loc == 3000


def test_calculate_transitive_loc_uses_cache(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    from iceberg.cache import save_dependencies, save_loc_metrics
    from iceberg.calculator import calculate_transitive_loc
    from iceberg.models import LocMetrics

    pkg = create_package_identifier(system="npm", name="react", version="18.2.0")
    dep = create_package_identifier(system="npm", name="loose-envify", version="1.4.0")

    pkg_metrics = LocMetrics(
        package=pkg,
        total_lines=5000,
        source="depsdev",
        cached_at="2026-01-30T12:00:00Z",
    )
    save_loc_metrics(pkg_metrics, cache_dir=tmp_path)

    dep_metrics = LocMetrics(
        package=dep,
        total_lines=100,
        source="depsdev",
        cached_at="2026-01-30T12:00:00Z",
    )
    save_loc_metrics(dep_metrics, cache_dir=tmp_path)

    save_dependencies(pkg, [dep], cache_dir=tmp_path)
    save_dependencies(dep, [], cache_dir=tmp_path)

    total_loc = calculate_transitive_loc(pkg, cache_dir=tmp_path)

    assert total_loc == 5100
    assert len(httpx_mock.get_requests()) == 0


def test_calculate_package_loc_includes_timing_data(
    httpx_mock: HTTPXMock, tmp_path: Path
) -> None:
    from iceberg.calculator import calculate_package_loc
    from iceberg.cache import load_loc_metrics

    pkg = create_package_identifier(system="npm", name="test-pkg", version="1.0.0")

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/test-pkg/versions/1.0.0",
        json={"lineCount": 1000},
    )

    calculate_package_loc(pkg, cache_dir=tmp_path)

    cached_metrics = load_loc_metrics(pkg, cache_dir=tmp_path)
    assert cached_metrics is not None
    assert cached_metrics.fetch_duration_seconds is not None
    assert cached_metrics.fetch_duration_seconds >= 0
