from iceberg.models import DiscoveredRepo, LocMetrics, PackageIdentifier, TrendingRepo


def create_discovered_repo(
    name: str = "example",
    owner: str = "owner",
    url: str = "https://github.com/owner/example",
    description: str | None = "A test repo",
    language: str | None = "Python",
    stars: int = 100,
    source: str = "trending-monthly",
    discovered_at: str = "2026-02-02T12:00:00Z",
    search_query: str | None = None,
) -> DiscoveredRepo:
    return DiscoveredRepo(
        name=name,
        owner=owner,
        url=url,
        description=description,
        language=language,
        stars=stars,
        source=source,  # type: ignore[arg-type]
        discovered_at=discovered_at,
        search_query=search_query,
    )


def create_trending_repo(
    name: str = "example",
    owner: str = "owner",
    url: str = "https://github.com/owner/example",
    description: str | None = "A test repo",
    language: str | None = "Python",
    stars: int = 100,
) -> TrendingRepo:
    return create_discovered_repo(
        name=name,
        owner=owner,
        url=url,
        description=description,
        language=language,
        stars=stars,
        source="trending-monthly",
        discovered_at="2026-02-02T12:00:00Z",
    )


def create_package_identifier(
    system: str = "npm",
    name: str = "react",
    version: str = "18.2.0",
) -> PackageIdentifier:
    return PackageIdentifier(
        system=system,  # type: ignore[arg-type]
        name=name,
        version=version,
    )


def create_loc_metrics(
    package: PackageIdentifier | None = None,
    total_lines: int = 10000,
    source: str = "depsdev",
    cached_at: str = "2026-01-30T12:00:00Z",
) -> LocMetrics:
    if package is None:
        package = create_package_identifier()

    return LocMetrics(
        package=package,
        total_lines=total_lines,
        source=source,  # type: ignore[arg-type]
        cached_at=cached_at,
    )
