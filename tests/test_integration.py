from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock
from typer.testing import CliRunner


def test_full_workflow_fetch_and_analyze(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    """Test complete workflow: fetch trending repos, then analyze one."""
    from iceberg.cache import load_loc_metrics, load_trending_repos
    from iceberg.cli import app

    trending_html = """
    <article class="Box-row">
      <h2 class="h3 lh-condensed">
        <a href="/facebook/react">
          <span class="text-normal">facebook /</span>
          react
        </a>
      </h2>
      <p class="col-9 color-fg-muted my-1 pr-4">
        A JavaScript library for building user interfaces
      </p>
      <div class="f6 color-fg-muted mt-2">
        <span class="d-inline-block ml-0 mr-3">
          <span itemprop="programmingLanguage">JavaScript</span>
        </span>
        <span class="d-inline-block mr-3">
          <svg aria-label="star"></svg>
          200,000
        </span>
      </div>
    </article>
    """

    httpx_mock.add_response(
        url="https://github.com/trending",
        text=trending_html,
    )

    runner = CliRunner()
    result = runner.invoke(app, ["fetch", "--cache-dir", str(tmp_path)])

    assert result.exit_code == 0
    assert "Fetched 1 trending" in result.stdout

    cached_repos = load_trending_repos(cache_dir=tmp_path)
    assert cached_repos is not None
    assert len(cached_repos) == 1
    assert cached_repos[0].name == "react"
    assert cached_repos[0].owner == "facebook"

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/projects/github.com%2Ffacebook%2Freact",
        json={"lineCount": 50000},
    )

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/react/versions/18.2.0",
        json={"lineCount": 10000},
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

    result = runner.invoke(
        app,
        [
            "analyze",
            "facebook/react",
            "--package",
            "npm:react:18.2.0",
            "--cache-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "facebook/react" in result.stdout
    assert "50,000" in result.stdout

    from iceberg.models import PackageIdentifier

    pkg = PackageIdentifier(system="npm", name="react", version="18.2.0")
    cached_metrics = load_loc_metrics(pkg, cache_dir=tmp_path)
    assert cached_metrics is not None
    assert cached_metrics.total_lines == 10000


def test_cache_reuse_on_second_analysis(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    """Test that cached data is reused on subsequent analysis."""
    from iceberg.cli import app

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/projects/github.com%2Fowner%2Frepo",
        json={"lineCount": 5000},
    )

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/test-pkg/versions/1.0.0",
        json={"lineCount": 1000},
    )

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/test-pkg/versions/1.0.0:dependencies",
        json={"dependencies": []},
    )

    runner = CliRunner()
    result1 = runner.invoke(
        app,
        [
            "analyze",
            "owner/repo",
            "--package",
            "npm:test-pkg:1.0.0",
            "--cache-dir",
            str(tmp_path),
        ],
    )

    assert result1.exit_code == 0

    requests_first_run = len(httpx_mock.get_requests())

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/projects/github.com%2Fowner%2Frepo",
        json={"lineCount": 5000},
    )

    result2 = runner.invoke(
        app,
        [
            "analyze",
            "owner/repo",
            "--package",
            "npm:test-pkg:1.0.0",
            "--cache-dir",
            str(tmp_path),
        ],
    )

    assert result2.exit_code == 0

    requests_second_run = len(httpx_mock.get_requests())

    assert requests_second_run == requests_first_run + 1


def test_json_output_integration(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    """Test JSON output format works end-to-end."""
    import json

    from iceberg.cli import app

    trending_html = """
    <article class="Box-row">
      <h2 class="h3 lh-condensed">
        <a href="/owner/repo">
          <span class="text-normal">owner /</span>
          repo
        </a>
      </h2>
      <div class="f6 color-fg-muted mt-2">
        <span class="d-inline-block mr-3"><svg aria-label="star"></svg>100</span>
      </div>
    </article>
    """

    httpx_mock.add_response(
        url="https://github.com/trending",
        text=trending_html,
    )

    runner = CliRunner()
    result = runner.invoke(app, ["fetch", "--json", "--cache-dir", str(tmp_path)])

    assert result.exit_code == 0

    data = json.loads(result.stdout)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["name"] == "repo"
    assert data[0]["stars"] == 100

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/projects/github.com%2Fowner%2Frepo",
        json={"lineCount": 5000},
    )

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/test/versions/1.0.0",
        json={"lineCount": 1000},
    )

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/test/versions/1.0.0:dependencies",
        json={"dependencies": []},
    )

    result = runner.invoke(
        app,
        [
            "analyze",
            "owner/repo",
            "--package",
            "npm:test:1.0.0",
            "--json",
            "--cache-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0

    data = json.loads(result.stdout)
    assert data["repo"] == "owner/repo"
    assert data["project_loc"] == 5000
    assert data["total_loc"] == 1000
