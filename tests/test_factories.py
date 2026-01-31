from tests.factories import (
    create_loc_metrics,
    create_package_identifier,
    create_trending_repo,
)


def test_create_trending_repo_produces_valid_instance() -> None:
    repo = create_trending_repo()
    assert repo.name == "example"
    assert repo.owner == "owner"


def test_create_trending_repo_accepts_overrides() -> None:
    repo = create_trending_repo(name="custom", stars=500)
    assert repo.name == "custom"
    assert repo.stars == 500


def test_create_package_identifier_produces_valid_instance() -> None:
    pkg = create_package_identifier()
    assert pkg.system == "npm"
    assert pkg.name == "react"


def test_create_package_identifier_accepts_overrides() -> None:
    pkg = create_package_identifier(system="pypi", name="requests")
    assert pkg.system == "pypi"
    assert pkg.name == "requests"


def test_create_loc_metrics_produces_valid_instance() -> None:
    metrics = create_loc_metrics()
    assert metrics.total_lines == 10000
    assert metrics.source == "depsdev"


def test_create_loc_metrics_accepts_overrides() -> None:
    pkg = create_package_identifier(name="custom")
    metrics = create_loc_metrics(package=pkg, total_lines=5000)
    assert metrics.package.name == "custom"
    assert metrics.total_lines == 5000


def test_create_loc_metrics_creates_default_package_if_none() -> None:
    metrics = create_loc_metrics()
    assert metrics.package.name == "react"
