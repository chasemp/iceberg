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
        source="trending-daily",
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
        source="trending-daily",
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
        source="trending-daily",
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
        source="trending-daily",
        discovered_at="2026-02-02T12:00:00Z",
    )

    assert repo.name == "example"
    assert repo.source == "trending-daily"
    assert repo.discovered_at == "2026-02-02T12:00:00Z"


def test_discovered_repo_rejects_invalid_source() -> None:
    from iceberg.models import DiscoveredRepo

    with pytest.raises(ValidationError):
        DiscoveredRepo(
            name="example",
            owner="owner",
            url="https://github.com/owner/example",
            description="A test repo",
            language="Python",
            stars=100,
            source="invalid-source",  # type: ignore[arg-type]
            discovered_at="2026-02-02T12:00:00Z",
        )


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
        source="trending-daily",
        discovered_at="2026-02-02T12:00:00Z",
    )

    assert repo.name == "example"
    assert repo.source == "trending-daily"


def test_discovered_repo_is_frozen() -> None:
    from iceberg.models import DiscoveredRepo

    repo = DiscoveredRepo(
        name="example",
        owner="owner",
        url="https://github.com/owner/example",
        description="A test repo",
        language="Python",
        stars=100,
        source="trending-daily",
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
    assert repo.source == "trending-daily"
    assert repo.discovered_at == "2026-02-02T12:00:00Z"
