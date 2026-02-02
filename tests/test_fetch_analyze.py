from pathlib import Path

from pytest_httpx import HTTPXMock
from typer.testing import CliRunner


def test_fetch_with_analyze_flag(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    """Test fetch command with --analyze flag."""
    from iceberg.cli import app

    # Mock GitHub trending page
    trending_html = """
    <article class="Box-row">
        <h2 class="h3">
            <a href="/owner/repo">repo</a>
        </h2>
        <p class="col-9">A test repo</p>
        <div>
            <span itemprop="programmingLanguage">Python</span>
            <span><svg aria-label="star"></svg>1234</span>
        </div>
    </article>
    """
    httpx_mock.add_response(
        url="https://github.com/trending",
        text=trending_html,
    )

    # Mock auto-detect
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
        json={
            "[project]": {"name": "test-pkg", "version": "1.0.0", "dependencies": []},
        },
    )

    # Mock deps.dev
    httpx_mock.add_response(
        url="https://api.deps.dev/v3/projects/github.com%2Fowner%2Frepo",
        json={"lineCount": 5000},
    )
    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/pypi/packages/test-pkg/versions/1.0.0",
        json={"lineCount": 1000},
    )
    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/pypi/packages/test-pkg/versions/1.0.0:dependencies",
        json={"dependencies": []},
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["fetch", "--limit", "1", "--analyze", "--head", "--cache-dir", str(tmp_path)],
    )

    assert result.exit_code == 0
    # Should show fetch results
    assert "Fetched" in result.stdout
    # Should show analysis
    assert "Analyzing" in result.stdout or "owner/repo" in result.stdout
    assert "Total LoC" in result.stdout


def test_fetch_analyze_skips_already_analyzed(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    """Test that fetch --analyze skips repos that were already analyzed."""
    from iceberg.cache import save_project_loc
    from iceberg.cli import app

    # Pre-populate cache with analyzed project
    save_project_loc(
        {
            "owner": "owner",
            "repo": "repo",
            "version": "HEAD",
            "loc": 5000,
            "source": "github_clone",
            "cached_at": "2026-02-02T12:00:00Z",
            "ref": "HEAD",
            "repo_url": "https://github.com/owner/repo.git",
            "clone_duration_seconds": 1.0,
            "count_duration_seconds": 0.5,
        },
        cache_dir=tmp_path,
    )

    # Mock GitHub trending
    trending_html = """
    <article class="Box-row">
        <h2 class="h3">
            <a href="/owner/repo">repo</a>
        </h2>
        <p class="col-9">A test repo</p>
        <div>
            <span itemprop="programmingLanguage">Python</span>
            <span><svg aria-label="star"></svg>1234</span>
        </div>
    </article>
    """
    httpx_mock.add_response(
        url="https://github.com/trending",
        text=trending_html,
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["fetch", "--limit", "1", "--analyze", "--head", "--cache-dir", str(tmp_path)],
    )

    assert result.exit_code == 0
    # Should indicate cache was used
    assert "cached" in result.stdout.lower() or "skipping" in result.stdout.lower()
