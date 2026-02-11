#!/usr/bin/env python3
"""Run discovery via the iceberg CLI.

Thin wrapper that calls `iceberg discover`. Prefer using the CLI directly:
    iceberg discover -v

Usage:
    python scripts/run_discovery.py
    python scripts/run_discovery.py --verbose
"""

import subprocess
import sys


def main() -> int:
    verbose = "-v" in sys.argv or "--verbose" in sys.argv

    cmd = ["iceberg", "discover"]
    if verbose:
        cmd.append("-v")

    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
