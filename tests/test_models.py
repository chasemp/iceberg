import pytest
from pydantic import ValidationError


def test_trending_repo_validates_with_valid_data() -> None:
    from iceberg.models import TrendingRepo

    repo = TrendingRepo(
        name="example",
        owner="owner",
        url="https://github.com/owner/example",
        description="A test repo",
        language="Python",
        stars=100,
        source="trending-monthly",
        discovered_at="2026-02-02T12:00:00Z",
    )

    assert repo.name == "example"
    assert repo.owner == "owner"
    assert repo.stars == 100


def test_trending_repo_is_frozen() -> None:
    from iceberg.models import TrendingRepo

    repo = TrendingRepo(
        name="example",
        owner="owner",
        url="https://github.com/owner/example",
        description="A test repo",
        language="Python",
        stars=100,
        source="trending-monthly",
        discovered_at="2026-02-02T12:00:00Z",
    )

    with pytest.raises(ValidationError):
        repo.stars = 200  # type: ignore[misc]


def test_trending_repo_allows_none_for_optional_fields() -> None:
    from iceberg.models import TrendingRepo

    repo = TrendingRepo(
        name="example",
        owner="owner",
        url="https://github.com/owner/example",
        description=None,
        language=None,
        stars=0,
        source="trending-monthly",
        discovered_at="2026-02-02T12:00:00Z",
    )

    assert repo.description is None
    assert repo.language is None


def test_package_identifier_validates_with_valid_data() -> None:
    from iceberg.models import PackageIdentifier

    pkg = PackageIdentifier(
        system="npm",
        name="react",
        version="18.2.0",
    )

    assert pkg.system == "npm"
    assert pkg.name == "react"
    assert pkg.version == "18.2.0"


def test_package_identifier_is_frozen() -> None:
    from iceberg.models import PackageIdentifier

    pkg = PackageIdentifier(
        system="pypi",
        name="requests",
        version="2.31.0",
    )

    with pytest.raises(ValidationError):
        pkg.version = "2.32.0"  # type: ignore[misc]


def test_package_identifier_rejects_invalid_system() -> None:
    from iceberg.models import PackageIdentifier

    with pytest.raises(ValidationError):
        PackageIdentifier(
            system="invalid",  # type: ignore[arg-type]
            name="test",
            version="1.0.0",
        )


def test_loc_metrics_validates_with_valid_data() -> None:
    from iceberg.models import LocMetrics, PackageIdentifier

    pkg = PackageIdentifier(
        system="npm",
        name="react",
        version="18.2.0",
    )

    metrics = LocMetrics(
        package=pkg,
        total_lines=10000,
        source="depsdev",
        cached_at="2026-01-30T12:00:00Z",
    )

    assert metrics.total_lines == 10000
    assert metrics.source == "depsdev"


def test_loc_metrics_is_frozen() -> None:
    from iceberg.models import LocMetrics, PackageIdentifier

    pkg = PackageIdentifier(
        system="npm",
        name="react",
        version="18.2.0",
    )

    metrics = LocMetrics(
        package=pkg,
        total_lines=10000,
        source="depsdev",
        cached_at="2026-01-30T12:00:00Z",
    )

    with pytest.raises(ValidationError):
        metrics.total_lines = 20000  # type: ignore[misc]


def test_loc_metrics_rejects_invalid_source() -> None:
    from iceberg.models import LocMetrics, PackageIdentifier

    pkg = PackageIdentifier(
        system="npm",
        name="react",
        version="18.2.0",
    )

    with pytest.raises(ValidationError):
        LocMetrics(
            package=pkg,
            total_lines=10000,
            source="invalid",  # type: ignore[arg-type]
            cached_at="2026-01-30T12:00:00Z",
        )


def test_loc_metrics_includes_timing_data() -> None:
    from iceberg.models import LocMetrics, PackageIdentifier

    pkg = PackageIdentifier(
        system="npm",
        name="react",
        version="18.2.0",
    )

    metrics = LocMetrics(
        package=pkg,
        total_lines=10000,
        source="github_clone",
        cached_at="2026-02-02T12:00:00Z",
        source_url="https://github.com/facebook/react",
        fetch_method="git_clone_and_count",
        fetch_duration_seconds=2.45,
        count_duration_seconds=1.23,
    )

    assert metrics.fetch_duration_seconds == 2.45
    assert metrics.count_duration_seconds == 1.23


def test_discovered_repo_validates_with_source_field() -> None:
    from iceberg.models import DiscoveredRepo

    repo = DiscoveredRepo(
        name="example",
        owner="owner",
        url="https://github.com/owner/example",
        description="A test repo",
        language="Python",
        stars=100,
        source="trending-monthly",
        discovered_at="2026-02-02T12:00:00Z",
    )

    assert repo.name == "example"
    assert repo.source == "trending-monthly"
    assert repo.discovered_at == "2026-02-02T12:00:00Z"


