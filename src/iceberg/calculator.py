import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from iceberg.ai_markers import detect_ai_markers, get_ai_tools_list, has_any_ai_markers
from iceberg.cache import (
    load_dependencies,
    load_loc_metrics,
    load_project_loc,
    save_dependencies,
    save_loc_metrics,
    save_project_loc,
)
from iceberg.detector import detect_package
from iceberg.depsdev import get_dependencies, get_package_loc, get_project_loc as get_depsdev_project_loc
from iceberg.github_loc import get_github_project_loc
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


def analyze_repository(
    owner: str,
    repo: str,
    package_spec: str | None = None,
    cache_dir: Path | None = None,
    verbose: bool = False,
) -> dict[str, Any] | None:
    """Analyze a repository and calculate its iceberg ratio.

    Supports partial analysis:
    - If deps.dev doesn't have the project, falls back to GitHub cloning
    - If package detection fails, saves project LoC anyway
    - If dependency analysis fails, saves partial results

    Args:
        owner: Repository owner
        repo: Repository name
        package_spec: Optional package spec (system:name:version), auto-detect if None
        cache_dir: Cache directory
        verbose: If True, log fallback attempts and reasons

    Returns:
        Dict with analysis results or None if project LoC can't be determined
    """
    # Check if already analyzed (using HEAD as default version)
    cached = load_project_loc(owner, repo, "HEAD", cache_dir=cache_dir)
    if cached:
        if verbose:
            print(f"    [cache] Using cached analysis for {owner}/{repo}")
        return cached

    # Step 1: Get project LoC (try deps.dev first, then GitHub clone)
    project_loc: int | None = None
    project_source = "unknown"
    project_metadata: dict[str, Any] = {}

    # Try deps.dev API first
    try:
        if verbose:
            print(f"    [deps.dev] Fetching project LoC for {owner}/{repo}")
        project_loc = get_depsdev_project_loc(owner, repo)
        if project_loc is not None:
            project_source = "depsdev_api"
            if verbose:
                print(f"    [deps.dev] ✓ Got {project_loc:,} LoC from deps.dev")
    except Exception as e:
        # deps.dev failed (404, network error, etc.), try GitHub clone
        if verbose:
            print(f"    [deps.dev] ✗ Failed ({e.__class__.__name__}), falling back to GitHub clone")

    # Fallback to GitHub cloning if deps.dev didn't work
    if project_loc is None:
        if verbose:
            print(f"    [github] Cloning and counting LoC for {owner}/{repo}")
        github_result = get_github_project_loc(owner, repo, cache_dir=cache_dir)
        if github_result:
            project_loc = github_result["loc"]
            project_source = github_result["source"]
            project_metadata = github_result.get("metadata", {})
            if verbose:
                print(f"    [github] ✓ Cloned and counted {project_loc:,} LoC")
        elif verbose:
            print(f"    [github] ✗ Clone failed")

    # If we can't get project LoC at all, give up
    if project_loc is None:
        return None

    # Step 2: Detect AI markers
    if verbose:
        print(f"    [ai] Detecting AI tool markers")
    try:
        ai_markers = detect_ai_markers(owner, repo)
        if has_any_ai_markers(ai_markers):
            tools = get_ai_tools_list(ai_markers)
            if verbose:
                print(f"    [ai] ✓ Detected AI tools: {', '.join(tools)}")
        elif verbose:
            print(f"    [ai] ✗ No AI tool markers found")
    except Exception:
        # AI detection failed, not critical
        ai_markers = {}
        if verbose:
            print(f"    [ai] ✗ Detection failed (continuing without AI markers)")

    # Step 3: Detect or parse package
    pkg: PackageIdentifier | None = None
    if package_spec:
        if verbose:
            print(f"    [package] Using provided spec: {package_spec}")
        parts = package_spec.split(":")
        if len(parts) == 3:
            system = parts[0]
            if system in ("npm", "pypi", "cargo", "maven", "go"):
                pkg = PackageIdentifier(system=system, name=parts[1], version=parts[2])  # type: ignore[arg-type]
    else:
        if verbose:
            print(f"    [package] Auto-detecting package manifest")
        pkg = detect_package(owner, repo)
        if pkg and verbose:
            print(f"    [package] ✓ Detected {pkg.system}:{pkg.name}@{pkg.version}")
        elif verbose:
            print(f"    [package] ✗ No package manifest found")

    # Step 4: Try to calculate dependencies (optional)
    total_loc: int | None = None
    ratio: float | None = None

    if pkg is not None:
        try:
            if verbose:
                print(f"    [deps] Calculating transitive dependencies for {pkg.system}:{pkg.name}")
            total_loc = calculate_transitive_loc(pkg, cache_dir=cache_dir)
            ratio = total_loc / (project_loc + total_loc) if (project_loc + total_loc) > 0 else 0.0
            if verbose:
                print(f"    [deps] ✓ Total dependencies: {total_loc:,} LoC (ratio: {ratio:.1%})")
        except Exception as e:
            # Dependency analysis failed, but we still have project LoC
            if verbose:
                print(f"    [deps] ✗ Dependency analysis failed ({e.__class__.__name__})")

    # Step 5: Save what we have (even if partial)
    project_data: dict[str, Any] = {
        "owner": owner,
        "repo": repo,
        "version": "HEAD",
        "loc": project_loc,
        "source": project_source,
        "cached_at": datetime.now(timezone.utc).isoformat(),
    }

    # Add optional fields if available
    if pkg is not None:
        project_data["package"] = pkg.model_dump(mode="json")
    if total_loc is not None:
        project_data["total_loc"] = total_loc
    if ratio is not None:
        project_data["ratio"] = ratio
    if ai_markers and has_any_ai_markers(ai_markers):
        project_data["ai_markers"] = ai_markers
        project_data["ai_tools"] = get_ai_tools_list(ai_markers)
    if project_metadata:
        project_data.update(project_metadata)

    save_project_loc(project_data, cache_dir=cache_dir)

    # Return result
    result: dict[str, Any] = {
        "owner": owner,
        "repo": repo,
        "project_loc": project_loc,
    }

    if pkg is not None:
        result["package"] = f"{pkg.system}:{pkg.name}:{pkg.version}"
    if total_loc is not None:
        result["total_loc"] = total_loc
    if ratio is not None:
        result["ratio"] = ratio

    return result
