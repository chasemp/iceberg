import json
import re
from typing import Any

import httpx

from iceberg.models import PackageIdentifier


def fetch_file(owner: str, repo: str, filename: str) -> str | None:
    """Fetch a file from GitHub raw content."""
    for branch in ["main", "master"]:
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{filename}"
        try:
            response = httpx.get(url, timeout=10.0)
            if response.status_code == 200:
                return response.text
        except Exception:
            continue
    return None


def parse_npm_package_json(content: str) -> PackageIdentifier | None:
    """Parse npm package.json file."""
    try:
        data: Any = json.loads(content)
        name = data.get("name")
        version = data.get("version")

        if name and version:
            return PackageIdentifier(
                system="npm",
                name=name,
                version=version,
            )
    except Exception:
        pass
    return None


def parse_pypi_pyproject_toml(content: str) -> PackageIdentifier | None:
    """Parse Python pyproject.toml file."""
    try:
        name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
        version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)

        if name_match and version_match:
            return PackageIdentifier(
                system="pypi",
                name=name_match.group(1),
                version=version_match.group(1),
            )
    except Exception:
        pass
    return None


def parse_cargo_toml(content: str) -> PackageIdentifier | None:
    """Parse Rust Cargo.toml file."""
    try:
        in_package_section = False
        name = None
        version = None

        for line in content.split('\n'):
            line = line.strip()

            if line == '[package]':
                in_package_section = True
                continue

            if line.startswith('[') and line != '[package]':
                in_package_section = False
                continue

            if in_package_section:
                name_match = re.match(r'name\s*=\s*["\']([^"\']+)["\']', line)
                if name_match:
                    name = name_match.group(1)

                version_match = re.match(r'version\s*=\s*["\']([^"\']+)["\']', line)
                if version_match:
                    version = version_match.group(1)

        if name and version:
            return PackageIdentifier(
                system="cargo",
                name=name,
                version=version,
            )
    except Exception:
        pass
    return None


def parse_maven_pom_xml(content: str) -> PackageIdentifier | None:
    """Parse Maven pom.xml file."""
    try:
        artifact_match = re.search(r'<artifactId>([^<]+)</artifactId>', content)
        version_match = re.search(r'<version>([^<]+)</version>', content)

        if artifact_match and version_match:
            return PackageIdentifier(
                system="maven",
                name=artifact_match.group(1),
                version=version_match.group(1),
            )
    except Exception:
        pass
    return None


def detect_package(owner: str, repo: str) -> PackageIdentifier | None:
    """Detect package ecosystem and extract package identifier."""

    detectors = [
        ("package.json", parse_npm_package_json),
        ("pyproject.toml", parse_pypi_pyproject_toml),
        ("Cargo.toml", parse_cargo_toml),
        ("pom.xml", parse_maven_pom_xml),
    ]

    for filename, parser in detectors:
        content = fetch_file(owner, repo, filename)
        if content:
            pkg = parser(content)
            if pkg:
                return pkg

    return None
