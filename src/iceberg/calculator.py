import tempfile
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
from iceberg.github_loc import clone_repository, count_repo_loc, get_github_project_loc
from iceberg.models import LocMetrics, PackageIdentifier
from iceberg.npm_loc import get_npm_package_loc
from iceberg.osv import parse_osv_sbom, run_osv_scanner


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
    force: bool = False,
) -> dict[str, Any] | None:
    """Analyze a repository and calculate its iceberg ratio.

    New flow (osv-scanner primary):
    - Clone GitHub repo and count project LoC
    - Run osv-scanner to discover dependencies from lock files
    - Calculate transitive LoC from SBOM dependencies
    - Use deps.dev as fallback for individual package LoC queries

    Args:
        owner: Repository owner
        repo: Repository name
        package_spec: Optional package spec (system:name:version), auto-detect if None
        cache_dir: Cache directory
        verbose: If True, log fallback attempts and reasons
        force: If True, skip cache and re-analyze from scratch

    Returns:
        Dict with analysis results or None if project LoC can't be determined
    """
    # Check if already analyzed (using HEAD as default version)
    if not force:
        cached = load_project_loc(owner, repo, "HEAD", cache_dir=cache_dir)
        if cached:
            if verbose:
                print(f"    [cache] Using cached analysis for {owner}/{repo}")
            return cached

    # Step 1: Try to detect package version before cloning (for release tag checkout)
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
            print(f"    [package] Pre-detecting package for release tag")
        try:
            pkg = detect_package(owner, repo)
            if pkg and verbose:
                print(f"    [package] ✓ Detected {pkg.system}:{pkg.name}@{pkg.version}")
        except Exception:
            if verbose:
                print(f"    [package] ✗ Pre-detection failed, will clone HEAD")

    # Step 2: Clone repo and count project LoC
    project_loc: int | None = None
    project_source = "unknown"
    project_metadata: dict[str, Any] = {}
    repo_path: Path | None = None
    ref_to_clone: str | None = None

    # If we detected a version, try to clone that release tag
    if pkg and pkg.version:
        # Try common tag formats: v1.2.3, 1.2.3
        for tag_format in [f"v{pkg.version}", pkg.version]:
            if verbose:
                print(f"    [github] Attempting to clone tag {tag_format}")
            ref_to_clone = tag_format
            break  # Use first format for now

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            if verbose:
                if ref_to_clone:
                    print(f"    [github] Cloning {owner}/{repo} at {ref_to_clone}")
                else:
                    print(f"    [github] Cloning {owner}/{repo} at HEAD")

            # Clone repository (with version tag if detected, otherwise HEAD)
            clone_result = clone_repository(owner, repo, target_dir=temp_path, ref=ref_to_clone)
            if not clone_result:
                # If clone with tag failed, try HEAD as fallback
                if ref_to_clone:
                    if verbose:
                        print(f"    [github] ✗ Clone with tag {ref_to_clone} failed, trying HEAD")
                    clone_result = clone_repository(owner, repo, target_dir=temp_path, ref=None)
                    if not clone_result:
                        if verbose:
                            print(f"    [github] ✗ Clone failed")
                        return None
                else:
                    if verbose:
                        print(f"    [github] ✗ Clone failed")
                    return None

            repo_path = temp_path

            # Count LoC
            if verbose:
                print(f"    [github] Counting LoC")
            count_result = count_repo_loc(temp_path)
            if not count_result:
                if verbose:
                    print(f"    [github] ✗ LoC counting failed")
                return None

            project_loc = count_result["loc"]
            project_source = "github_clone"
            project_metadata = {
                "repo_url": clone_result["repo_url"],
                "ref": clone_result["ref"],
                "commit_hash": clone_result.get("commit_hash"),
                "clone_duration_seconds": clone_result["duration_seconds"],
                "count_duration_seconds": count_result["duration_seconds"],
            }

            if verbose:
                print(f"    [github] ✓ Cloned and counted {project_loc:,} LoC")

            # Step 2: Run osv-scanner to discover dependencies
            total_loc: int | None = None
            ratio: float | None = None

            if verbose:
                print(f"    [osv] Running osv-scanner to discover dependencies")

            osv_output = run_osv_scanner(temp_path)
            if osv_output:
                deps = parse_osv_sbom(osv_output)
                if deps:
                    if verbose:
                        print(f"    [osv] ✓ Discovered {len(deps)} dependencies")

                    # Calculate LoC for each dependency
                    dep_loc_sum = 0
                    for dep in deps:
                        try:
                            dep_loc = calculate_package_loc(dep, cache_dir=cache_dir)
                            dep_loc_sum += dep_loc
                        except Exception:
                            # Individual dependency calculation failed, continue with others
                            continue

                    total_loc = dep_loc_sum
                    ratio = total_loc / (project_loc + total_loc) if (project_loc + total_loc) > 0 else 0.0

                    if verbose:
                        print(f"    [osv] ✓ Total dependencies: {total_loc:,} LoC (ratio: {ratio:.1%})")
                else:
                    if verbose:
                        print(f"    [osv] ✗ No dependencies found in SBOM")
            else:
                if verbose:
                    print(f"    [osv] No lockfiles found (no dependency data)")

            # Step 3: Detect AI markers
            if verbose:
                print(f"    [ai] Detecting AI tool markers")
            ai_markers = {}
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
                if verbose:
                    print(f"    [ai] ✗ Detection failed (continuing without AI markers)")

            # Step 4: Package already detected in Step 1 (before cloning)
            # If it wasn't detected earlier, we won't try again here

            # Step 5: Save results
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

    except Exception as e:
        if verbose:
            print(f"    [error] Analysis failed: {e.__class__.__name__}")
        return None
