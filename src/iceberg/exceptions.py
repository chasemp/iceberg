"""Domain exception hierarchy for Iceberg.

This module defines a consistent exception hierarchy for the Iceberg project,
enabling structured error handling and clear error propagation.

Error Handling Strategy:
- Use domain-specific exceptions for business logic errors
- Use base IcebergError to catch all domain exceptions
- Network errors (GitHub, deps.dev) inherit from NetworkError
- Cache-related errors use CacheError (distinct from file-not-found)
- Repository lookup failures use RepositoryNotFoundError
"""


class IcebergError(Exception):
    """Base exception for all Iceberg domain errors."""

    pass


class RepositoryNotFoundError(IcebergError):
    """Raised when a repository cannot be found."""

    pass


class CacheError(IcebergError):
    """Raised when cache data is corrupted or invalid.

    This is distinct from cache-miss (file not found), which returns None.
    CacheError indicates data corruption or invalid format.
    """

    pass


class NetworkError(IcebergError):
    """Base exception for network-related errors."""

    pass


class GitHubError(NetworkError):
    """Raised when GitHub API requests fail."""

    pass


class DepsDevError(NetworkError):
    """Raised when deps.dev API requests fail."""

    pass
