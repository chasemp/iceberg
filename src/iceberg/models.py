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
    source: str  # Source identifier (e.g., "trending-daily", "search", "github-ranking-python")
    discovered_at: str
    search_query: str | None = None


TrendingRepo = DiscoveredRepo


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
