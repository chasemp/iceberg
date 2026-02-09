"""Fetch repositories from EvanLi/Github-Ranking.

This module fetches curated top repositories from the Github-Ranking project,
which maintains daily-updated lists of the most starred repositories by language.

Source: https://github.com/EvanLi/Github-Ranking
"""

import re
from datetime import datetime, timezone
from typing import Literal
from urllib.request import Request, urlopen

from iceberg.models import DiscoveredRepo

# Available categories from Github-Ranking
AVAILABLE_CATEGORIES = [
    "Top-100-stars",
    "Top-100-forks",
    "Python",
    "JavaScript",
    "TypeScript",
    "Java",
    "Go",
    "C",
    "CPP",
    "CSharp",
    "Ruby",
    "PHP",
    "Swift",
    "Rust",
    "Kotlin",
    "Scala",
    "Dart",
    "R",
    "Shell",
    "Vim-script",
    "HTML",
    "CSS",
]

CategoryType = Literal[
    "Top-100-stars",
    "Top-100-forks",
    "Python",
    "JavaScript",
    "TypeScript",
    "Java",
    "Go",
    "C",
    "CPP",
    "CSharp",
    "Ruby",
    "PHP",
    "Swift",
    "Rust",
    "Kotlin",
    "Scala",
    "Dart",
    "R",
    "Shell",
    "Vim-script",
    "HTML",
    "CSS",
]


def fetch_github_ranking(
    category: CategoryType = "Top100",
    limit: int = 100,
) -> list[DiscoveredRepo]:
    """Fetch repositories from Github-Ranking.

    Args:
        category: Category to fetch (language name or "Top100" for overall)
        limit: Maximum number of repositories to return (default 100)

    Returns:
        List of DiscoveredRepo objects

    Raises:
        Exception: If fetch fails or parsing fails
    """
    # Build URL to raw markdown file
    base_url = "https://raw.githubusercontent.com/EvanLi/Github-Ranking/master/Top100"
    url = f"{base_url}/{category}.md"

    # Fetch markdown content
    try:
        req = Request(url)
        req.add_header("User-Agent", "iceberg-analysis/1.0")
        with urlopen(req, timeout=30) as response:
            content = response.read().decode("utf-8")
    except Exception as e:
        raise Exception(f"Failed to fetch {category} rankings: {e}") from e

    # Parse markdown table
    repos = _parse_markdown_table(content, category)

    # Apply limit
    return repos[:limit]


def _parse_markdown_table(content: str, category: str) -> list[DiscoveredRepo]:
    """Parse markdown table to extract repository information.

    Expected format:
    | Ranking | Project Name | Stars | Forks | Language | Open Issues | Description | Last Commit |
    | 1 | [repo-name](https://github.com/owner/repo) | 12345 | 678 | Python | 10 | "Description" | 2024-01-01T00:00:00Z |
    """
    repos: list[DiscoveredRepo] = []
    lines = content.split("\n")

    # Find table start (after header separator line with dashes)
    table_start = -1
    for i, line in enumerate(lines):
        if line.strip().startswith("|") and "---" in line:
            table_start = i + 1
            break

    if table_start == -1:
        raise Exception("Could not find table in markdown")

    # Parse each row
    for line in lines[table_start:]:
        line = line.strip()
        if not line or not line.startswith("|"):
            continue

        # Split by pipe and clean up
        cols = [col.strip() for col in line.split("|")[1:-1]]  # Remove empty first/last

        if len(cols) < 8:
            continue  # Skip malformed rows

        # Extract data
        ranking = cols[0]
        project_name = cols[1]
        stars_str = cols[2]
        forks_str = cols[3]
        language = cols[4]
        open_issues = cols[5]
        description = cols[6].strip('"')
        last_commit = cols[7]

        # Extract GitHub URL from markdown link: [name](url)
        link_match = re.search(r"\[([^\]]+)\]\(([^\)]+)\)", project_name)
        if not link_match:
            continue

        name = link_match.group(1)
        url = link_match.group(2)

        # Extract owner and repo from URL
        # URL format: https://github.com/owner/repo
        url_match = re.search(r"github\.com/([^/]+)/([^/\s]+)", url)
        if not url_match:
            continue

        owner = url_match.group(1)
        repo = url_match.group(2)

        # Parse stars (remove commas)
        try:
            stars = int(stars_str.replace(",", ""))
        except ValueError:
            stars = 0

        # Create DiscoveredRepo
        discovered_repo = DiscoveredRepo(
            owner=owner,
            name=repo,
            url=url,
            description=description,
            language=language if language and language != "-" else None,
            stars=stars,
            source=f"github-ranking-{category.lower()}",
            discovered_at=datetime.now(timezone.utc).isoformat(),
        )

        repos.append(discovered_repo)

    return repos


def list_available_categories() -> list[str]:
    """Return list of available categories."""
    return AVAILABLE_CATEGORIES.copy()
