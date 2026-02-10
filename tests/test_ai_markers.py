from pathlib import Path

import pytest

from iceberg.ai_markers import AI_MARKER_FILES

from pytest_httpx import HTTPXMock

TOOL_FILES = {
    "claude": {"CLAUDE.md", ".claude/CLAUDE.md", ".clauderc"},
    "cursor": {".cursor/", ".cursorrules"},
    "copilot": {".github/copilot-instructions.md"},
    "aider": {".aider/", ".aider.conf.yml"},
    "windsurf": {".windsurfrules"},
    "cline": {".clinerules", ".cline/"},
    "codex": {".codex/"},
    "generic_ai": {"AI_INSTRUCTIONS.md", "AGENTS.md", ".ai/", "GEMINI.md"},
}


def _mock_all_404(
    httpx_mock: HTTPXMock,
    owner: str,
    repo: str,
    exclude: set[str] | None = None,
) -> None:
    """Mock all AI marker file checks as 404, optionally excluding specific paths."""
    exclude = exclude or set()
    for filepath in AI_MARKER_FILES:
        if filepath in exclude:
            continue
        for branch in ["main", "master"]:
            httpx_mock.add_response(
                url=f"https://api.github.com/repos/{owner}/{repo}/contents/{filepath}?ref={branch}",
                status_code=404,
            )


@pytest.mark.httpx_mock(can_send_already_matched_responses=True, assert_all_responses_were_requested=False)
def test_detect_claude_markers(httpx_mock: HTTPXMock) -> None:
    from iceberg.ai_markers import detect_ai_markers

    _mock_all_404(httpx_mock, "owner", "repo", exclude=TOOL_FILES["claude"])

    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo/contents/CLAUDE.md?ref=main",
        json={"name": "CLAUDE.md", "type": "file"},
    )

    markers = detect_ai_markers("owner", "repo")

    assert markers["claude"] is True
    assert markers["cursor"] is False
    assert markers["copilot"] is False


@pytest.mark.httpx_mock(can_send_already_matched_responses=True, assert_all_responses_were_requested=False)
def test_detect_cursor_markers(httpx_mock: HTTPXMock) -> None:
    from iceberg.ai_markers import detect_ai_markers

    _mock_all_404(httpx_mock, "owner", "repo", exclude=TOOL_FILES["cursor"])

    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo/contents/.cursor/?ref=main",
        json={"name": ".cursor", "type": "dir"},
    )

    markers = detect_ai_markers("owner", "repo")

    assert markers["cursor"] is True
    assert markers["claude"] is False


def test_detect_no_markers(httpx_mock: HTTPXMock) -> None:
    from iceberg.ai_markers import detect_ai_markers

    _mock_all_404(httpx_mock, "owner", "repo")

    markers = detect_ai_markers("owner", "repo")

    assert markers["claude"] is False
    assert markers["cursor"] is False
    assert markers["copilot"] is False
    assert markers["aider"] is False
    assert markers["windsurf"] is False
    assert markers["cline"] is False
    assert markers["codex"] is False
    assert markers["generic_ai"] is False


def test_has_any_ai_markers() -> None:
    from iceberg.ai_markers import has_any_ai_markers

    assert has_any_ai_markers({"claude": True, "cursor": False}) is True
    assert has_any_ai_markers({"claude": False, "cursor": False}) is False


def test_get_ai_tools_list() -> None:
    from iceberg.ai_markers import get_ai_tools_list

    markers = {
        "claude": True, "cursor": True, "copilot": False,
        "aider": False, "generic_ai": False,
        "windsurf": False, "cline": False, "codex": False,
    }
    tools = get_ai_tools_list(markers)

    assert "Claude" in tools
    assert "Cursor" in tools
    assert "GitHub Copilot" not in tools


@pytest.mark.httpx_mock(can_send_already_matched_responses=True, assert_all_responses_were_requested=False)
def test_detect_windsurf_markers(httpx_mock: HTTPXMock) -> None:
    from iceberg.ai_markers import detect_ai_markers

    _mock_all_404(httpx_mock, "owner", "repo", exclude=TOOL_FILES["windsurf"])

    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo/contents/.windsurfrules?ref=main",
        json={"name": ".windsurfrules", "type": "file"},
    )

    markers = detect_ai_markers("owner", "repo")
    assert markers["windsurf"] is True
    assert markers["claude"] is False


