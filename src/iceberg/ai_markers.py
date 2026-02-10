"""Detect hallmark markers of AI-assisted development in repositories.

This module checks for common files and directories that indicate
the use of AI coding assistants like Claude, Cursor, GitHub Copilot, etc.
"""

import json
from pathlib import Path
from typing import Any

import httpx


AI_MARKER_FILES = [
    # Claude Code
    "CLAUDE.md",
    ".claude/CLAUDE.md",
    ".clauderc",

    # Cursor
    ".cursor/",
    ".cursorrules",

    # GitHub Copilot
    ".github/copilot-instructions.md",

    # Aider
    ".aider/",
    ".aider.conf.yml",

    # Windsurf
    ".windsurfrules",

    # Cline
    ".clinerules",
    ".cline/",

    # OpenAI Codex
    ".codex/",

    # Generic AI markers
    "AI_INSTRUCTIONS.md",
    "AGENTS.md",
    ".ai/",
    "GEMINI.md",
]


def check_file_exists(owner: str, repo: str, filepath: str) -> bool:
    """Check if a file exists in a GitHub repository.

    Args:
        owner: Repository owner
        repo: Repository name
        filepath: Path to check (e.g., "CLAUDE.md" or ".claude/")

    Returns:
        True if file/directory exists, False otherwise
    """
    for branch in ["main", "master"]:
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{filepath}?ref={branch}"
        try:
            response = httpx.get(url, timeout=5.0)
            if response.status_code == 200:
                return True
        except Exception:
            continue
    return False


def detect_ai_markers(owner: str, repo: str) -> dict[str, bool]:
    """Detect which AI development markers are present in a repository.

    Args:
        owner: Repository owner
        repo: Repository name

    Returns:
        Dictionary mapping marker names to presence (True/False)

    Example:
        {
            "claude": True,
            "cursor": False,
            "copilot": False,
            "aider": False,
            "windsurf": False,
            "cline": False,
            "codex": False,
            "generic_ai": False
        }
    """
    markers = {
        "claude": False,
        "cursor": False,
        "copilot": False,
        "aider": False,
        "windsurf": False,
        "cline": False,
        "codex": False,
        "generic_ai": False,
    }

    tool_files: dict[str, list[str]] = {
        "claude": ["CLAUDE.md", ".claude/CLAUDE.md", ".clauderc"],
        "cursor": [".cursor/", ".cursorrules"],
        "copilot": [".github/copilot-instructions.md"],
        "aider": [".aider/", ".aider.conf.yml"],
        "windsurf": [".windsurfrules"],
        "cline": [".clinerules", ".cline/"],
        "codex": [".codex/"],
        "generic_ai": ["AI_INSTRUCTIONS.md", "AGENTS.md", ".ai/", "GEMINI.md"],
    }

    for tool, filepaths in tool_files.items():
        for filepath in filepaths:
            if check_file_exists(owner, repo, filepath):
                markers[tool] = True
                break

    return markers


def has_any_ai_markers(markers: dict[str, bool]) -> bool:
    """Check if any AI markers were detected.

    Args:
        markers: Dictionary from detect_ai_markers()

    Returns:
        True if any AI marker is present, False otherwise
    """
    return any(markers.values())


def get_ai_tools_list(markers: dict[str, bool]) -> list[str]:
    """Get list of detected AI tool names.

    Args:
        markers: Dictionary from detect_ai_markers()

    Returns:
        List of tool names (e.g., ["Claude", "Cursor"])
    """
    tool_names = {
        "claude": "Claude",
        "cursor": "Cursor",
        "copilot": "GitHub Copilot",
        "aider": "Aider",
        "windsurf": "Windsurf",
        "cline": "Cline",
        "codex": "Codex",
        "generic_ai": "AI Tools",
    }

    return [tool_names[key] for key, present in markers.items() if present and key in tool_names]


def backfill_ai_markers(
    cache_dir: Path,
    force: bool = False,
    verbose: bool = False,
) -> dict[str, Any]:
    """Backfill AI marker detection for repos missing it.

    Scans all analysis files in cache/projects/ and runs AI marker
    detection for any that don't have ai_markers data.

    Args:
        cache_dir: Path to cache directory
        force: If True, re-run detection even for repos that already have markers
        verbose: If True, print progress

    Returns:
        Dictionary with stats: total, skipped, detected, errors
    """
    projects_dir = cache_dir / "projects"
    if not projects_dir.exists():
        return {"total": 0, "skipped": 0, "detected": 0, "errors": 0}

    stats: dict[str, int] = {"total": 0, "skipped": 0, "detected": 0, "errors": 0}

    for head_file in projects_dir.rglob("HEAD.json"):
        stats["total"] += 1

        try:
            data = json.loads(head_file.read_text())
        except (json.JSONDecodeError, IOError):
            stats["errors"] += 1
            continue

        owner = data.get("owner", "")
        repo = data.get("repo", "")

        if not owner or not repo:
            stats["errors"] += 1
            continue

        if not force and "ai_markers" in data:
            stats["skipped"] += 1
            if verbose:
                tools = data.get("ai_tools", [])
                label = f" ({', '.join(tools)})" if tools else ""
                print(f"  [skip] {owner}/{repo}{label}")
            continue

        if verbose:
            print(f"  [scan] {owner}/{repo}")

        try:
            markers = detect_ai_markers(owner, repo)
            data["ai_markers"] = markers

            if has_any_ai_markers(markers):
                tools = get_ai_tools_list(markers)
                data["ai_tools"] = tools
                stats["detected"] += 1
                if verbose:
                    print(f"         -> {', '.join(tools)}")
            else:
                data.pop("ai_tools", None)
                if verbose:
                    print(f"         -> none")

            head_file.write_text(json.dumps(data, indent=2))

        except Exception as e:
            stats["errors"] += 1
            if verbose:
                print(f"         -> error: {e}")

    return stats
