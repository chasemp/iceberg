from datetime import datetime, timezone
from typing import Any

import httpx

from iceberg.models import DiscoveredRepo


class GitHubSearchError(Exception):
    """Raised when GitHub Search API fails."""
    pass


class RateLimitError(GitHubSearchError):
    """Raised when rate limit exceeded."""

    def __init__(self, reset_at: int) -> None:
        self.reset_at = reset_at
        reset_time = datetime.fromtimestamp(reset_at, tz=timezone.utc)
        msg = f"Rate limit exceeded. Resets at {reset_time}"
        super().__init__(msg)


def build_search_query(
    stars: str | None = None,
    language: str | None = None,
    created: str | None = None,
    pushed: str | None = None,
    custom_query: str | None = None,
) -> str:
    """Build GitHub search query string.

    Args:
        stars: Star count filter (e.g., ">1000", "1000..5000")
        language: Language filter (e.g., "python", "javascript")
        created: Created date filter (e.g., ">2024-01-01")
        pushed: Last push date filter (e.g., ">2024-01-01")
        custom_query: Custom query string (overrides other parameters)

    Returns:
        GitHub search query string
    """
    if custom_query:
        return custom_query

    parts: list[str] = []

    if stars:
        parts.append(f"stars:{stars}")
    if language:
        parts.append(f"language:{language}")
    if created:
        parts.append(f"created:{created}")
    if pushed:
        parts.append(f"pushed:{pushed}")

    return " ".join(parts)


def parse_search_response(
    response_json: dict[str, Any],
    query: str,
) -> list[DiscoveredRepo]:
    """Transform GitHub API response to DiscoveredRepo models.

    Args:
        response_json: GitHub API search response
        query: The search query used

    Returns:
        List of DiscoveredRepo instances
    """
    items = response_json.get("items", [])
    discovered_at = datetime.now(timezone.utc).isoformat()

    repos: list[DiscoveredRepo] = []

    for item in items:
        repo = DiscoveredRepo(
            name=item["name"],
            owner=item["owner"]["login"],
            url=item["html_url"],
            description=item.get("description"),
            language=item.get("language"),
            stars=item["stargazers_count"],
            source="search",
            discovered_at=discovered_at,
            search_query=query,
        )
        repos.append(repo)

    return repos


def search_repositories(
    query: str,
    limit: int = 30,
    token: str | None = None,
) -> list[DiscoveredRepo]:
    """Search GitHub repositories via REST API.

    Args:
        query: GitHub search query string
        limit: Maximum number of results (supports pagination for limit > 100)
        token: Optional GitHub token for authentication

    Returns:
        List of DiscoveredRepo instances

    Raises:
        RateLimitError: When rate limit is exceeded
        GitHubSearchError: When search fails
    """
    try:
        headers: dict[str, str] = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        all_repos: list[DiscoveredRepo] = []
        remaining = limit
        page = 1

        while remaining > 0:
            # GitHub API limits to 100 per page
            per_page = min(remaining, 100)

            url = f"https://api.github.com/search/repositories?q={query}&per_page={per_page}&page={page}"

            response = httpx.get(url, headers=headers, timeout=10.0, follow_redirects=True)

            # Check for rate limit
            if response.status_code == 403:
                reset_header = response.headers.get("X-RateLimit-Reset")
                if reset_header:
                    raise RateLimitError(int(reset_header))

            response.raise_for_status()

            data = response.json()
            repos = parse_search_response(data, query)

            if not repos:
                break

            all_repos.extend(repos)
            remaining -= len(repos)

            # Stop if we got fewer results than requested (no more pages)
            if len(repos) < per_page:
                break

            page += 1

        return all_repos

    except RateLimitError:
        raise
    except Exception as e:
        raise GitHubSearchError(f"Failed to search repositories: {e}") from e
