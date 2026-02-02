import io
import tarfile
import tempfile
from pathlib import Path
from typing import Any

import httpx


def fetch_npm_tarball(name: str, version: str) -> bytes | None:
    """Fetch package tarball from npm registry."""
    try:
        # Get package metadata
        metadata_url = f"https://registry.npmjs.org/{name}/{version}"
        response = httpx.get(metadata_url, timeout=10.0)
        response.raise_for_status()

        data: Any = response.json()
        tarball_url = data.get("dist", {}).get("tarball")

        if not tarball_url:
            return None

        # Download tarball
        tarball_response = httpx.get(tarball_url, timeout=30.0)
        tarball_response.raise_for_status()

        return tarball_response.content
    except Exception:
        return None


def count_loc_in_directory(directory: Path) -> int:
    """Count lines of code in a directory (simple implementation)."""
    total_lines = 0

    # Common code file extensions
    code_extensions = {
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".mjs",
        ".cjs",
        ".py",
        ".rs",
        ".go",
        ".java",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
    }

    for file_path in directory.rglob("*"):
        if file_path.is_file() and file_path.suffix in code_extensions:
            try:
                # Skip node_modules, tests, and build directories
                if any(
                    part in ["node_modules", "test", "tests", "__tests__", "dist", "build"]
                    for part in file_path.parts
                ):
                    continue

                content = file_path.read_text(errors="ignore")
                lines = content.split("\n")

                # Count non-empty, non-comment lines (simple heuristic)
                for line in lines:
                    stripped = line.strip()
                    if stripped and not stripped.startswith(("//", "#", "/*", "*")):
                        total_lines += 1
            except Exception:
                continue

    return total_lines


def get_npm_package_loc(
    name: str,
    version: str,
    cache_dir: Path | None = None,
) -> dict[str, Any] | None:
    """Get LoC for an npm package by downloading and analyzing it."""
    try:
        tarball_data = fetch_npm_tarball(name, version)
        if not tarball_data:
            return None

        # Extract tarball to temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Extract tarball
            with tarfile.open(fileobj=io.BytesIO(tarball_data), mode="r:gz") as tar:
                # Security: only extract safe files
                for member in tar.getmembers():
                    if member.name.startswith("/") or ".." in member.name:
                        continue
                    tar.extract(member, temp_path)

            # Count LoC
            loc = count_loc_in_directory(temp_path)

            tarball_url = f"https://registry.npmjs.org/{name}/-/{name}-{version}.tgz"

            return {
                "loc": loc,
                "source": "npm_tarball",
                "metadata": {
                    "tarball_url": tarball_url,
                    "package": f"{name}@{version}",
                },
            }
    except Exception:
        return None
