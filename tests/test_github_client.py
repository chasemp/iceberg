"""Tests for GitHub API client with rate limiting."""

import time
from unittest.mock import Mock, patch

import httpx
import pytest
from pytest_httpx import HTTPXMock

from iceberg.exceptions import GitHubError


def test_github_client_makes_successful_request(httpx_mock: HTTPXMock) -> None:
    from iceberg.github_client import GitHubClient

    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo",
        json={"name": "repo", "owner": {"login": "owner"}},
    )

    client = GitHubClient()
    response = client.get("/repos/owner/repo")

    assert response.status_code == 200
    assert response.json()["name"] == "repo"


def test_github_client_includes_auth_token_when_provided(httpx_mock: HTTPXMock) -> None:
    from iceberg.github_client import GitHubClient

    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo",
        json={"name": "repo"},
        match_headers={"Authorization": "Bearer test-token"},
    )

    client = GitHubClient(token="test-token")
    response = client.get("/repos/owner/repo")

    assert response.status_code == 200


def test_github_client_handles_403_rate_limit_with_retry_after(httpx_mock: HTTPXMock) -> None:
    from iceberg.github_client import GitHubClient

    # First request: rate limited
    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo",
        status_code=403,
        json={"message": "API rate limit exceeded"},
        headers={
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(int(time.time()) + 1),
        },
    )

    # Second request: success after waiting
    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo",
        json={"name": "repo"},
    )

    client = GitHubClient()

    with patch("time.sleep") as mock_sleep:
        response = client.get("/repos/owner/repo")

    # Should have waited before retrying
    assert mock_sleep.called
    assert response.status_code == 200
    assert response.json()["name"] == "repo"


def test_github_client_respects_retry_after_header(httpx_mock: HTTPXMock) -> None:
    from iceberg.github_client import GitHubClient

    # First request: rate limited with Retry-After header
    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo",
        status_code=403,
        headers={
            "Retry-After": "2",
            "X-RateLimit-Remaining": "0",
        },
    )

    # Second request: success
    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo",
        json={"name": "repo"},
    )

    client = GitHubClient()

    with patch("time.sleep") as mock_sleep:
        response = client.get("/repos/owner/repo")

    # Should have waited for the specified time
    mock_sleep.assert_called_once()
    wait_time = mock_sleep.call_args[0][0]
    assert wait_time >= 2
    assert response.status_code == 200


def test_github_client_uses_exponential_backoff_for_retries(httpx_mock: HTTPXMock) -> None:
    from iceberg.github_client import GitHubClient

    # First request: server error (retryable)
    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo",
        status_code=500,
    )

    # Second request: server error
    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo",
        status_code=500,
    )

    # Third request: success
    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo",
        json={"name": "repo"},
    )

    client = GitHubClient(max_retries=3)

    with patch("time.sleep") as mock_sleep:
        response = client.get("/repos/owner/repo")

    # Should have retried with exponential backoff
    assert mock_sleep.call_count == 2
    wait_times = [call[0][0] for call in mock_sleep.call_args_list]
    # First wait should be shorter than second wait (exponential)
    assert wait_times[0] < wait_times[1]
    assert response.status_code == 200


def test_github_client_stops_after_max_retries(httpx_mock: HTTPXMock) -> None:
    from iceberg.github_client import GitHubClient

    # All requests fail (1 initial + 3 retries = 4 total)
    for _ in range(4):
        httpx_mock.add_response(
            url="https://api.github.com/repos/owner/repo",
            status_code=500,
        )

    client = GitHubClient(max_retries=3)

    with patch("time.sleep"):
        with pytest.raises(GitHubError) as exc_info:
            client.get("/repos/owner/repo")

    assert "Failed after 3 retries" in str(exc_info.value)


def test_github_client_does_not_retry_404_errors(httpx_mock: HTTPXMock) -> None:
    from iceberg.github_client import GitHubClient

    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/nonexistent",
        status_code=404,
        json={"message": "Not Found"},
    )

    client = GitHubClient()

    with patch("time.sleep") as mock_sleep:
        with pytest.raises(GitHubError) as exc_info:
            client.get("/repos/owner/nonexistent")

    # Should not retry 404s
    assert not mock_sleep.called
    assert "404" in str(exc_info.value)


def test_github_client_checks_rate_limit_before_request(httpx_mock: HTTPXMock) -> None:
    from iceberg.github_client import GitHubClient

    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo",
        json={"name": "repo"},
    )

    client = GitHubClient()

    # Simulate having rate limit info from a previous request
    client._rate_limit_remaining = 0
    client._rate_limit_reset = int(time.time()) + 10

    with patch("time.sleep") as mock_sleep:
        response = client.get("/repos/owner/repo")

    # Should have waited before making request
    assert mock_sleep.called
    wait_time = mock_sleep.call_args[0][0]
    assert wait_time > 0
    assert response.status_code == 200


def test_github_client_updates_rate_limit_info_from_headers(httpx_mock: HTTPXMock) -> None:
    from iceberg.github_client import GitHubClient

    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo",
        json={"name": "repo"},
        headers={
            "X-RateLimit-Remaining": "42",
            "X-RateLimit-Reset": "1609459200",
        },
    )

    client = GitHubClient()
    response = client.get("/repos/owner/repo")

    assert response.status_code == 200
    assert client._rate_limit_remaining == 42
    assert client._rate_limit_reset == 1609459200


def test_github_client_logs_rate_limit_warnings() -> None:
    from iceberg.github_client import GitHubClient

    client = GitHubClient()
    client._rate_limit_remaining = 5
    client._rate_limit_reset = int(time.time()) + 60

    with patch("iceberg.github_client.logger") as mock_logger:
        client._check_rate_limit()

    # Should log warning when rate limit is low
    assert mock_logger.warning.called
    warning_msg = mock_logger.warning.call_args[0][0]
    assert "rate limit" in warning_msg.lower()
