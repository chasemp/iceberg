import logging
import re
from datetime import datetime, timezone
from typing import Any

import httpx
from bs4 import BeautifulSoup
from pydantic import HttpUrl

from iceberg.exceptions import GitHubError
from iceberg.models import DiscoveredRepo, TrendingRepo

logger = logging.getLogger(__name__)


def parse_trending_html(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    articles = soup.find_all("article", class_="Box-row")

    repos: list[dict[str, Any]] = []

    for article in articles:
        h2 = article.find("h2", class_="h3")
        if not h2:
            continue

        link = h2.find("a")
        if not link or not link.get("href"):
            continue

        href = str(link.get("href"))
        parts = href.strip("/").split("/")
        if len(parts) < 2:
            continue

        owner = parts[0]
        name = parts[1]

        description_tag = article.find("p", class_="col-9")
        description = description_tag.get_text(strip=True) if description_tag else None

        language_tag = article.find("span", {"itemprop": "programmingLanguage"})
        language = language_tag.get_text(strip=True) if language_tag else None

        stars = 0
        star_svg = article.find("svg", {"aria-label": "star"})
        if star_svg and star_svg.parent:
            star_text = star_svg.parent.get_text(strip=True)
            star_text_cleaned = re.sub(r"[,\s]", "", star_text)
            if star_text_cleaned.isdigit():
                stars = int(star_text_cleaned)

        url_str = f"https://github.com/{owner}/{name}"

        repos.append(
            {
                "name": name,
                "owner": owner,
                "url": url_str,
                "description": description if description else None,
                "language": language if language else None,
                "stars": stars,
            }
        )

    return repos


def fetch_trending_repos(
    limit: int = 10,
) -> list[DiscoveredRepo]:
    """Fetch monthly trending repos from GitHub.

    Args:
        limit: Maximum number of repos to return

    Returns:
        List of DiscoveredRepo instances with source "trending-monthly"

    Raises:
        GitHubError: When fetching fails
    """
    try:
        url = "https://github.com/trending?since=monthly"
        source = "trending-monthly"

        logger.info(f"Fetching trending repos from {url}")
        response = httpx.get(url, timeout=30.0, follow_redirects=True)
        response.raise_for_status()
        repos = parse_trending_html(response.text)

        # Add source and timestamp to repos
        discovered_at = datetime.now(timezone.utc).isoformat()
        discovered_repos = [
            DiscoveredRepo(
                **repo,
                source=source,
                discovered_at=discovered_at,
                search_query=None,
            )
            for repo in repos[:limit]
        ]

        logger.info(f"Successfully fetched {len(discovered_repos)} trending repos")
        return discovered_repos
    except Exception as e:
        logger.error(f"Failed to fetch trending repos: {e}")
        raise GitHubError(f"Failed to fetch trending repos: {e}") from e


def fetch_repo_metadata(owner: str, repo: str) -> dict[str, Any]:
    """Fetch repository metadata from GitHub API.

    Args:
        owner: Repository owner
        repo: Repository name

    Returns:
        Dictionary with repo metadata (name, owner, url, description, language, stars)

    Raises:
        GitHubError: When API request fails
    """
    try:
        url = f"https://api.github.com/repos/{owner}/{repo}"
        logger.info(f"Fetching repo metadata from {url}")

        response = httpx.get(url, timeout=30.0, follow_redirects=True)
        response.raise_for_status()
        data = response.json()

        metadata = {
            "owner": data["owner"]["login"],
            "name": data["name"],
            "url": data["html_url"],
            "description": data.get("description"),
            "language": data.get("language"),
            "stars": data.get("stargazers_count", 0),
        }

        logger.info(f"Successfully fetched metadata for {owner}/{repo}")
        return metadata
    except Exception as e:
        logger.error(f"Failed to fetch repo metadata for {owner}/{repo}: {e}")
        raise GitHubError(f"Failed to fetch repo metadata for {owner}/{repo}: {e}") from e
