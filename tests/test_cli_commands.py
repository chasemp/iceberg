import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner


def _write_repo_metadata(
    cache_dir: Path, owner: str, repo: str, stars: int = 100
) -> None:
    repos_dir = cache_dir / "repos" / owner
    repos_dir.mkdir(parents=True, exist_ok=True)
    (repos_dir / f"{repo}.json").write_text(
        json.dumps({"owner": owner, "name": repo, "stars": stars})
    )


def _write_analysis(
    cache_dir: Path,
    owner: str,
    repo: str,
    hours_ago: float = 48,
    loc: int = 5000,
    total_loc: int | None = None,
    ai_markers: list[str] | None = None,
) -> None:
    project_dir = cache_dir / "projects" / owner / repo
    project_dir.mkdir(parents=True, exist_ok=True)
    cached_at = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()
    data: dict = {
        "owner": owner,
        "repo": repo,
        "version": "HEAD",
        "loc": loc,
        "source": "github_clone",
        "cached_at": cached_at,
    }
    if total_loc is not None:
        data["total_loc"] = total_loc
    if ai_markers is not None:
        data["ai_markers"] = ai_markers
    (project_dir / "HEAD.json").write_text(json.dumps(data))


def _write_spa_index(cache_dir: Path, repos: list[dict]) -> None:
    spa_dir = cache_dir.parent / "spa" / "data"
    spa_dir.mkdir(parents=True, exist_ok=True)
    index = {
        "dimensions": [
            {
                "name": "trending",
                "repos": repos,
            }
        ]
    }
    (spa_dir / "index.json").write_text(json.dumps(index))


def test_status_shows_counts(tmp_path: Path) -> None:
    from iceberg.cli import app

    _write_repo_metadata(tmp_path, "owner1", "repo1", stars=100)
    _write_repo_metadata(tmp_path, "owner2", "repo2", stars=200)
    _write_analysis(tmp_path, "owner1", "repo1", hours_ago=12)
    _write_spa_index(
        tmp_path,
        [{"owner": "owner1", "name": "repo1"}],
    )

    runner = CliRunner()
    result = runner.invoke(app, ["status", "--cache-dir", str(tmp_path)])

    assert result.exit_code == 0
    assert "Discovered repos:     2" in result.output
    assert "Analyzed repos:       1" in result.output
    assert "Exported to SPA:      1" in result.output


def test_status_shows_age_buckets(tmp_path: Path) -> None:
    from iceberg.cli import app

    _write_repo_metadata(tmp_path, "a", "recent", stars=100)
    _write_analysis(tmp_path, "a", "recent", hours_ago=6)

    _write_repo_metadata(tmp_path, "b", "weekold", stars=100)
    _write_analysis(tmp_path, "b", "weekold", hours_ago=3 * 24)

    _write_repo_metadata(tmp_path, "c", "monthish", stars=100)
    _write_analysis(tmp_path, "c", "monthish", hours_ago=15 * 24)

    runner = CliRunner()
    result = runner.invoke(app, ["status", "--cache-dir", str(tmp_path)])

    assert result.exit_code == 0
    assert "< 1 day" in result.output
    assert "1-7 days" in result.output
    assert "7-30 days" in result.output


def test_status_json_output(tmp_path: Path) -> None:
    from iceberg.cli import app

    _write_repo_metadata(tmp_path, "owner1", "repo1", stars=100)
    _write_analysis(tmp_path, "owner1", "repo1", hours_ago=12)

    runner = CliRunner()
    result = runner.invoke(app, ["status", "--json", "--cache-dir", str(tmp_path)])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["discovered"] == 1
    assert data["analyzed"] == 1
    assert "age_buckets" in data


def test_status_verbose_shows_per_repo(tmp_path: Path) -> None:
    from iceberg.cli import app

    _write_repo_metadata(tmp_path, "owner1", "repo1", stars=100)
    _write_analysis(tmp_path, "owner1", "repo1", hours_ago=48)

    runner = CliRunner()
    result = runner.invoke(app, ["status", "-v", "--cache-dir", str(tmp_path)])

    assert result.exit_code == 0
    assert "owner1/repo1" in result.output
    assert "Per-repo details" in result.output


def test_status_counts_dependencies_and_ai(tmp_path: Path) -> None:
    from iceberg.cli import app

    _write_repo_metadata(tmp_path, "a", "withdeps", stars=100)
    _write_analysis(tmp_path, "a", "withdeps", hours_ago=12, total_loc=50000)

    _write_repo_metadata(tmp_path, "b", "withai", stars=100)
    _write_analysis(tmp_path, "b", "withai", hours_ago=12, ai_markers=["copilot"])

    runner = CliRunner()
    result = runner.invoke(app, ["status", "--cache-dir", str(tmp_path)])

    assert result.exit_code == 0
    assert "With dependencies:  1" in result.output
    assert "With AI markers:    1" in result.output


