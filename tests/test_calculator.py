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


def test_analyze_repository_uses_osv_scanner(
    httpx_mock: HTTPXMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that analyze_repository uses osv-scanner to discover dependencies."""
    from iceberg.calculator import analyze_repository

    # Mock cloning
    def mock_clone_repository(
        owner: str, name: str, target_dir: Path | None = None, ref: str | None = None
    ) -> dict:
        return {
            "duration_seconds": 1.0,
            "repo_url": f"https://github.com/{owner}/{name}.git",
            "ref": ref or "HEAD",
            "commit_hash": "abc123",
        }

    # Mock LoC counting
    def mock_count_repo_loc(repo_dir: Path) -> dict:
        return {
            "loc": 10000,
            "duration_seconds": 0.5,
        }

    # Mock osv-scanner output with dependencies
    def mock_run_osv_scanner(repo_path: Path) -> str:
        return """
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

    # Mock package detection to return None (osv-scanner will be primary)
    def mock_detect_package(owner: str, repo: str) -> None:
        return None

    # Mock AI detection
    def mock_detect_ai_markers(owner: str, repo: str) -> dict:
        return {}

    monkeypatch.setattr("iceberg.calculator.clone_repository", mock_clone_repository)
    monkeypatch.setattr("iceberg.calculator.count_repo_loc", mock_count_repo_loc)
    monkeypatch.setattr("iceberg.calculator.run_osv_scanner", mock_run_osv_scanner)
    monkeypatch.setattr("iceberg.calculator.detect_package", mock_detect_package)
    monkeypatch.setattr("iceberg.calculator.detect_ai_markers", mock_detect_ai_markers)

    # Mock deps.dev API for dependency LoC
    # (osv-scanner gives flat list, so no :dependencies endpoints needed)
    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/react/versions/18.2.0",
        json={"lineCount": 5000},
    )
    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/lodash/versions/4.17.21",
        json={"lineCount": 3000},
    )

    result = analyze_repository("facebook", "react", cache_dir=tmp_path, verbose=True)

    assert result is not None
    assert result["project_loc"] == 10000
    assert result["total_loc"] == 8000  # 5000 (react) + 3000 (lodash)
    assert result["ratio"] > 0  # Dependencies ratio should be calculated


def test_analyze_repository_checkouts_release_tag_when_version_detected(
    httpx_mock: HTTPXMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that analyze_repository checks out release tag when package version is detected."""
    from iceberg.calculator import analyze_repository
    from iceberg.models import PackageIdentifier

    checkout_ref_called_with: list[str | None] = []

    # Mock cloning - track what ref is requested
    def mock_clone_repository(
        owner: str, name: str, target_dir: Path | None = None, ref: str | None = None
    ) -> dict:
        checkout_ref_called_with.append(ref)
        return {
            "duration_seconds": 1.0,
            "repo_url": f"https://github.com/{owner}/{name}.git",
            "ref": ref or "HEAD",
            "commit_hash": "abc123",
        }

    def mock_count_repo_loc(repo_dir: Path) -> dict:
        return {"loc": 10000, "duration_seconds": 0.5}

    def mock_run_osv_scanner(repo_path: Path) -> str | None:
        return None

    # Mock package detection to return a version
    def mock_detect_package(owner: str, repo: str) -> PackageIdentifier:
        return PackageIdentifier(system="npm", name="test-pkg", version="1.2.3")

    def mock_detect_ai_markers(owner: str, repo: str) -> dict:
        return {}

    monkeypatch.setattr("iceberg.calculator.clone_repository", mock_clone_repository)
    monkeypatch.setattr("iceberg.calculator.count_repo_loc", mock_count_repo_loc)
    monkeypatch.setattr("iceberg.calculator.run_osv_scanner", mock_run_osv_scanner)
    monkeypatch.setattr("iceberg.calculator.detect_package", mock_detect_package)
    monkeypatch.setattr("iceberg.calculator.detect_ai_markers", mock_detect_ai_markers)

    result = analyze_repository("owner", "repo", cache_dir=tmp_path)

    assert result is not None
    # Should have attempted to clone with the version tag
    assert len(checkout_ref_called_with) > 0
    # First attempt should be with the version tag (v1.2.3 or 1.2.3)
    first_ref = checkout_ref_called_with[0]
    assert first_ref in ["v1.2.3", "1.2.3"]


def test_analyze_repository_force_bypasses_cache(
    httpx_mock: HTTPXMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that force=True re-analyzes even when cache exists."""
    import json
    from iceberg.calculator import analyze_repository

    # Pre-populate cache with stale data (no ai_markers, no total_loc)
    projects_dir = tmp_path / "projects" / "owner" / "repo"
    projects_dir.mkdir(parents=True)
    (projects_dir / "HEAD.json").write_text(json.dumps({
        "owner": "owner", "repo": "repo", "version": "HEAD",
        "loc": 5000, "source": "github_clone",
        "cached_at": "2026-01-01T00:00:00Z",
    }))

    clone_called = []

    def mock_clone_repository(
        owner: str, name: str, target_dir: Path | None = None, ref: str | None = None
    ) -> dict:
        clone_called.append(True)
        return {
            "duration_seconds": 1.0,
            "repo_url": f"https://github.com/{owner}/{name}.git",
            "ref": ref or "HEAD",
            "commit_hash": "def456",
        }

    def mock_count_repo_loc(repo_dir: Path) -> dict:
        return {"loc": 8000, "duration_seconds": 0.5}

    def mock_run_osv_scanner(repo_path: Path) -> str | None:
        return None

    def mock_detect_package(owner: str, repo: str) -> None:
        return None

    def mock_detect_ai_markers(owner: str, repo: str) -> dict:
        return {"claude": True, "cursor": False, "copilot": False, "aider": False,
                "windsurf": False, "cline": False, "codex": False, "generic_ai": False}

    monkeypatch.setattr("iceberg.calculator.clone_repository", mock_clone_repository)
    monkeypatch.setattr("iceberg.calculator.count_repo_loc", mock_count_repo_loc)
    monkeypatch.setattr("iceberg.calculator.run_osv_scanner", mock_run_osv_scanner)
    monkeypatch.setattr("iceberg.calculator.detect_package", mock_detect_package)
    monkeypatch.setattr("iceberg.calculator.detect_ai_markers", mock_detect_ai_markers)

    # Without force — returns cached (stale) data
    result_cached = analyze_repository("owner", "repo", cache_dir=tmp_path)
    assert result_cached is not None
    assert result_cached["loc"] == 5000
    assert len(clone_called) == 0  # Should not have cloned

    # With force — re-analyzes
    result_fresh = analyze_repository("owner", "repo", cache_dir=tmp_path, force=True)
    assert result_fresh is not None
    assert len(clone_called) == 1  # Should have cloned
    assert result_fresh["project_loc"] == 8000  # New LoC from fresh analysis

    # Verify the saved cache file was updated
    updated = json.loads((projects_dir / "HEAD.json").read_text())
    assert updated["loc"] == 8000
    assert updated["ai_markers"]["claude"] is True
    assert "Claude" in updated["ai_tools"]
