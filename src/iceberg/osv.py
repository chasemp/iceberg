import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from iceberg.models import PackageIdentifier


ECOSYSTEM_MAP = {
    "npm": "npm",
    "PyPI": "pypi",
    "pypi": "pypi",
    "crates.io": "cargo",
    "Maven": "maven",
}


def parse_osv_sbom(osv_output: str) -> list[PackageIdentifier]:
    """Parse OSV-Scanner JSON output and extract dependencies."""
    try:
        data: Any = json.loads(osv_output)
        results = data.get("results", [])

        packages = []
        for result in results:
            for pkg_entry in result.get("packages", []):
                pkg_info = pkg_entry.get("package", {})

                name = pkg_info.get("name")
                version = pkg_info.get("version")
                ecosystem = pkg_info.get("ecosystem")

                if not all([name, version, ecosystem]):
                    continue

                mapped_ecosystem = ECOSYSTEM_MAP.get(ecosystem, ecosystem)

                if mapped_ecosystem in ["npm", "pypi", "cargo", "maven"]:
                    packages.append(
                        PackageIdentifier(
                            system=mapped_ecosystem,
                            name=name,
                            version=version,
                        )
                    )

        return packages
    except Exception:
        return []


def run_osv_scanner(repo_path: Path) -> str | None:
    """Run osv-scanner on a repository and return JSON output."""
    if not shutil.which("osv-scanner"):
        return None

    try:
        result = subprocess.run(
            [
                "osv-scanner",
                "scan",
                "source",
                "--format=json",
                "-r",
                str(repo_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # OSV-Scanner returns non-zero if vulnerabilities found
        # We still want the output
        return result.stdout if result.stdout else None
    except Exception:
        return None


def analyze_with_osv(
    repo_path: str,
    loc_calculator: Any,
    cache_dir: Path | None = None,
) -> dict[str, Any] | None:
    """Analyze dependencies using OSV-Scanner.

    Args:
        repo_path: Path to repository
        loc_calculator: Function to calculate LoC for a package (signature: (PackageIdentifier, cache_dir) -> int)
        cache_dir: Cache directory
    """
    path = Path(repo_path)

    osv_output = run_osv_scanner(path)
    if not osv_output:
        return None

    deps = parse_osv_sbom(osv_output)
    if not deps:
        return None

    total_loc = 0
    dependency_details = []

    for pkg in deps:
        try:
            dep_loc = loc_calculator(pkg, cache_dir=cache_dir)
            total_loc += dep_loc

            dependency_details.append({
                "name": pkg.name,
                "version": pkg.version,
                "system": pkg.system,
                "loc": dep_loc,
            })
        except Exception:
            continue

    return {
        "total_dependencies_loc": total_loc,
        "dependencies": dependency_details,
        "source": "osv-scanner",
    }