@pytest.mark.httpx_mock(can_send_already_matched_responses=True, assert_all_responses_were_requested=False)
def test_detect_cline_markers(httpx_mock: HTTPXMock) -> None:
    from iceberg.ai_markers import detect_ai_markers

    _mock_all_404(httpx_mock, "owner", "repo", exclude=TOOL_FILES["cline"])

    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo/contents/.clinerules?ref=main",
        json={"name": ".clinerules", "type": "file"},
    )

    markers = detect_ai_markers("owner", "repo")
    assert markers["cline"] is True


@pytest.mark.httpx_mock(can_send_already_matched_responses=True, assert_all_responses_were_requested=False)
def test_detect_codex_markers(httpx_mock: HTTPXMock) -> None:
    from iceberg.ai_markers import detect_ai_markers

    _mock_all_404(httpx_mock, "owner", "repo", exclude=TOOL_FILES["codex"])

    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo/contents/.codex/?ref=main",
        json={"name": ".codex", "type": "dir"},
    )

    markers = detect_ai_markers("owner", "repo")
    assert markers["codex"] is True


def test_get_ai_tools_list_includes_new_tools() -> None:
    from iceberg.ai_markers import get_ai_tools_list

    markers = {
        "claude": False, "cursor": False, "copilot": False,
        "aider": False, "generic_ai": False,
        "windsurf": True, "cline": True, "codex": True,
    }
    tools = get_ai_tools_list(markers)

    assert "Windsurf" in tools
    assert "Cline" in tools
    assert "Codex" in tools
    assert len(tools) == 3


@pytest.mark.httpx_mock(can_send_already_matched_responses=True, assert_all_responses_were_requested=False)
def test_backfill_updates_repos_missing_markers(tmp_path: Path, httpx_mock: HTTPXMock) -> None:
    import json
    from iceberg.ai_markers import backfill_ai_markers

    projects_dir = tmp_path / "projects" / "owner" / "repo"
    projects_dir.mkdir(parents=True)
    head_file = projects_dir / "HEAD.json"
    head_file.write_text(json.dumps({
        "owner": "owner", "repo": "repo", "version": "HEAD", "loc": 5000,
    }))

    _mock_all_404(httpx_mock, "owner", "repo", exclude=TOOL_FILES["claude"])
    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo/contents/CLAUDE.md?ref=main",
        json={"name": "CLAUDE.md", "type": "file"},
    )

    stats = backfill_ai_markers(tmp_path)

    assert stats["total"] == 1
    assert stats["detected"] == 1
    assert stats["skipped"] == 0

    updated = json.loads(head_file.read_text())
    assert updated["ai_markers"]["claude"] is True
    assert "Claude" in updated["ai_tools"]


@pytest.mark.httpx_mock(can_send_already_matched_responses=True, assert_all_responses_were_requested=False)
def test_backfill_skips_repos_with_existing_markers(tmp_path: Path, httpx_mock: HTTPXMock) -> None:
    import json
    from iceberg.ai_markers import backfill_ai_markers

    projects_dir = tmp_path / "projects" / "owner" / "repo"
    projects_dir.mkdir(parents=True)
    head_file = projects_dir / "HEAD.json"
    head_file.write_text(json.dumps({
        "owner": "owner", "repo": "repo", "version": "HEAD", "loc": 5000,
        "ai_markers": {"claude": True}, "ai_tools": ["Claude"],
    }))

    stats = backfill_ai_markers(tmp_path)

    assert stats["total"] == 1
    assert stats["skipped"] == 1
    assert stats["detected"] == 0


@pytest.mark.httpx_mock(can_send_already_matched_responses=True, assert_all_responses_were_requested=False)
def test_backfill_force_reruns_existing(tmp_path: Path, httpx_mock: HTTPXMock) -> None:
    import json
    from iceberg.ai_markers import backfill_ai_markers

    projects_dir = tmp_path / "projects" / "owner" / "repo"
    projects_dir.mkdir(parents=True)
    head_file = projects_dir / "HEAD.json"
    head_file.write_text(json.dumps({
        "owner": "owner", "repo": "repo", "version": "HEAD", "loc": 5000,
        "ai_markers": {"claude": True}, "ai_tools": ["Claude"],
    }))

    _mock_all_404(httpx_mock, "owner", "repo")

    stats = backfill_ai_markers(tmp_path, force=True)

    assert stats["total"] == 1
    assert stats["skipped"] == 0

    updated = json.loads(head_file.read_text())
    assert updated["ai_markers"]["claude"] is False
    assert "ai_tools" not in updated
