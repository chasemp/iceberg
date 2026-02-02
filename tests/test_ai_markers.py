from pytest_httpx import HTTPXMock


def test_detect_claude_markers(httpx_mock: HTTPXMock) -> None:
    from iceberg.ai_markers import detect_ai_markers

    # Mock CLAUDE.md exists
    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo/contents/CLAUDE.md?ref=main",
        json={"name": "CLAUDE.md", "type": "file"},
    )

    # Mock all other files as 404
    for path in [".cursor/", ".cursorrules", ".github/copilot-instructions.md",
                 ".aider/", ".aider.conf.yml", "AI_INSTRUCTIONS.md", "AGENTS.md", ".ai/"]:
        for branch in ["main", "master"]:
            httpx_mock.add_response(
                url=f"https://api.github.com/repos/owner/repo/contents/{path}?ref={branch}",
                status_code=404,
            )

    markers = detect_ai_markers("owner", "repo")

    assert markers["claude"] is True
    assert markers["cursor"] is False
    assert markers["copilot"] is False


def test_detect_cursor_markers(httpx_mock: HTTPXMock) -> None:
    from iceberg.ai_markers import detect_ai_markers

    # Mock all Claude markers as 404
    for path in ["CLAUDE.md", ".claude/CLAUDE.md", ".clauderc"]:
        for branch in ["main", "master"]:
            httpx_mock.add_response(
                url=f"https://api.github.com/repos/owner/repo/contents/{path}?ref={branch}",
                status_code=404,
            )

    # Mock .cursor/ exists (will break after finding this)
    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo/contents/.cursor/?ref=main",
        json={"name": ".cursor", "type": "dir"},
    )

    # Mock remaining markers as 404 (note: .cursorrules won't be checked since .cursor/ breaks the loop)
    for path in [".github/copilot-instructions.md",
                 ".aider/", ".aider.conf.yml", "AI_INSTRUCTIONS.md", "AGENTS.md", ".ai/"]:
        for branch in ["main", "master"]:
            httpx_mock.add_response(
                url=f"https://api.github.com/repos/owner/repo/contents/{path}?ref={branch}",
                status_code=404,
            )

    markers = detect_ai_markers("owner", "repo")

    assert markers["cursor"] is True
    assert markers["claude"] is False


def test_detect_no_markers(httpx_mock: HTTPXMock) -> None:
    from iceberg.ai_markers import detect_ai_markers

    # Mock all files as 404
    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo/contents/CLAUDE.md?ref=main",
        status_code=404,
    )
    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo/contents/CLAUDE.md?ref=master",
        status_code=404,
    )
    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo/contents/.claude/CLAUDE.md?ref=main",
        status_code=404,
    )
    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo/contents/.claude/CLAUDE.md?ref=master",
        status_code=404,
    )
    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo/contents/.clauderc?ref=main",
        status_code=404,
    )
    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo/contents/.clauderc?ref=master",
        status_code=404,
    )
    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo/contents/.cursor/?ref=main",
        status_code=404,
    )
    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo/contents/.cursor/?ref=master",
        status_code=404,
    )
    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo/contents/.cursorrules?ref=main",
        status_code=404,
    )
    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo/contents/.cursorrules?ref=master",
        status_code=404,
    )
    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo/contents/.github/copilot-instructions.md?ref=main",
        status_code=404,
    )
    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo/contents/.github/copilot-instructions.md?ref=master",
        status_code=404,
    )
    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo/contents/.aider/?ref=main",
        status_code=404,
    )
    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo/contents/.aider/?ref=master",
        status_code=404,
    )
    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo/contents/.aider.conf.yml?ref=main",
        status_code=404,
    )
    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo/contents/.aider.conf.yml?ref=master",
        status_code=404,
    )
    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo/contents/AI_INSTRUCTIONS.md?ref=main",
        status_code=404,
    )
    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo/contents/AI_INSTRUCTIONS.md?ref=master",
        status_code=404,
    )
    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo/contents/AGENTS.md?ref=main",
        status_code=404,
    )
    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo/contents/AGENTS.md?ref=master",
        status_code=404,
    )
    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo/contents/.ai/?ref=main",
        status_code=404,
    )
    httpx_mock.add_response(
        url="https://api.github.com/repos/owner/repo/contents/.ai/?ref=master",
        status_code=404,
    )

    markers = detect_ai_markers("owner", "repo")

    assert markers["claude"] is False
    assert markers["cursor"] is False
    assert markers["copilot"] is False
    assert markers["aider"] is False
    assert markers["generic_ai"] is False


def test_has_any_ai_markers() -> None:
    from iceberg.ai_markers import has_any_ai_markers

    assert has_any_ai_markers({"claude": True, "cursor": False}) is True
    assert has_any_ai_markers({"claude": False, "cursor": False}) is False


def test_get_ai_tools_list() -> None:
    from iceberg.ai_markers import get_ai_tools_list

    markers = {"claude": True, "cursor": True, "copilot": False, "aider": False, "generic_ai": False}
    tools = get_ai_tools_list(markers)

    assert "Claude" in tools
    assert "Cursor" in tools
    assert "GitHub Copilot" not in tools
