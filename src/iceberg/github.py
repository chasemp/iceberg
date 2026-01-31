import re
from typing import Any

import httpx
from bs4 import BeautifulSoup
from pydantic import HttpUrl

from iceberg.models import TrendingRepo


class GitHubError(Exception):
    pass


def parse_trending_html(html: str) -> list[TrendingRepo]:
    soup = BeautifulSoup(html, "html.parser")
    articles = soup.find_all("article", class_="Box-row")

    repos: list[TrendingRepo] = []

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
            TrendingRepo(
                name=name,
                owner=owner,
                url=HttpUrl(url_str),
                description=description if description else None,
                language=language if language else None,
                stars=stars,
            )
        )

    return repos


def fetch_trending_repos(limit: int = 10) -> list[TrendingRepo]:
    try:
        response = httpx.get("https://github.com/trending")
        response.raise_for_status()
        repos = parse_trending_html(response.text)
        return repos[:limit]
    except Exception as e:
        raise GitHubError(f"Failed to fetch trending repos: {e}") from e