def test_status_handles_empty_cache(tmp_path: Path) -> None:
    from iceberg.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["status", "--cache-dir", str(tmp_path)])

    assert result.exit_code == 0
    assert "Discovered repos:     0" in result.output
    assert "Analyzed repos:       0" in result.output


def test_run_analysis_analyzes_stale_repos(tmp_path: Path) -> None:
    from iceberg.cli import app

    _write_repo_metadata(tmp_path, "owner1", "repo1", stars=100)

    def mock_analyze_repository(owner, repo, cache_dir=None, verbose=False, force=False, **kwargs):
        _write_analysis(cache_dir, owner, repo, hours_ago=0, loc=1234)
        return {"project_loc": 1234, "loc": 1234}

    runner = CliRunner()
    with patch("iceberg.calculator.analyze_repository", side_effect=mock_analyze_repository):
        result = runner.invoke(
            app,
            ["run-analysis", "--batch-size", "5", "--cache-dir", str(tmp_path)],
        )

    assert result.exit_code == 0
    assert "Analyzed:" in result.output or "1,234" in result.output


def test_run_analysis_skips_fresh_repos(tmp_path: Path) -> None:
    from iceberg.cli import app

    _write_repo_metadata(tmp_path, "owner1", "repo1", stars=100)
    _write_analysis(tmp_path, "owner1", "repo1", hours_ago=0.1)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["run-analysis", "-v", "--cache-dir", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "Skipped:" in result.output
    assert "Analyzing: 0" in result.output


def test_run_analysis_force_overrides_staleness(tmp_path: Path) -> None:
    from iceberg.cli import app

    _write_repo_metadata(tmp_path, "owner1", "repo1", stars=100)
    _write_analysis(tmp_path, "owner1", "repo1", hours_ago=0.1)

    def mock_analyze_repository(owner, repo, cache_dir=None, verbose=False, force=False, **kwargs):
        return {"project_loc": 1234, "loc": 1234}

    runner = CliRunner()
    with patch("iceberg.calculator.analyze_repository", side_effect=mock_analyze_repository):
        result = runner.invoke(
            app,
            ["run-analysis", "--force", "--batch-size", "5", "--cache-dir", str(tmp_path)],
        )

    assert result.exit_code == 0
    assert "FORCE" in result.output
    assert "Analyzing: 1" in result.output


def test_run_analysis_respects_batch_size(tmp_path: Path) -> None:
    from iceberg.cli import app

    for i in range(5):
        _write_repo_metadata(tmp_path, f"owner{i}", f"repo{i}", stars=100)

    call_count = 0

    def mock_analyze_repository(owner, repo, cache_dir=None, verbose=False, force=False, **kwargs):
        nonlocal call_count
        call_count += 1
        return {"project_loc": 1000, "loc": 1000}

    runner = CliRunner()
    with patch("iceberg.calculator.analyze_repository", side_effect=mock_analyze_repository):
        result = runner.invoke(
            app,
            ["run-analysis", "--batch-size", "2", "--cache-dir", str(tmp_path)],
        )

    assert result.exit_code == 0
    assert call_count == 2
    assert "Remaining:  3" in result.output


def test_discover_command_calls_discovery(tmp_path: Path) -> None:
    from iceberg.cli import app

    mock_results = {
        "total_fetched": 100,
        "unique_repos": 80,
        "sources_saved": 5,
        "repos_saved": 80,
        "sources": {"trending-monthly": 25, "search": 75},
    }

    runner = CliRunner()
    with patch("iceberg.discovery.run_discovery", return_value=mock_results):
        result = runner.invoke(
            app,
            ["discover", "--cache-dir", str(tmp_path)],
        )

    assert result.exit_code == 0
    assert "Discovery complete" in result.output
    assert "Total fetched:  100" in result.output
    assert "Unique repos:   80" in result.output


def test_discover_verbose_shows_sources(tmp_path: Path) -> None:
    from iceberg.cli import app

    mock_results = {
        "total_fetched": 100,
        "unique_repos": 80,
        "sources_saved": 5,
        "repos_saved": 80,
        "sources": {"trending-monthly": 25, "search": 75},
    }

    runner = CliRunner()
    with patch("iceberg.discovery.run_discovery", return_value=mock_results):
        result = runner.invoke(
            app,
            ["discover", "-v", "--cache-dir", str(tmp_path)],
        )

    assert result.exit_code == 0
    assert "By source:" in result.output
    assert "trending-monthly: 25" in result.output
    assert "search: 75" in result.output
