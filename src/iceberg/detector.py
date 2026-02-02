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


def parse_go_mod(content: str, owner: str, repo: str) -> PackageIdentifier | None:
    """Parse Go go.mod file.

    Note: Go modules don't have explicit versions in go.mod.
    Uses v0.0.0 as default version (can be improved to fetch from Git tags).
    """
    try:
        module_match = re.search(r'module\s+(\S+)', content)

        if module_match:
            module_path = module_match.group(1)

            return PackageIdentifier(
                system="go",
                name=module_path,
                version="v0.0.0",  # Default version
            )
    except Exception:
        pass
    return None


def detect_package(owner: str, repo: str) -> PackageIdentifier | None:
    """Detect package ecosystem and extract package identifier."""

    # Try npm
    content = fetch_file(owner, repo, "package.json")
    if content:
        pkg = parse_npm_package_json(content)
        if pkg:
            return pkg

    # Try Python
    content = fetch_file(owner, repo, "pyproject.toml")
    if content:
        pkg = parse_pypi_pyproject_toml(content)
        if pkg:
            return pkg

    # Try Rust
    content = fetch_file(owner, repo, "Cargo.toml")
    if content:
        pkg = parse_cargo_toml(content)
        if pkg:
            return pkg

    # Try Maven
    content = fetch_file(owner, repo, "pom.xml")
    if content:
        pkg = parse_maven_pom_xml(content)
        if pkg:
            return pkg

    # Try Go
    content = fetch_file(owner, repo, "go.mod")
    if content:
        pkg = parse_go_mod(content, owner, repo)
        if pkg:
            return pkg

    return None
