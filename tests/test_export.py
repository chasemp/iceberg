import json
from pathlib import Path

from tests.factories import create_discovered_repo


def test_export_discovery_index_creates_structured_output(tmp_path: Path) -> None:
    from datetime import datetime, timezone

    from iceberg.cache import save_discovered_repos
    from iceberg.export import export_discovery_index

    # Create some test data
    repos = [
        create_discovered_repo(name="repo1", owner="owner1", source="trending-daily", stars=1000),
        create_discovered_repo(name="repo2", owner="owner2", source="trending-daily", stars=2000),
    ]

    cache_dir = tmp_path / "cache"
    save_discovered_repos(repos, cache_dir=cache_dir)

    # Export
    output_dir = tmp_path / "export"
    result = export_discovery_index(output_dir, cache_dir=cache_dir)

    assert result["dimensions_exported"] == 1
    assert (output_dir / "index.json").exists()

    # Verify structure
    index = json.loads((output_dir / "index.json").read_text())
    assert "dimensions" in index
    assert "generated_at" in index
    assert len(index["dimensions"]) == 1

    dimension = index["dimensions"][0]
    assert dimension["id"] == "trending-daily"
    assert dimension["type"] == "trending"
    assert dimension["timeframe"] == "daily"
    assert len(dimension["snapshots"]) == 1

    snapshot = dimension["snapshots"][0]
    assert snapshot["count"] == 2
    assert len(snapshot["repos"]) == 2
    assert snapshot["repos"][0]["name"] == "repo1"
    assert snapshot["repos"][0]["stars"] == 1000


def test_export_discovery_index_with_multiple_dimensions(tmp_path: Path) -> None:
    from iceberg.cache import save_discovered_repos
    from iceberg.export import export_discovery_index

    # Create trending-daily
    daily_repos = [create_discovered_repo(name="daily1", source="trending-daily")]
    cache_dir = tmp_path / "cache"
    save_discovered_repos(daily_repos, cache_dir=cache_dir)

    # Create trending-weekly
    weekly_repos = [create_discovered_repo(name="weekly1", source="trending-weekly")]
    save_discovered_repos(weekly_repos, cache_dir=cache_dir)

    # Create search
    search_repos = [
        create_discovered_repo(
            name="search1",
            source="search",
            search_query="stars:>10000",
        )
    ]
    save_discovered_repos(search_repos, cache_dir=cache_dir)

    # Export
    output_dir = tmp_path / "export"
    result = export_discovery_index(output_dir, cache_dir=cache_dir)

    assert result["dimensions_exported"] == 3

    index = json.loads((output_dir / "index.json").read_text())
    dimension_ids = {d["id"] for d in index["dimensions"]}
    assert "trending-daily" in dimension_ids
    assert "trending-weekly" in dimension_ids
    assert any("search:" in d_id for d_id in dimension_ids)


def test_export_repository_details_creates_per_repo_files(tmp_path: Path) -> None:
    from iceberg.export import export_repository_details

    # Create test project data
    cache_dir = tmp_path / "cache"
    projects_dir = cache_dir / "projects" / "facebook" / "react"
    projects_dir.mkdir(parents=True)

    analysis = {
        "owner": "facebook",
        "repo": "react",
        "version": "HEAD",
        "loc": 50000,
        "source": "github_clone",
        "cached_at": "2026-02-02T12:00:00Z",
    }

    (projects_dir / "HEAD.json").write_text(json.dumps(analysis))

    # Export
    output_dir = tmp_path / "export"
    result = export_repository_details(output_dir, cache_dir=cache_dir)

    assert result["repos_exported"] == 1

    repo_file = output_dir / "repos" / "facebook-react.json"
    assert repo_file.exists()

    repo_data = json.loads(repo_file.read_text())
    assert repo_data["owner"] == "facebook"
    assert repo_data["repo"] == "react"
    assert repo_data["full_name"] == "facebook/react"
    assert repo_data["analysis"]["loc"] == 50000


