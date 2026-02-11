import json
from pathlib import Path

from tests.factories import create_discovered_repo


def _create_analysis(cache_dir: Path, owner: str, name: str, loc: int = 10000, **extra: object) -> None:
    """Create a minimal analysis file for a repo in the cache."""
    projects_dir = cache_dir / "projects" / owner / name
    projects_dir.mkdir(parents=True)
    analysis = {"owner": owner, "repo": name, "version": "HEAD", "loc": loc, **extra}
    (projects_dir / "HEAD.json").write_text(json.dumps(analysis))


def test_export_discovery_index_creates_structured_output(tmp_path: Path) -> None:
    from iceberg.cache import save_repo_metadata
    from iceberg.export import export_discovery_index

    cache_dir = tmp_path / "cache"
    repos = [
        create_discovered_repo(name="repo1", owner="owner1", source="trending-monthly", stars=1000),
        create_discovered_repo(name="repo2", owner="owner2", source="trending-monthly", stars=2000),
    ]

    for repo in repos:
        save_repo_metadata(repo, repo.source, cache_dir=cache_dir)
        _create_analysis(cache_dir, repo.owner, repo.name)

    output_dir = tmp_path / "export"
    result = export_discovery_index(output_dir, cache_dir=cache_dir)

    assert result["dimensions_exported"] == 1
    assert (output_dir / "index.json").exists()

    index = json.loads((output_dir / "index.json").read_text())
    assert "dimensions" in index
    assert "generated_at" in index
    assert len(index["dimensions"]) == 1

    dimension = index["dimensions"][0]
    assert dimension["id"] == "trending-monthly"
    assert dimension["type"] == "trending"
    assert dimension["timeframe"] == "monthly"
    assert dimension["count"] == 2
    assert len(dimension["repos"]) == 2
    repo_names = {r["name"] for r in dimension["repos"]}
    assert repo_names == {"repo1", "repo2"}
    repo1 = next(r for r in dimension["repos"] if r["name"] == "repo1")
    assert repo1["stars"] == 1000


def test_export_discovery_index_with_multiple_dimensions(tmp_path: Path) -> None:
    from iceberg.cache import save_repo_metadata
    from iceberg.export import export_discovery_index

    cache_dir = tmp_path / "cache"

    monthly_repos = [create_discovered_repo(name="monthly1", owner="m1", source="trending-monthly")]
    ranking_repos = [create_discovered_repo(name="ranking1", owner="r1", source="github-ranking")]
    search_repos = [
        create_discovered_repo(name="search1", owner="s1", source="search", search_query="stars:>10000")
    ]

    for repo in monthly_repos + ranking_repos + search_repos:
        save_repo_metadata(repo, repo.source, cache_dir=cache_dir)
        _create_analysis(cache_dir, repo.owner, repo.name)

    output_dir = tmp_path / "export"
    result = export_discovery_index(output_dir, cache_dir=cache_dir)

    assert result["dimensions_exported"] == 3

    index = json.loads((output_dir / "index.json").read_text())
    dimension_ids = {d["id"] for d in index["dimensions"]}
    assert "trending-monthly" in dimension_ids
    assert "github-ranking" in dimension_ids
    assert "search" in dimension_ids


def test_export_repository_details_creates_per_repo_files(tmp_path: Path) -> None:
    from iceberg.export import export_repository_details

    cache_dir = tmp_path / "cache"
    _create_analysis(
        cache_dir, "facebook", "react", loc=50000,
        source="github_clone", cached_at="2026-02-02T12:00:00Z",
    )

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
    from iceberg.cache import save_repo_metadata
    from iceberg.export import export_all

    cache_dir = tmp_path / "cache"
    repo = create_discovered_repo(name="test", source="trending-monthly")
    save_repo_metadata(repo, repo.source, cache_dir=cache_dir)
    _create_analysis(cache_dir, repo.owner, repo.name, loc=1000)

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
    from iceberg.cache import save_repo_metadata
    from iceberg.export import export_discovery_index

    cache_dir = tmp_path / "cache"
    repos = [
        create_discovered_repo(name="repo-with-ai", owner="owner1", source="trending-monthly", stars=1000),
        create_discovered_repo(name="repo-without-ai", owner="owner2", source="trending-monthly", stars=2000),
    ]

    for repo in repos:
        save_repo_metadata(repo, repo.source, cache_dir=cache_dir)

    _create_analysis(
        cache_dir, "owner1", "repo-with-ai", loc=50000,
        ai_tools=["Claude", "GitHub Copilot"],
        source="github_clone", cached_at="2026-02-02T12:00:00Z",
    )
    _create_analysis(
        cache_dir, "owner2", "repo-without-ai", loc=30000,
        source="github_clone", cached_at="2026-02-02T12:00:00Z",
    )

    output_dir = tmp_path / "export"
    result = export_discovery_index(output_dir, cache_dir=cache_dir)

    index = json.loads((output_dir / "index.json").read_text())
    assert len(index["dimensions"]) == 1

    dimension = index["dimensions"][0]
    repo1 = next(r for r in dimension["repos"] if r["name"] == "repo-with-ai")
    assert "ai_tools" in repo1
    assert repo1["ai_tools"] == ["Claude", "GitHub Copilot"]

    repo2 = next(r for r in dimension["repos"] if r["name"] == "repo-without-ai")
    assert repo2.get("ai_tools") is None or repo2.get("ai_tools") == []


def test_export_skips_repos_without_analysis(tmp_path: Path) -> None:
    """Repos discovered but never analyzed should not appear in the index."""
    from iceberg.cache import save_repo_metadata
    from iceberg.export import export_discovery_index

    cache_dir = tmp_path / "cache"
    analyzed = create_discovered_repo(name="analyzed", owner="a", source="trending-monthly")
    unanalyzed = create_discovered_repo(name="unanalyzed", owner="b", source="trending-monthly")

    for repo in [analyzed, unanalyzed]:
        save_repo_metadata(repo, repo.source, cache_dir=cache_dir)

    _create_analysis(cache_dir, "a", "analyzed", loc=5000)

    output_dir = tmp_path / "export"
    export_discovery_index(output_dir, cache_dir=cache_dir)

    index = json.loads((output_dir / "index.json").read_text())
    dimension = index["dimensions"][0]
    repo_names = [r["name"] for r in dimension["repos"]]
    assert "analyzed" in repo_names
    assert "unanalyzed" not in repo_names


def test_export_skips_repos_with_zero_loc(tmp_path: Path) -> None:
    """Repos with loc=0 (documentation-only) should not appear in the index."""
    from iceberg.cache import save_repo_metadata
    from iceberg.export import export_discovery_index

    cache_dir = tmp_path / "cache"
    real_repo = create_discovered_repo(name="real", owner="a", source="trending-monthly")
    doc_repo = create_discovered_repo(name="docs", owner="b", source="trending-monthly")

    for repo in [real_repo, doc_repo]:
        save_repo_metadata(repo, repo.source, cache_dir=cache_dir)

    _create_analysis(cache_dir, "a", "real", loc=5000)
    _create_analysis(cache_dir, "b", "docs", loc=0)

    output_dir = tmp_path / "export"
    export_discovery_index(output_dir, cache_dir=cache_dir)

    index = json.loads((output_dir / "index.json").read_text())
    dimension = index["dimensions"][0]
    repo_names = [r["name"] for r in dimension["repos"]]
    assert "real" in repo_names
    assert "docs" not in repo_names
