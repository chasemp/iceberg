from typing import Literal

from pydantic import BaseModel, ConfigDict, HttpUrl


class DiscoveredRepo(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    owner: str
    url: HttpUrl
    description: str | None
    language: str | None
    stars: int
    source: str  # Source identifier (e.g., "trending-monthly", "search", "github-ranking-python")
    discovered_at: str
    search_query: str | None = None


TrendingRepo = DiscoveredRepo


class RepositoryMetadata(BaseModel):
    """Repository metadata aggregated across multiple discovery events.

    This represents the cached metadata structure that tracks a repository
    across multiple categories and discovery dates.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    owner: str
    url: HttpUrl
    description: str | None
    language: str | None
    stars: int
    categories: dict[str, str]  # Maps category -> date discovered
    last_discovered: str


class PackageIdentifier(BaseModel):
    model_config = ConfigDict(frozen=True)

    system: Literal["npm", "pypi", "cargo", "maven", "go"]
    name: str
    version: str


class LocMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)

    package: PackageIdentifier
    total_lines: int
    source: Literal[
        "depsdev",
        "github",
        "github_clone",
        "npm_tarball",
        "pypi_package",
        "cargo_crate",
    ]
    cached_at: str
    source_url: str | None = None
    fetch_method: str | None = None
    fetch_duration_seconds: float | None = None
    count_duration_seconds: float | None = None
