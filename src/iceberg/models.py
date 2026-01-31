from typing import Literal

from pydantic import BaseModel, ConfigDict, HttpUrl


class TrendingRepo(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    owner: str
    url: HttpUrl
    description: str | None
    language: str | None
    stars: int


class PackageIdentifier(BaseModel):
    model_config = ConfigDict(frozen=True)

    system: Literal["npm", "pypi", "cargo", "maven"]
    name: str
    version: str


class LocMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)

    package: PackageIdentifier
    total_lines: int
    source: Literal["depsdev", "github"]
    cached_at: str
