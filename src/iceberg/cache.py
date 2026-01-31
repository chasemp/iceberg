import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from iceberg.models import LocMetrics, PackageIdentifier, TrendingRepo


def get_default_cache_dir() -> Path:
    return Path(__file__).parent.parent.parent / "cache"


def save_trending_repos(
    repos: list[TrendingRepo],
    cache_dir: Path | None = None,
) -> None:
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    trending_dir = cache_dir / "trending"
    trending_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now(timezone.utc).date().isoformat()
    cache_file = trending_dir / f"{today}.json"

    data = [repo.model_dump(mode="json") for repo in repos]

    cache_file.write_text(json.dumps(data, indent=2))


def load_trending_repos(
    cache_dir: Path | None = None,
) -> list[TrendingRepo] | None:
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    trending_dir = cache_dir / "trending"
    today = datetime.now(timezone.utc).date().isoformat()
    cache_file = trending_dir / f"{today}.json"

    if not cache_file.exists():
        return None

    data = json.loads(cache_file.read_text())
    return [TrendingRepo.model_validate(item) for item in data]


def save_loc_metrics(
    metrics: LocMetrics,
    cache_dir: Path | None = None,
) -> None:
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    pkg = metrics.package
    loc_dir = cache_dir / "loc" / pkg.system / pkg.name
    loc_dir.mkdir(parents=True, exist_ok=True)

    cache_file = loc_dir / f"{pkg.version}.json"

    data = metrics.model_dump(mode="json")
    cache_file.write_text(json.dumps(data, indent=2))


def load_loc_metrics(
    pkg: PackageIdentifier,
    cache_dir: Path | None = None,
) -> LocMetrics | None:
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    cache_file = cache_dir / "loc" / pkg.system / pkg.name / f"{pkg.version}.json"

    if not cache_file.exists():
        return None

    data = json.loads(cache_file.read_text())
    return LocMetrics.model_validate(data)


def save_dependencies(
    pkg: PackageIdentifier,
    deps: list[PackageIdentifier],
    cache_dir: Path | None = None,
) -> None:
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    deps_dir = cache_dir / "dependencies" / pkg.system / pkg.name
    deps_dir.mkdir(parents=True, exist_ok=True)

    cache_file = deps_dir / f"{pkg.version}.json"

    data = [dep.model_dump(mode="json") for dep in deps]
    cache_file.write_text(json.dumps(data, indent=2))


def load_dependencies(
    pkg: PackageIdentifier,
    cache_dir: Path | None = None,
) -> list[PackageIdentifier] | None:
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    cache_file = cache_dir / "dependencies" / pkg.system / pkg.name / f"{pkg.version}.json"

    if not cache_file.exists():
        return None

    data = json.loads(cache_file.read_text())
    return [PackageIdentifier.model_validate(item) for item in data]


def is_cache_fresh(
    cache_dir: Path | None = None,
    max_age_days: int = 7,
) -> bool:
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    trending_dir = cache_dir / "trending"
    today = datetime.now(timezone.utc).date().isoformat()
    cache_file = trending_dir / f"{today}.json"

    if not cache_file.exists():
        return False

    file_date_str = cache_file.stem
    file_date = datetime.fromisoformat(file_date_str).replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)

    age = now - file_date
    return age <= timedelta(days=max_age_days)
