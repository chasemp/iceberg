from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock

from iceberg.models import DiscoveredRepo, TrendingRepo


def load_fixture(filename: str) -> str:
    fixture_path = Path(__file__).parent / "fixtures" / filename
    return fixture_path.read_text()


def test_parse_trending_html_extracts_single_repo() -> None:
    from iceberg.github import parse_trending_html

    html = """
    <article class="Box-row">
      <h2 class="h3 lh-condensed">
        <a href="/owner/repo">
          <span class="text-normal">owner /</span>
          repo
        </a>
      </h2>
      <p class="col-9 color-fg-muted my-1 pr-4">
        A test description
      </p>
      <div class="f6 color-fg-muted mt-2">
        <span class="d-inline-block ml-0 mr-3">
          <span itemprop="programmingLanguage">Python</span>
        </span>
        <span class="d-inline-block mr-3">
          <svg aria-label="star"></svg>
          1,234
        </span>
      </div>
    </article>
    """

    repos = parse_trending_html(html)

    assert len(repos) == 1
    assert repos[0]["name"] == "repo"
    assert repos[0]["owner"] == "owner"
    assert repos[0]["url"] == "https://github.com/owner/repo"
    assert repos[0]["description"] == "A test description"
    assert repos[0]["language"] == "Python"
    assert repos[0]["stars"] == 1234


def test_parse_trending_html_extracts_multiple_repos() -> None:
    from iceberg.github import parse_trending_html

    html = load_fixture("github_trending.html")
    repos = parse_trending_html(html)

    assert len(repos) == 2
    assert repos[0]["name"] == "repo1"
    assert repos[0]["owner"] == "owner1"
    assert repos[0]["stars"] == 1234
    assert repos[1]["name"] == "repo2"
    assert repos[1]["owner"] == "owner2"
    assert repos[1]["stars"] == 567


def test_parse_trending_html_handles_missing_description() -> None:
    from iceberg.github import parse_trending_html

    html = """
    <article class="Box-row">
      <h2 class="h3 lh-condensed">
        <a href="/owner/repo">
          <span class="text-normal">owner /</span>
          repo
        </a>
      </h2>
      <div class="f6 color-fg-muted mt-2">
        <span class="d-inline-block ml-0 mr-3">
          <span itemprop="programmingLanguage">Python</span>
        </span>
        <span class="d-inline-block mr-3">
          <svg aria-label="star"></svg>
          100
        </span>
      </div>
    </article>
    """

    repos = parse_trending_html(html)

    assert len(repos) == 1
    assert repos[0]["description"] is None


def test_parse_trending_html_handles_missing_language() -> None:
    from iceberg.github import parse_trending_html

    html = """
    <article class="Box-row">
      <h2 class="h3 lh-condensed">
        <a href="/owner/repo">
          <span class="text-normal">owner /</span>
          repo
        </a>
      </h2>
      <p class="col-9 color-fg-muted my-1 pr-4">
        A test description
      </p>
      <div class="f6 color-fg-muted mt-2">
        <span class="d-inline-block mr-3">
          <svg aria-label="star"></svg>
          100
        </span>
      </div>
    </article>
    """

    repos = parse_trending_html(html)

    assert len(repos) == 1
    assert repos[0]["language"] is None


def test_parse_trending_html_handles_star_count_with_commas() -> None:
    from iceberg.github import parse_trending_html

    html = """
    <article class="Box-row">
      <h2 class="h3 lh-condensed">
        <a href="/owner/repo">
          <span class="text-normal">owner /</span>
          repo
        </a>
      </h2>
      <div class="f6 color-fg-muted mt-2">
        <span class="d-inline-block mr-3">
          <svg aria-label="star"></svg>
          12,345
        </span>
      </div>
    </article>
    """

    repos = parse_trending_html(html)

    assert repos[0]["stars"] == 12345


def test_fetch_trending_repos_makes_http_request(httpx_mock: HTTPXMock) -> None:
    from iceberg.github import fetch_trending_repos

    httpx_mock.add_response(
        url="https://github.com/trending?since=monthly",
        text=load_fixture("github_trending.html"),
    )

    repos = fetch_trending_repos()

    assert len(repos) == 2
    assert isinstance(repos[0], DiscoveredRepo)
    assert repos[0].source == "trending-monthly"
    assert repos[0].discovered_at is not None
    assert repos[0].search_query is None


def test_fetch_trending_repos_respects_limit(httpx_mock: HTTPXMock) -> None:
    from iceberg.github import fetch_trending_repos

    httpx_mock.add_response(
        url="https://github.com/trending?since=monthly",
        text=load_fixture("github_trending.html"),
    )

    repos = fetch_trending_repos(limit=1)

    assert len(repos) == 1
    assert repos[0].name == "repo1"
    assert repos[0].source == "trending-monthly"


def test_fetch_trending_repos_handles_network_error(httpx_mock: HTTPXMock) -> None:
    from iceberg.github import GitHubError, fetch_trending_repos

    httpx_mock.add_exception(Exception("Network error"))

    with pytest.raises(GitHubError) as exc_info:
        fetch_trending_repos()

    assert "Failed to fetch trending repos" in str(exc_info.value)


def test_fetch_trending_repos_fetches_monthly(httpx_mock: HTTPXMock) -> None:
    from iceberg.github import fetch_trending_repos

    httpx_mock.add_response(
        url="https://github.com/trending?since=monthly",
        text=load_fixture("github_trending.html"),
    )

    repos = fetch_trending_repos(limit=10)

    assert len(repos) == 2
    assert repos[0].source == "trending-monthly"
    assert repos[0].discovered_at is not None
