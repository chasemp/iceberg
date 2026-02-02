import time
from datetime import datetime, timezone
from pathlib import Path

from iceberg.cache import (
    load_dependencies,
    load_loc_metrics,
    save_dependencies,
    save_loc_metrics,
)
from iceberg.depsdev import get_dependencies, get_package_loc
from iceberg.models import LocMetrics, PackageIdentifier
from iceberg.npm_loc import get_npm_package_loc


def calculate_package_loc(
    pkg: PackageIdentifier,
    cache_dir: Path | None = None,
) -> int:
    cached_metrics = load_loc_metrics(pkg, cache_dir=cache_dir)
    if cached_metrics is not None:
        return cached_metrics.total_lines

    # Try deps.dev first
    fetch_start = time.time()
    loc = get_package_loc(pkg)
    fetch_duration = time.time() - fetch_start

    source = "depsdev"
    source_url = f"https://api.deps.dev/v3/systems/{pkg.system}/packages/{pkg.name}/versions/{pkg.version}"
    fetch_method = "api_call"
    count_duration: float | None = None

    # If deps.dev doesn't have data, try package-specific fallbacks
    if loc is None or loc == 0:
        if pkg.system == "npm":
            npm_start = time.time()
            npm_result = get_npm_package_loc(pkg.name, pkg.version, cache_dir=cache_dir)
            npm_duration = time.time() - npm_start

            if npm_result:
                loc = npm_result["loc"]
                source = "npm_tarball"
                source_url = npm_result["metadata"]["tarball_url"]
                fetch_method = "tarball_download_and_count"
                fetch_duration = npm_duration
                # For npm tarball, we don't separate fetch and count since it's done internally
                count_duration = None

    if loc is None:
        loc = 0

    metrics = LocMetrics(
        package=pkg,
        total_lines=loc,
        source=source,  # type: ignore[arg-type]
        cached_at=datetime.now(timezone.utc).isoformat(),
        source_url=source_url,
        fetch_method=fetch_method,
        fetch_duration_seconds=fetch_duration,
        count_duration_seconds=count_duration,
    )
    save_loc_metrics(metrics, cache_dir=cache_dir)

    return loc


def calculate_transitive_loc(
    root: PackageIdentifier,
    cache_dir: Path | None = None,
) -> int:
    visited: set[PackageIdentifier] = set()
    total = 0
    queue: list[PackageIdentifier] = [root]

    while queue:
        pkg = queue.pop(0)

        if pkg in visited:
            continue

        visited.add(pkg)

        loc = calculate_package_loc(pkg, cache_dir=cache_dir)
        total += loc

        cached_deps = load_dependencies(pkg, cache_dir=cache_dir)
        if cached_deps is not None:
            deps = cached_deps
        else:
            deps = get_dependencies(pkg)
            save_dependencies(pkg, deps, cache_dir=cache_dir)

        queue.extend(deps)

    return total