def test_discovered_repo_with_search_query() -> None:
    from iceberg.models import DiscoveredRepo

    repo = DiscoveredRepo(
        name="react",
        owner="facebook",
        url="https://github.com/facebook/react",
        description="A JavaScript library",
        language="JavaScript",
        stars=220000,
        source="search",
        discovered_at="2026-02-02T12:00:00Z",
        search_query="stars:>10000 language:JavaScript",
    )

    assert repo.source == "search"
    assert repo.search_query == "stars:>10000 language:JavaScript"


def test_trending_repo_alias_works() -> None:
    from iceberg.models import TrendingRepo

    repo = TrendingRepo(
        name="example",
        owner="owner",
        url="https://github.com/owner/example",
        description="A test repo",
        language="Python",
        stars=100,
        source="trending-monthly",
        discovered_at="2026-02-02T12:00:00Z",
    )

    assert repo.name == "example"
    assert repo.source == "trending-monthly"


def test_discovered_repo_is_frozen() -> None:
    from iceberg.models import DiscoveredRepo

    repo = DiscoveredRepo(
        name="example",
        owner="owner",
        url="https://github.com/owner/example",
        description="A test repo",
        language="Python",
        stars=100,
        source="trending-monthly",
        discovered_at="2026-02-02T12:00:00Z",
    )

    with pytest.raises(ValidationError):
        repo.stars = 200  # type: ignore[misc]


def test_create_discovered_repo_factory() -> None:
    from tests.factories import create_discovered_repo

    repo = create_discovered_repo(
        name="test",
        source="search",
        search_query="stars:>1000",
    )

    assert repo.name == "test"
    assert repo.source == "search"
    assert repo.search_query == "stars:>1000"


def test_create_trending_repo_factory_backward_compatible() -> None:
    from tests.factories import create_trending_repo

    repo = create_trending_repo(name="test")

    assert repo.name == "test"
    assert repo.source == "trending-monthly"
    assert repo.discovered_at == "2026-02-02T12:00:00Z"


def test_repository_metadata_validates_with_valid_data() -> None:
    """Test RepositoryMetadata validates with complete data."""
    from iceberg.models import RepositoryMetadata

    metadata = RepositoryMetadata(
        name="react",
        owner="facebook",
        url="https://github.com/facebook/react",
        description="A JavaScript library for building user interfaces",
        language="JavaScript",
        stars=220000,
        categories={"trending-monthly": "2026-02-09", "github-ranking": "2026-02-10"},
        last_discovered="2026-02-10",
    )

    assert metadata.name == "react"
    assert metadata.owner == "facebook"
    assert metadata.stars == 220000
    assert "trending-monthly" in metadata.categories
    assert metadata.last_discovered == "2026-02-10"


def test_repository_metadata_allows_none_for_optional_fields() -> None:
    """Test RepositoryMetadata accepts None for description and language."""
    from iceberg.models import RepositoryMetadata

    metadata = RepositoryMetadata(
        name="test",
        owner="owner",
        url="https://github.com/owner/test",
        description=None,
        language=None,
        stars=100,
        categories={"search": "2026-02-09"},
        last_discovered="2026-02-09",
    )

    assert metadata.description is None
    assert metadata.language is None


def test_repository_metadata_is_frozen() -> None:
    """Test RepositoryMetadata is immutable."""
    from iceberg.models import RepositoryMetadata

    metadata = RepositoryMetadata(
        name="react",
        owner="facebook",
        url="https://github.com/facebook/react",
        description="A JavaScript library",
        language="JavaScript",
        stars=220000,
        categories={"trending-monthly": "2026-02-09"},
        last_discovered="2026-02-09",
    )

    with pytest.raises(ValidationError):
        metadata.stars = 300000  # type: ignore[misc]


def test_repository_metadata_requires_all_mandatory_fields() -> None:
    """Test RepositoryMetadata rejects missing required fields."""
    from iceberg.models import RepositoryMetadata

    with pytest.raises(ValidationError):
        RepositoryMetadata(  # type: ignore[call-arg]
            name="react",
            owner="facebook",
            # missing url, stars, categories, last_discovered
        )


def test_repository_metadata_with_empty_categories() -> None:
    """Test RepositoryMetadata accepts empty categories dict."""
    from iceberg.models import RepositoryMetadata

    metadata = RepositoryMetadata(
        name="test",
        owner="owner",
        url="https://github.com/owner/test",
        description="Test repo",
        language="Python",
        stars=50,
        categories={},
        last_discovered="2026-02-09",
    )

    assert metadata.categories == {}


def test_repository_metadata_validates_url_format() -> None:
    """Test RepositoryMetadata validates HttpUrl format."""
    from iceberg.models import RepositoryMetadata

    with pytest.raises(ValidationError):
        RepositoryMetadata(
            name="test",
            owner="owner",
            url="not-a-valid-url",  # type: ignore[arg-type]
            description="Test",
            language="Python",
            stars=100,
            categories={"search": "2026-02-09"},
            last_discovered="2026-02-09",
        )
