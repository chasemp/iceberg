from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock


def test_detect_npm_package(httpx_mock: HTTPXMock) -> None:
    from iceberg.detector import detect_package

    package_json = """
    {
      "name": "react",
      "version": "18.2.0"
    }
    """

    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/facebook/react/main/package.json",
        text=package_json,
    )

    pkg = detect_package("facebook", "react")

    assert pkg is not None
    assert pkg.system == "npm"
    assert pkg.name == "react"
    assert pkg.version == "18.2.0"


def test_detect_pypi_package(httpx_mock: HTTPXMock) -> None:
    from iceberg.detector import detect_package

    pyproject_toml = """
    [project]
    name = "requests"
    version = "2.31.0"
    """

    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/psf/requests/main/pyproject.toml",
        status_code=404,
    )

    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/psf/requests/master/pyproject.toml",
        text=pyproject_toml,
    )

    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/psf/requests/main/package.json",
        status_code=404,
    )

    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/psf/requests/master/package.json",
        status_code=404,
    )

    pkg = detect_package("psf", "requests")

    assert pkg is not None
    assert pkg.system == "pypi"
    assert pkg.name == "requests"
    assert pkg.version == "2.31.0"


def test_detect_cargo_package(httpx_mock: HTTPXMock) -> None:
    from iceberg.detector import detect_package

    cargo_toml = """
    [package]
    name = "serde"
    version = "1.0.0"
    """

    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/serde-rs/serde/main/package.json",
        status_code=404,
    )

    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/serde-rs/serde/master/package.json",
        status_code=404,
    )

    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/serde-rs/serde/main/pyproject.toml",
        status_code=404,
    )

    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/serde-rs/serde/master/pyproject.toml",
        status_code=404,
    )

    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/serde-rs/serde/main/Cargo.toml",
        text=cargo_toml,
    )

    pkg = detect_package("serde-rs", "serde")

    assert pkg is not None
    assert pkg.system == "cargo"
    assert pkg.name == "serde"
    assert pkg.version == "1.0.0"


def test_detect_package_returns_none_when_not_found(httpx_mock: HTTPXMock) -> None:
    from iceberg.detector import detect_package

    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/owner/repo/main/package.json",
        status_code=404,
    )

    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/owner/repo/master/package.json",
        status_code=404,
    )

    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/owner/repo/main/pyproject.toml",
        status_code=404,
    )

    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/owner/repo/master/pyproject.toml",
        status_code=404,
    )

    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/owner/repo/main/Cargo.toml",
        status_code=404,
    )

    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/owner/repo/master/Cargo.toml",
        status_code=404,
    )

    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/owner/repo/main/pom.xml",
        status_code=404,
    )

    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/owner/repo/master/pom.xml",
        status_code=404,
    )

    pkg = detect_package("owner", "repo")

    assert pkg is None


def test_detect_maven_package(httpx_mock: HTTPXMock) -> None:
    from iceberg.detector import detect_package

    pom_xml = """
    <project>
      <artifactId>junit</artifactId>
      <version>4.13.2</version>
    </project>
    """

    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/junit-team/junit4/main/package.json",
        status_code=404,
    )

    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/junit-team/junit4/master/package.json",
        status_code=404,
    )

    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/junit-team/junit4/main/pyproject.toml",
        status_code=404,
    )

    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/junit-team/junit4/master/pyproject.toml",
        status_code=404,
    )

    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/junit-team/junit4/main/Cargo.toml",
        status_code=404,
    )

    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/junit-team/junit4/master/Cargo.toml",
        status_code=404,
    )

    httpx_mock.add_response(
        url="https://raw.githubusercontent.com/junit-team/junit4/main/pom.xml",
        text=pom_xml,
    )

    pkg = detect_package("junit-team", "junit4")

    assert pkg is not None
    assert pkg.system == "maven"
    assert pkg.name == "junit"
    assert pkg.version == "4.13.2"


def test_parse_npm_package_json() -> None:
    from iceberg.detector import parse_npm_package_json

    package_json = """
    {
      "name": "@types/node",
      "version": "20.0.0"
    }
    """

    pkg = parse_npm_package_json(package_json)

    assert pkg is not None
    assert pkg.system == "npm"
    assert pkg.name == "@types/node"
    assert pkg.version == "20.0.0"


def test_parse_pypi_pyproject_toml() -> None:
    from iceberg.detector import parse_pypi_pyproject_toml

    pyproject_toml = """
    [project]
    name = "django"
    version = "4.2.0"
    """

    pkg = parse_pypi_pyproject_toml(pyproject_toml)

    assert pkg is not None
    assert pkg.system == "pypi"
    assert pkg.name == "django"
    assert pkg.version == "4.2.0"


def test_parse_cargo_toml() -> None:
    from iceberg.detector import parse_cargo_toml

    cargo_toml = """
    [package]
    name = "tokio"
    version = "1.28.0"
    """

    pkg = parse_cargo_toml(cargo_toml)

    assert pkg is not None
    assert pkg.system == "cargo"
    assert pkg.name == "tokio"
    assert pkg.version == "1.28.0"


def test_parse_maven_pom_xml() -> None:
    from iceberg.detector import parse_maven_pom_xml

    pom_xml = """
    <?xml version="1.0"?>
    <project>
      <artifactId>spring-boot</artifactId>
      <version>3.0.0</version>
    </project>
    """

    pkg = parse_maven_pom_xml(pom_xml)

    assert pkg is not None
    assert pkg.system == "maven"
    assert pkg.name == "spring-boot"
    assert pkg.version == "3.0.0"
