import logging
from typing import Any, cast
from urllib.parse import quote

import httpx

from iceberg.exceptions import DepsDevError
from iceberg.models import PackageIdentifier

logger = logging.getLogger(__name__)


def get_project_loc(owner: str, repo: str) -> int | None:
    try:
        project_id = f"github.com/{owner}/{repo}"
        encoded_id = quote(project_id, safe="")
        url = f"https://api.deps.dev/v3/projects/{encoded_id}"

        logger.debug(f"Fetching project LoC from deps.dev for {owner}/{repo}")
        response = httpx.get(url)
        response.raise_for_status()
        data: Any = response.json()

        line_count = data.get("lineCount")
        if line_count is not None and isinstance(line_count, int):
            logger.debug(f"Got LoC for {owner}/{repo}: {line_count}")
            return cast(int, line_count)
        logger.debug(f"No LoC data available for {owner}/{repo}")
        return None
    except Exception as e:
        logger.error(f"Failed to fetch project LoC for {owner}/{repo}: {e}")
        raise DepsDevError(f"Failed to fetch project LoC for {owner}/{repo}: {e}") from e


def get_dependencies(pkg: PackageIdentifier) -> list[PackageIdentifier]:
    try:
        url = f"https://api.deps.dev/v3/systems/{pkg.system}/packages/{pkg.name}/versions/{pkg.version}:dependencies"

        response = httpx.get(url)
        response.raise_for_status()
        data = response.json()

        deps: list[PackageIdentifier] = []
        dependencies_data = data.get("dependencies", [])

        for dep in dependencies_data:
            package_info = dep.get("package", {})
            system = package_info.get("system")
            name = package_info.get("name")
            version = dep.get("version")

            if system and name and version:
                deps.append(
                    PackageIdentifier(
                        system=system,
                        name=name,
                        version=version,
                    )
                )

        return deps
    except Exception as e:
        raise DepsDevError(f"Failed to fetch dependencies for {pkg.system}:{pkg.name}@{pkg.version}: {e}") from e


def get_package_loc(pkg: PackageIdentifier) -> int | None:
    try:
        url = f"https://api.deps.dev/v3/systems/{pkg.system}/packages/{pkg.name}/versions/{pkg.version}"

        response = httpx.get(url)
        response.raise_for_status()
        data: Any = response.json()

        line_count = data.get("lineCount")
        if line_count is not None and isinstance(line_count, int):
            return cast(int, line_count)
        return None
    except Exception as e:
        raise DepsDevError(f"Failed to fetch package LoC for {pkg.system}:{pkg.name}@{pkg.version}: {e}") from e
