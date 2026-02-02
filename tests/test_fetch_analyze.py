from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock
from typer.testing import CliRunner


def test_fetch_with_analyze_flag(httpx_mock: HTTPXMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test fetch command with --analyze flag."""
    from iceberg.cli import app

    # Mock cloning and LoC counting
    def mock_clone_repository(
        owner: str, name: str, target_dir: Path | None = None, ref: str | None = None
    ) -> dict:
        return {
            "duration_seconds": 1.0,
            "repo_url": f"https://github.com/{owner}/{name}.git",
            "ref": ref or "HEAD",
            "commit_hash": "abc123",
        }

    def mock_count_repo_loc(repo_dir: Path) -> dict:
        return {
            "loc": 5000,
            "duration_seconds": 0.5,
        }

    # Mock osv-scanner to return None (no dependencies found)
    def mock_run_osv_scanner(repo_path: Path) -> str | None:
        return None

    monkeypatch.setattr("iceberg.calculator.clone_repository", mock_clone_repository)
    monkeypatch.setattr("iceberg.calculator.count_repo_loc", mock_count_repo_loc)
    monkeypatch.setattr("iceberg.calculator.run_osv_scanner", mock_run_osv_scanner)

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

    # Mock auto-detect (for package detection via HTTP)
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
        text="""
[project]
name = "test-pkg"
version = "1.0.0"
""",
    )

    # Mock AI marker checks (all 404)
    for path in ["CLAUDE.md", ".claude/CLAUDE.md", ".clauderc", ".cursor/", ".cursorrules",
                 ".github/copilot-instructions.md", ".aider/", ".aider.conf.yml",
                 "AI_INSTRUCTIONS.md", "AGENTS.md", ".ai/"]:
        for branch in ["main", "master"]:
            httpx_mock.add_response(
                url=f"https://api.github.com/repos/owner/repo/contents/{path}?ref={branch}",
                status_code=404,
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
    assert "Dependencies" in result.stdout and "LoC" in result.stdout


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
    # Should indicate already analyzed
    assert "already" in result.stdout.lower()
