"""Tests for RepositoryStore abstraction."""

from pathlib import Path


def test_repository_store_saves_and_loads_repository(tmp_path: Path) -> None:
    """Test saving and loading a repository."""
    from iceberg.models import RepositoryMetadata
    from iceberg.repository_store import RepositoryStore

    store = RepositoryStore(cache_dir=tmp_path)

    metadata = RepositoryMetadata(
        name="react",
        owner="facebook",
        url="https://github.com/facebook/react",
        description="A JavaScript library",
        language="JavaScript",
        stars=200000,
        categories={"trending-monthly": "2026-02-09"},
        last_discovered="2026-02-09",
    )

    store.save(metadata)

    loaded = store.load("facebook", "react")

    assert loaded is not None
    assert loaded.name == "react"
    assert loaded.owner == "facebook"
    assert loaded.stars == 200000


def test_repository_store_load_returns_none_when_not_found(tmp_path: Path) -> None:
    """Test loading non-existent repository returns None."""
    from iceberg.repository_store import RepositoryStore

    store = RepositoryStore(cache_dir=tmp_path)

    result = store.load("nonexistent", "repo")

    assert result is None


def test_repository_store_exists_returns_true_when_found(tmp_path: Path) -> None:
    """Test exists returns True for existing repository."""
    from iceberg.models import RepositoryMetadata
    from iceberg.repository_store import RepositoryStore

    store = RepositoryStore(cache_dir=tmp_path)

    metadata = RepositoryMetadata(
        name="test",
        owner="owner",
        url="https://github.com/owner/test",
        description="Test repo",
        language="Python",
        stars=100,
        categories={"search": "2026-02-09"},
        last_discovered="2026-02-09",
    )

    store.save(metadata)

    assert store.exists("owner", "test") is True


def test_repository_store_exists_returns_false_when_not_found(tmp_path: Path) -> None:
    """Test exists returns False for non-existent repository."""
    from iceberg.repository_store import RepositoryStore

    store = RepositoryStore(cache_dir=tmp_path)

    assert store.exists("nonexistent", "repo") is False


def test_repository_store_list_all_returns_all_repos(tmp_path: Path) -> None:
    """Test listing all repositories."""
    from iceberg.models import RepositoryMetadata
    from iceberg.repository_store import RepositoryStore

    store = RepositoryStore(cache_dir=tmp_path)

    repos = [
        RepositoryMetadata(
            name="repo1",
            owner="owner1",
            url="https://github.com/owner1/repo1",
            description="First",
            language="Python",
            stars=100,
            categories={"search": "2026-02-09"},
            last_discovered="2026-02-09",
        ),
        RepositoryMetadata(
            name="repo2",
            owner="owner2",
            url="https://github.com/owner2/repo2",
            description="Second",
            language="JavaScript",
            stars=200,
            categories={"trending-monthly": "2026-02-09"},
            last_discovered="2026-02-09",
        ),
    ]

    for repo in repos:
        store.save(repo)

    all_repos = store.list_all()

    assert len(all_repos) == 2
    names = {r.name for r in all_repos}
    assert names == {"repo1", "repo2"}


def test_repository_store_get_by_category_filters_correctly(tmp_path: Path) -> None:
    """Test getting repositories by category."""
    from iceberg.models import RepositoryMetadata
    from iceberg.repository_store import RepositoryStore

    store = RepositoryStore(cache_dir=tmp_path)

    repos = [
        RepositoryMetadata(
            name="trending-repo",
            owner="owner1",
            url="https://github.com/owner1/trending-repo",
            description="Trending",
            language="Python",
            stars=1000,
            categories={"trending-monthly": "2026-02-09"},
            last_discovered="2026-02-09",
        ),
        RepositoryMetadata(
            name="search-repo",
            owner="owner2",
            url="https://github.com/owner2/search-repo",
            description="Search",
            language="JavaScript",
            stars=500,
            categories={"search": "2026-02-09"},
            last_discovered="2026-02-09",
        ),
        RepositoryMetadata(
            name="both-repo",
            owner="owner3",
            url="https://github.com/owner3/both-repo",
            description="Both",
            language="Go",
            stars=750,
            categories={"trending-monthly": "2026-02-09", "search": "2026-02-10"},
            last_discovered="2026-02-10",
        ),
    ]

    for repo in repos:
        store.save(repo)

    trending = store.get_by_category("trending-monthly")

    assert len(trending) == 2
    names = {r.name for r in trending}
    assert names == {"trending-repo", "both-repo"}


def test_repository_store_updates_existing_repository(tmp_path: Path) -> None:
    """Test updating an existing repository preserves and merges categories."""
    from iceberg.models import RepositoryMetadata
    from iceberg.repository_store import RepositoryStore

    store = RepositoryStore(cache_dir=tmp_path)

    initial = RepositoryMetadata(
        name="test",
        owner="owner",
        url="https://github.com/owner/test",
        description="Initial",
        language="Python",
        stars=100,
        categories={"search": "2026-02-09"},
        last_discovered="2026-02-09",
    )

    store.save(initial)

    updated = RepositoryMetadata(
        name="test",
        owner="owner",
        url="https://github.com/owner/test",
        description="Updated",
        language="Python",
        stars=150,
        categories={"search": "2026-02-09", "trending-monthly": "2026-02-10"},
        last_discovered="2026-02-10",
    )

    store.save(updated)

    loaded = store.load("owner", "test")

    assert loaded is not None
    assert loaded.stars == 150
    assert "search" in loaded.categories
    assert "trending-monthly" in loaded.categories


def test_repository_store_uses_default_cache_dir_when_not_specified() -> None:
    """Test RepositoryStore uses default cache directory."""
    from iceberg.repository_store import RepositoryStore

    store = RepositoryStore()

    assert store.cache_dir is not None
    assert store.cache_dir.name == "cache"
