from pathlib import Path
from typing import Any, Callable

from iceberg.cache import (
    get_default_cache_dir,
    save_discovered_repos,
    save_repo_metadata,
)
from iceberg.github import fetch_trending_repos
from iceberg.github_ranking import fetch_github_ranking
from iceberg.github_search import build_search_query, search_repositories
from iceberg.models import DiscoveredRepo


def fetch_all_discovery_sources(
    log: Callable[[str], None] = print,
) -> list[DiscoveredRepo]:
    all_repos: list[DiscoveredRepo] = []

    log("Fetching discovery sources...\n")

    try:
        log("  Fetching trending monthly...")
        repos = fetch_trending_repos(limit=25)
        all_repos.extend(repos)
        log(f"  Got {len(repos)} repos from trending monthly")
    except Exception as e:
        log(f"  Failed to fetch trending monthly: {e}")

    for lang_config in [
        {"stars": ">10000", "language": "javascript", "limit": 50},
        {"stars": ">10000", "language": "python", "limit": 50},
    ]:
        try:
            label = f"stars>{lang_config['stars'].lstrip('>')} language:{lang_config['language']}"
            log(f"  Fetching search: {label}...")
            query = build_search_query(
                stars=lang_config["stars"], language=lang_config["language"]
            )
            repos = search_repositories(query, limit=lang_config["limit"])
            all_repos.extend(repos)
            log(f"  Got {len(repos)} repos from search")
        except Exception as e:
            log(f"  Failed to fetch search: {e}")

    for category in ["Top-100-stars", "Top-100-forks"]:
        try:
            log(f"  Fetching GitHub-Ranking: {category}...")
            repos = fetch_github_ranking(category=category, limit=100)
            all_repos.extend(repos)
            log(f"  Got {len(repos)} repos from GitHub-Ranking ({category})")
        except Exception as e:
            log(f"  Failed to fetch GitHub-Ranking {category}: {e}")

    languages = [
        "Python", "JavaScript", "TypeScript", "Java", "Go", "Rust",
        "C", "CPP", "CSharp", "PHP", "Ruby", "Swift", "Kotlin",
        "R", "Scala", "Dart", "Shell", "Lua", "Haskell", "Julia", "Elixir",
    ]
    for category in languages:
        try:
            log(f"  Fetching GitHub-Ranking: {category}...")
            repos = fetch_github_ranking(category=category, limit=25)
            all_repos.extend(repos)
            log(f"  Got {len(repos)} repos from GitHub-Ranking ({category})")
        except Exception as e:
            log(f"  Failed to fetch GitHub-Ranking {category}: {e}")

    return all_repos


def deduplicate_repos(repos: list[DiscoveredRepo]) -> list[DiscoveredRepo]:
    seen: set[str] = set()
    unique: list[DiscoveredRepo] = []

    for repo in repos:
        key = f"{repo.owner}/{repo.name}"
        if key not in seen:
            seen.add(key)
            unique.append(repo)

    return unique


def save_discovery_results(
    all_repos: list[DiscoveredRepo],
    unique_repos: list[DiscoveredRepo],
    cache_dir: Path | None = None,
) -> dict[str, int]:
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    sources: dict[str, list[DiscoveredRepo]] = {}
    for repo in unique_repos:
        source = repo.source
        if source not in sources:
            sources[source] = []
        sources[source].append(repo)

    for source, repos in sources.items():
        save_discovered_repos(repos, cache_dir=cache_dir)

    for repo in all_repos:
        save_repo_metadata(repo, repo.source, cache_dir=cache_dir)

    return {"sources_saved": len(sources), "repos_saved": len(unique_repos)}


def run_discovery(
    cache_dir: Path | None = None,
    verbose: bool = False,
    log: Callable[[str], None] = print,
) -> dict[str, Any]:
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    all_repos = fetch_all_discovery_sources(log=log)
    unique_repos = deduplicate_repos(all_repos)

    log(f"\nTotal repos fetched: {len(all_repos)}")
    log(f"Unique repos: {len(unique_repos)}")

    save_results = save_discovery_results(all_repos, unique_repos, cache_dir=cache_dir)

    sources_summary: dict[str, int] = {}
    for repo in all_repos:
        sources_summary[repo.source] = sources_summary.get(repo.source, 0) + 1

    return {
        "total_fetched": len(all_repos),
        "unique_repos": len(unique_repos),
        "sources": sources_summary,
        **save_results,
    }
