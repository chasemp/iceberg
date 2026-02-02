import pytest
from pytest_httpx import HTTPXMock


def test_build_search_query_with_stars_filter() -> None:
    from iceberg.github_search import build_search_query

    query = build_search_query(stars=">1000")

    assert query == "stars:>1000"


def test_build_search_query_with_multiple_filters() -> None:
    from iceberg.github_search import build_search_query

    query = build_search_query(stars=">1000", language="python")

    assert "stars:>1000" in query
    assert "language:python" in query


def test_build_search_query_with_custom_query() -> None:
    from iceberg.github_search import build_search_query

    query = build_search_query(custom_query="stars:>5000 language:rust")

    assert query == "stars:>5000 language:rust"


def test_search_repositories_returns_discovered_repos(httpx_mock: HTTPXMock) -> None:
    from iceberg.github_search import search_repositories

    httpx_mock.add_response(
        url="https://api.github.com/search/repositories?q=stars%3A%3E1000&per_page=30&page=1",
        json={
            "items": [
                {
                    "name": "react",
                    "owner": {"login": "facebook"},
                    "html_url": "https://github.com/facebook/react",
                    "description": "A JavaScript library",
                    "language": "JavaScript",
                    "stargazers_count": 220000,
                }
            ]
        },
    )

    repos = search_repositories("stars:>1000", limit=30)

    assert len(repos) == 1
    assert repos[0].name == "react"
    assert repos[0].owner == "facebook"
    assert repos[0].source == "search"
    assert repos[0].search_query == "stars:>1000"


def test_search_repositories_handles_multiple_results(httpx_mock: HTTPXMock) -> None:
    from iceberg.github_search import search_repositories

    httpx_mock.add_response(
        url="https://api.github.com/search/repositories?q=language%3Apython&per_page=30&page=1",
        json={
            "items": [
                {
                    "name": "requests",
                    "owner": {"login": "psf"},
                    "html_url": "https://github.com/psf/requests",
                    "description": "HTTP library",
                    "language": "Python",
                    "stargazers_count": 50000,
                },
                {
                    "name": "flask",
                    "owner": {"login": "pallets"},
                    "html_url": "https://github.com/pallets/flask",
                    "description": "Web framework",
                    "language": "Python",
                    "stargazers_count": 65000,
                },
            ]
        },
    )

    repos = search_repositories("language:python", limit=30)

    assert len(repos) == 2
    assert repos[0].name == "requests"
    assert repos[1].name == "flask"


def test_search_repositories_with_authentication(httpx_mock: HTTPXMock) -> None:
    from iceberg.github_search import search_repositories

    httpx_mock.add_response(
        url="https://api.github.com/search/repositories?q=stars%3A%3E1000&per_page=30&page=1",
        json={"items": []},
        match_headers={"Authorization": "Bearer test-token"},
    )

    repos = search_repositories("stars:>1000", limit=30, token="test-token")

    assert len(repos) == 0


def test_search_repositories_handles_null_description(httpx_mock: HTTPXMock) -> None:
    from iceberg.github_search import search_repositories

    httpx_mock.add_response(
        url="https://api.github.com/search/repositories?q=stars%3A%3E1000&per_page=30&page=1",
        json={
            "items": [
                {
                    "name": "test-repo",
                    "owner": {"login": "test-owner"},
                    "html_url": "https://github.com/test-owner/test-repo",
                    "description": None,
                    "language": None,
                    "stargazers_count": 5000,
                }
            ]
        },
    )

    repos = search_repositories("stars:>1000", limit=30)

    assert len(repos) == 1
    assert repos[0].description is None
    assert repos[0].language is None


def test_search_repositories_rate_limit_error(httpx_mock: HTTPXMock) -> None:
    from iceberg.github_search import RateLimitError, search_repositories

    httpx_mock.add_response(
        url="https://api.github.com/search/repositories?q=stars%3A%3E1000&per_page=30&page=1",
        status_code=403,
        json={
            "message": "API rate limit exceeded",
            "documentation_url": "https://docs.github.com/rest/overview/resources-in-the-rest-api#rate-limiting",
        },
        headers={"X-RateLimit-Reset": "1609459200"},
    )

    with pytest.raises(RateLimitError) as exc_info:
        search_repositories("stars:>1000", limit=30)

    assert "rate limit" in str(exc_info.value).lower()


def test_search_repositories_handles_network_error(httpx_mock: HTTPXMock) -> None:
    from iceberg.github_search import GitHubSearchError, search_repositories

    httpx_mock.add_exception(Exception("Network error"))

    with pytest.raises(GitHubSearchError) as exc_info:
        search_repositories("stars:>1000", limit=30)

    assert "Failed to search" in str(exc_info.value)


def test_search_repositories_pagination_for_large_limits(httpx_mock: HTTPXMock) -> None:
    from iceberg.github_search import search_repositories

    # First page (100 results)
    httpx_mock.add_response(
        url="https://api.github.com/search/repositories?q=stars%3A%3E1000&per_page=100&page=1",
        json={
            "items": [
                {
                    "name": f"repo{i}",
                    "owner": {"login": "owner"},
                    "html_url": f"https://github.com/owner/repo{i}",
                    "description": "Test repo",
                    "language": "Python",
                    "stargazers_count": 5000,
                }
                for i in range(100)
            ]
        },
    )

    # Second page (50 results to reach limit of 150)
    httpx_mock.add_response(
        url="https://api.github.com/search/repositories?q=stars%3A%3E1000&per_page=50&page=2",
        json={
            "items": [
                {
                    "name": f"repo{i}",
                    "owner": {"login": "owner"},
                    "html_url": f"https://github.com/owner/repo{i}",
                    "description": "Test repo",
                    "language": "Python",
                    "stargazers_count": 5000,
                }
                for i in range(100, 150)
            ]
        },
    )

    repos = search_repositories("stars:>1000", limit=150)

    assert len(repos) == 150
    assert repos[0].name == "repo0"
    assert repos[99].name == "repo99"
    assert repos[100].name == "repo100"
    assert repos[149].name == "repo149"
