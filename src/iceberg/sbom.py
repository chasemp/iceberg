import json
import re
from pathlib import Path
from typing import Any, TypedDict

import httpx

from iceberg.calculator import calculate_transitive_loc
from iceberg.detector import fetch_file
from iceberg.models import PackageIdentifier


class AnalysisResult(TypedDict):
    total_dependencies_loc: int
    dependencies: list[dict[str, Any]]


def parse_version_spec(spec: str) -> str:
    """Extract version number from dependency specification."""
    spec = spec.strip()

    version_match = re.search(r'(\d+\.\d+\.\d+)', spec)
    if version_match:
        return version_match.group(1)

    if spec.startswith('^'):
        return spec[1:]
    elif spec.startswith('~'):
        return spec[1:]
    elif spec.startswith('>='):
        return spec[2:]
    elif spec.startswith('=='):
        return spec[2:]

    return spec


def parse_npm_dependencies(content: str) -> list[tuple[str, str]]:
    """Parse dependencies from package.json."""
    try:
        data: Any = json.loads(content)
        dependencies = data.get("dependencies", {})

        result = []
        for name, version_spec in dependencies.items():
            version = parse_version_spec(version_spec)
            result.append((name, version))

        return result
    except Exception:
        return []


def parse_python_dependencies(content: str) -> list[tuple[str, str]]:
    """Parse dependencies from pyproject.toml."""
    try:
        deps_match = re.search(
            r'dependencies\s*=\s*\[(.*?)\]',
            content,
            re.DOTALL
        )

        if not deps_match:
            return []

        deps_str = deps_match.group(1)

        result = []
        for line in deps_str.split(','):
            line = line.strip().strip('"').strip("'")
            if not line:
                continue

            name_match = re.match(r'([a-zA-Z0-9\-_]+)', line)
            if not name_match:
                continue

            name = name_match.group(1)

            version_match = re.search(r'[>=~]+([0-9.]+)', line)
            if version_match:
                version = version_match.group(1)
            else:
                version = "0.0.0"

            result.append((name, version))

        return result
    except Exception:
        return []


def analyze_from_manifest(
    owner: str,
    repo: str,
    cache_dir: Path | None = None,
) -> AnalysisResult | None:
    """Analyze dependencies by reading manifest file directly."""

    package_json = fetch_file(owner, repo, "package.json")
    if package_json:
        deps = parse_npm_dependencies(package_json)
        system = "npm"
    else:
        pyproject_toml = fetch_file(owner, repo, "pyproject.toml")
        if pyproject_toml:
            deps = parse_python_dependencies(pyproject_toml)
            system = "pypi"
        else:
            return None

    if not deps:
        return AnalysisResult(total_dependencies_loc=0, dependencies=[])

    total_loc = 0
    dependency_details = []

    for name, version in deps:
        try:
            pkg = PackageIdentifier(
                system=system,  # type: ignore[arg-type]
                name=name,
                version=version,
            )

            dep_loc = calculate_transitive_loc(pkg, cache_dir=cache_dir)
            total_loc += dep_loc

            dependency_details.append({
                "name": name,
                "version": version,
                "loc": dep_loc,
            })
        except Exception:
            continue

    return AnalysisResult(
        total_dependencies_loc=total_loc,
        dependencies=dependency_details,
    )