def test_export_all_runs_all_exports(tmp_path: Path) -> None:
    from iceberg.cache import save_discovered_repos
    from iceberg.export import export_all

    # Create test data
    repos = [create_discovered_repo(name="test", source="trending-daily")]
    cache_dir = tmp_path / "cache"
    save_discovered_repos(repos, cache_dir=cache_dir)

    # Create project data
    projects_dir = cache_dir / "projects" / "owner" / "test"
    projects_dir.mkdir(parents=True)
    (projects_dir / "HEAD.json").write_text(json.dumps({"loc": 1000}))

    # Export all
    output_dir = tmp_path / "export"
    results = export_all(output_dir, cache_dir=cache_dir)

    assert "discovery_index" in results
    assert "repository_details" in results
    assert (output_dir / "index.json").exists()
    assert (output_dir / "repos" / "owner-test.json").exists()


def test_export_handles_empty_cache(tmp_path: Path) -> None:
    from iceberg.export import export_discovery_index

    cache_dir = tmp_path / "cache"
    output_dir = tmp_path / "export"

    result = export_discovery_index(output_dir, cache_dir=cache_dir)

    assert result["dimensions_exported"] == 0
    assert (output_dir / "index.json").exists()

    index = json.loads((output_dir / "index.json").read_text())
    assert index["dimensions"] == []


def test_export_discovery_index_includes_ai_tools(tmp_path: Path) -> None:
    """Test that AI tools information is included in repo summaries."""
    from iceberg.cache import save_discovered_repos
    from iceberg.export import export_discovery_index

    # Create discovered repos
    repos = [
        create_discovered_repo(name="repo-with-ai", owner="owner1", source="trending-daily", stars=1000),
        create_discovered_repo(name="repo-without-ai", owner="owner2", source="trending-daily", stars=2000),
    ]

    cache_dir = tmp_path / "cache"
    save_discovered_repos(repos, cache_dir=cache_dir)

    # Create analyzed project data with AI tools for first repo
    projects_dir = cache_dir / "projects" / "owner1" / "repo-with-ai"
    projects_dir.mkdir(parents=True)
    analysis_with_ai = {
        "owner": "owner1",
        "repo": "repo-with-ai",
        "version": "HEAD",
        "loc": 50000,
        "ai_tools": ["Claude", "GitHub Copilot"],
        "source": "github_clone",
        "cached_at": "2026-02-02T12:00:00Z",
    }
    (projects_dir / "HEAD.json").write_text(json.dumps(analysis_with_ai))

    # Create analyzed project data without AI tools for second repo
    projects_dir2 = cache_dir / "projects" / "owner2" / "repo-without-ai"
    projects_dir2.mkdir(parents=True)
    analysis_without_ai = {
        "owner": "owner2",
        "repo": "repo-without-ai",
        "version": "HEAD",
        "loc": 30000,
        "source": "github_clone",
        "cached_at": "2026-02-02T12:00:00Z",
    }
    (projects_dir2 / "HEAD.json").write_text(json.dumps(analysis_without_ai))

    # Export
    output_dir = tmp_path / "export"
    result = export_discovery_index(output_dir, cache_dir=cache_dir)

    # Verify
    index = json.loads((output_dir / "index.json").read_text())
    snapshot = index["dimensions"][0]["snapshots"][0]

    # First repo should have ai_tools
    repo1 = next(r for r in snapshot["repos"] if r["name"] == "repo-with-ai")
    assert "ai_tools" in repo1
    assert repo1["ai_tools"] == ["Claude", "GitHub Copilot"]

    # Second repo should not have ai_tools field (or it should be empty)
    repo2 = next(r for r in snapshot["repos"] if r["name"] == "repo-without-ai")
    assert repo2.get("ai_tools") is None or repo2.get("ai_tools") == []
