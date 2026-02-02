"""Detect hallmark markers of AI-assisted development in repositories.

This module checks for common files and directories that indicate
the use of AI coding assistants like Claude, Cursor, GitHub Copilot, etc.
"""

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

    # Generic AI markers
    "AI_INSTRUCTIONS.md",
    "AGENTS.md",
    ".ai/",
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
            "generic_ai": False
        }
    """
    markers = {
        "claude": False,
        "cursor": False,
        "copilot": False,
        "aider": False,
        "generic_ai": False,
    }

    # Check Claude markers
    claude_files = ["CLAUDE.md", ".claude/CLAUDE.md", ".clauderc"]
    for filepath in claude_files:
        if check_file_exists(owner, repo, filepath):
            markers["claude"] = True
            break

    # Check Cursor markers
    cursor_files = [".cursor/", ".cursorrules"]
    for filepath in cursor_files:
        if check_file_exists(owner, repo, filepath):
            markers["cursor"] = True
            break

    # Check Copilot markers
    if check_file_exists(owner, repo, ".github/copilot-instructions.md"):
        markers["copilot"] = True

    # Check Aider markers
    aider_files = [".aider/", ".aider.conf.yml"]
    for filepath in aider_files:
        if check_file_exists(owner, repo, filepath):
            markers["aider"] = True
            break

    # Check generic AI markers
    generic_files = ["AI_INSTRUCTIONS.md", "AGENTS.md", ".ai/"]
    for filepath in generic_files:
        if check_file_exists(owner, repo, filepath):
            markers["generic_ai"] = True
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
        "generic_ai": "AI Tools",
    }

    return [tool_names[key] for key, present in markers.items() if present]
