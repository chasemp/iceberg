"""GitHub API client with rate limiting and retry logic."""

import logging
import time
from typing import Any

import httpx

from iceberg.exceptions import GitHubError

logger = logging.getLogger(__name__)

# Retryable status codes
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# Non-retryable client error codes
CLIENT_ERROR_CODES = {400, 401, 404, 422}


class GitHubClient:
    """GitHub API client with automatic rate limiting and retry logic.

    Features:
    - Automatic rate limit detection and waiting
    - Exponential backoff for transient errors
    - Respects Retry-After and X-RateLimit-Reset headers
    - Proactive rate limit checking before requests

    Can be used as a context manager:
        with GitHubClient(token=token) as client:
            response = client.get("/repos/owner/repo")
    """

    def __init__(
        self,
        token: str | None = None,
        max_retries: int = 3,
        base_url: str = "https://api.github.com",
        timeout: float = 30.0,
    ) -> None:
        self.token = token
        self.max_retries = max_retries
        self.base_url = base_url
        self.timeout = timeout

        # Rate limit tracking
        self._rate_limit_remaining: int | None = None
        self._rate_limit_reset: int | None = None

        # HTTP client (trust_env=False to avoid proxy issues in tests)
        self._client = httpx.Client(
            timeout=timeout, follow_redirects=True, trust_env=False
        )

    def __enter__(self) -> "GitHubClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def get(self, path: str, **kwargs: Any) -> httpx.Response:
        """Make a GET request to GitHub API with rate limiting and retries.

        Args:
            path: API path (e.g., "/repos/owner/repo")
            **kwargs: Additional arguments passed to httpx.get()

        Returns:
            httpx.Response object

        Raises:
            GitHubError: When request fails after all retries
        """
        return self._request("GET", path, **kwargs)

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Make an HTTP request with rate limiting and retries.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path
            **kwargs: Additional arguments passed to httpx request

        Returns:
            httpx.Response object

        Raises:
            GitHubError: When request fails after all retries
        """
        # Check rate limit before making request
        self._check_rate_limit()

        url = f"{self.base_url}{path}" if path.startswith("/") else f"{self.base_url}/{path}"

        headers = kwargs.pop("headers", {})
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        kwargs["headers"] = headers
        kwargs.setdefault("timeout", self.timeout)
        kwargs.setdefault("follow_redirects", True)

        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self._make_request(method, url, **kwargs)

                # Update rate limit info from headers
                self._update_rate_limit(response)

                # Handle rate limiting
                if response.status_code == 403:
                    if self._is_rate_limit_error(response):
                        if attempt < self.max_retries:
                            wait_time = self._get_rate_limit_wait_time(response)
                            logger.warning(
                                f"Rate limit exceeded. Waiting {wait_time:.1f}s before retry "
                                f"(attempt {attempt + 1}/{self.max_retries})"
                            )
                            time.sleep(wait_time)
                            continue
                        else:
                            raise GitHubError(
                                f"Rate limit exceeded and max retries reached. "
                                f"Reset at: {self._rate_limit_reset}"
                            )

                # Don't retry client errors (except rate limits)
                if response.status_code in CLIENT_ERROR_CODES:
                    response.raise_for_status()

                # Handle retryable errors (5xx, 429)
                if response.status_code in RETRYABLE_STATUS_CODES:
                    if attempt < self.max_retries:
                        wait_time = self._get_retry_wait_time(response, attempt)
                        logger.warning(
                            f"Request failed with {response.status_code}. "
                            f"Retrying in {wait_time:.1f}s (attempt {attempt + 1}/{self.max_retries})"
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        response.raise_for_status()

                # Success or non-retryable error
                response.raise_for_status()
                return response

            except httpx.HTTPStatusError as e:
                # Don't retry client errors (4xx except rate limits)
                if e.response.status_code in CLIENT_ERROR_CODES:
                    raise GitHubError(f"HTTP {e.response.status_code}: {e}") from e
                last_error = e
                if attempt >= self.max_retries:
                    break
            except Exception as e:
                last_error = e
                if attempt >= self.max_retries:
                    break
                # Retry on network errors
                wait_time = self._calculate_exponential_backoff(attempt)
                logger.warning(f"Request failed: {e}. Retrying in {wait_time:.1f}s")
                time.sleep(wait_time)

        # All retries exhausted
        error_msg = f"Failed after {self.max_retries} retries"
        if last_error:
            error_msg = f"{error_msg}: {last_error}"
        raise GitHubError(error_msg) from last_error

    def _make_request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Make the actual HTTP request.

        Args:
            method: HTTP method
            url: Full URL
            **kwargs: Request arguments

        Returns:
            httpx.Response object
        """
        return self._client.request(method, url, **kwargs)

    def _check_rate_limit(self) -> None:
        """Check if we should wait before making a request due to rate limits."""
        if self._rate_limit_remaining is None or self._rate_limit_reset is None:
            return

        # Warn if rate limit is low
        if self._rate_limit_remaining < 10:
            logger.warning(
                f"GitHub rate limit low: {self._rate_limit_remaining} requests remaining"
            )

        # Wait if rate limit is exhausted
        if self._rate_limit_remaining == 0:
            current_time = int(time.time())
            if self._rate_limit_reset > current_time:
                wait_time = self._rate_limit_reset - current_time + 1
                logger.warning(
                    f"Rate limit exhausted. Waiting {wait_time}s until reset at "
                    f"{time.ctime(self._rate_limit_reset)}"
                )
                time.sleep(wait_time)

    def _update_rate_limit(self, response: httpx.Response) -> None:
        """Update rate limit tracking from response headers.

        Args:
            response: HTTP response with rate limit headers
        """
        if "X-RateLimit-Remaining" in response.headers:
            self._rate_limit_remaining = int(response.headers["X-RateLimit-Remaining"])

        if "X-RateLimit-Reset" in response.headers:
            self._rate_limit_reset = int(response.headers["X-RateLimit-Reset"])

    def _is_rate_limit_error(self, response: httpx.Response) -> bool:
        """Check if a 403 response is due to rate limiting.

        Args:
            response: HTTP response

        Returns:
            True if response indicates rate limiting
        """
        # Check for explicit rate limit remaining header
        if "X-RateLimit-Remaining" in response.headers:
            return int(response.headers["X-RateLimit-Remaining"]) == 0

        # Check response body for rate limit message
        try:
            data = response.json()
            message = data.get("message", "").lower()
            return "rate limit" in message
        except Exception:
            return False

    def _get_rate_limit_wait_time(self, response: httpx.Response) -> float:
        """Calculate how long to wait for rate limit reset.

        Args:
            response: HTTP response with rate limit info

        Returns:
            Wait time in seconds
        """
        # Check for Retry-After header
        if "Retry-After" in response.headers:
            return float(response.headers["Retry-After"])

        # Check for X-RateLimit-Reset header
        if "X-RateLimit-Reset" in response.headers:
            reset_time = int(response.headers["X-RateLimit-Reset"])
            current_time = int(time.time())
            wait_time = max(0, reset_time - current_time) + 1  # Add 1s buffer
            return float(wait_time)

        # Default to 60 seconds if no headers available
        return 60.0

    def _get_retry_wait_time(self, response: httpx.Response, attempt: int) -> float:
        """Calculate retry wait time with exponential backoff.

        Args:
            response: HTTP response
            attempt: Current attempt number (0-indexed)

        Returns:
            Wait time in seconds
        """
        # Check for Retry-After header
        if "Retry-After" in response.headers:
            return float(response.headers["Retry-After"])

        # Use exponential backoff
        return self._calculate_exponential_backoff(attempt)

    def _calculate_exponential_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff wait time.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Wait time in seconds
        """
        # Base: 1s, 2s, 4s, 8s, etc.
        return min(2**attempt, 60.0)  # Cap at 60 seconds
