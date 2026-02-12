"""Tests for exception hierarchy."""


def test_iceberg_error_is_base_exception() -> None:
    """Test that IcebergError is the base exception."""
    from iceberg.exceptions import IcebergError

    error = IcebergError("test error")
    assert isinstance(error, Exception)
    assert str(error) == "test error"


def test_repository_not_found_error_inherits_from_iceberg_error() -> None:
    """Test RepositoryNotFoundError is a subclass of IcebergError."""
    from iceberg.exceptions import IcebergError, RepositoryNotFoundError

    error = RepositoryNotFoundError("owner/repo not found")
    assert isinstance(error, IcebergError)
    assert isinstance(error, Exception)


def test_cache_error_inherits_from_iceberg_error() -> None:
    """Test CacheError is a subclass of IcebergError."""
    from iceberg.exceptions import CacheError, IcebergError

    error = CacheError("cache corrupted")
    assert isinstance(error, IcebergError)
    assert isinstance(error, Exception)


def test_network_error_inherits_from_iceberg_error() -> None:
    """Test NetworkError is a subclass of IcebergError."""
    from iceberg.exceptions import IcebergError, NetworkError

    error = NetworkError("connection failed")
    assert isinstance(error, IcebergError)
    assert isinstance(error, Exception)


def test_github_error_inherits_from_network_error() -> None:
    """Test GitHubError is a subclass of NetworkError."""
    from iceberg.exceptions import GitHubError, IcebergError, NetworkError

    error = GitHubError("GitHub API failed")
    assert isinstance(error, NetworkError)
    assert isinstance(error, IcebergError)
    assert isinstance(error, Exception)


def test_depsdev_error_inherits_from_network_error() -> None:
    """Test DepsDevError is a subclass of NetworkError."""
    from iceberg.exceptions import DepsDevError, IcebergError, NetworkError

    error = DepsDevError("deps.dev API failed")
    assert isinstance(error, NetworkError)
    assert isinstance(error, IcebergError)
    assert isinstance(error, Exception)


def test_exception_hierarchy_allows_catching_by_base_class() -> None:
    """Test that catching IcebergError catches all domain exceptions."""
    from iceberg.exceptions import (
        CacheError,
        DepsDevError,
        GitHubError,
        IcebergError,
        RepositoryNotFoundError,
    )

    exceptions = [
        RepositoryNotFoundError("not found"),
        CacheError("cache error"),
        GitHubError("github error"),
        DepsDevError("depsdev error"),
    ]

    for exception in exceptions:
        try:
            raise exception
        except IcebergError:
            pass  # Successfully caught by base class
        else:
            assert False, f"{exception.__class__.__name__} was not caught by IcebergError"
