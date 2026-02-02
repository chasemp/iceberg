import json
from pathlib import Path

from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from tests.factories import create_trending_repo


def test_fetch_command_fetches_and_caches(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    from iceberg.cli import app

    html = """
    <article class="Box-row">
      <h2 class="h3 lh-condensed">
        <a href="/owner/repo">
          <span class="text-normal">owner /</span>
          repo
        </a>
      </h2>
      <p class="col-9 color-fg-muted my-1 pr-4">Test description</p>
      <div class="f6 color-fg-muted mt-2">
        <span class="d-inline-block ml-0 mr-3">
          <span itemprop="programmingLanguage">Python</span>
        </span>
        <span class="d-inline-block mr-3">
          <svg aria-label="star"></svg>
          1,234
        </span>
      </div>
    </article>
    """

    httpx_mock.add_response(
        url="https://github.com/trending",
        text=html,
    )

    runner = CliRunner()
    result = runner.invoke(app, ["fetch", "--cache-dir", str(tmp_path)])

    assert result.exit_code == 0
    assert "Fetched 1 daily trending" in result.stdout


def test_fetch_command_respects_limit(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    from iceberg.cli import app

    html = """
    <article class="Box-row">
      <h2 class="h3 lh-condensed">
        <a href="/owner1/repo1"><span class="text-normal">owner1 /</span>repo1</a>
      </h2>
      <div class="f6 color-fg-muted mt-2">
        <span class="d-inline-block mr-3"><svg aria-label="star"></svg>100</span>
      </div>
    </article>
    <article class="Box-row">
      <h2 class="h3 lh-condensed">
        <a href="/owner2/repo2"><span class="text-normal">owner2 /</span>repo2</a>
      </h2>
      <div class="f6 color-fg-muted mt-2">
        <span class="d-inline-block mr-3"><svg aria-label="star"></svg>200</span>
      </div>
    </article>
    """

    httpx_mock.add_response(
        url="https://github.com/trending",
        text=html,
    )

    runner = CliRunner()
    result = runner.invoke(app, ["fetch", "--limit", "1", "--cache-dir", str(tmp_path)])

    assert result.exit_code == 0
    assert "Fetched 1 daily trending" in result.stdout


def test_fetch_command_json_output(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    from iceberg.cli import app

    html = """
    <article class="Box-row">
      <h2 class="h3 lh-condensed">
        <a href="/owner/repo">
          <span class="text-normal">owner /</span>
          repo
        </a>
      </h2>
      <div class="f6 color-fg-muted mt-2">
        <span class="d-inline-block mr-3"><svg aria-label="star"></svg>100</span>
      </div>
    </article>
    """

    httpx_mock.add_response(
        url="https://github.com/trending",
        text=html,
    )

    runner = CliRunner()
    result = runner.invoke(app, ["fetch", "--json", "--cache-dir", str(tmp_path)])

    assert result.exit_code == 0

    output = json.loads(result.stdout)
    assert len(output) == 1
    assert output[0]["name"] == "repo"
    assert output[0]["owner"] == "owner"


def test_analyze_command_calculates_loc(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    from iceberg.cli import app

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/projects/github.com%2Fowner%2Frepo",
        json={"lineCount": 5000},
    )

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/repo/versions/1.0.0",
        json={"lineCount": 1000},
    )

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/repo/versions/1.0.0:dependencies",
        json={"dependencies": []},
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["analyze", "owner/repo", "--package", "npm:repo:1.0.0", "--cache-dir", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "Project LoC:" in result.stdout
    assert "5,000" in result.stdout


def test_analyze_command_json_output(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    from iceberg.cli import app

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/projects/github.com%2Fowner%2Frepo",
        json={"lineCount": 5000},
    )

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/repo/versions/1.0.0",
        json={"lineCount": 5000},
    )

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/repo/versions/1.0.0:dependencies",
        json={
            "dependencies": [
                {
                    "requirement": "^1.0.0",
                    "package": {"system": "npm", "name": "dep1"},
                    "version": "1.0.0",
                }
            ]
        },
    )

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/dep1/versions/1.0.0",
        json={"lineCount": 100},
    )

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/dep1/versions/1.0.0:dependencies",
        json={"dependencies": []},
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "analyze",
            "owner/repo",
            "--package",
            "npm:repo:1.0.0",
            "--json",
            "--cache-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0

    output = json.loads(result.stdout)
    assert output["repo"] == "owner/repo"
    assert output["project_loc"] == 5000
    assert output["total_loc"] == 5100


def test_analyze_command_handles_missing_project_loc(
    httpx_mock: HTTPXMock, tmp_path: Path
) -> None:
    """Test analyzing a package when project LoC is missing (using --head to skip clone)."""
    from iceberg.cli import app

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/projects/github.com%2Fowner%2Frepo",
        json={},
    )

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/repo/versions/1.0.0",
        json={"lineCount": 1000},
    )

    httpx_mock.add_response(
        url="https://api.deps.dev/v3/systems/npm/packages/repo/versions/1.0.0:dependencies",
        json={"dependencies": []},
    )

    runner = CliRunner()
    # Use --head flag to skip published version detection and clone (would require git)
    result = runner.invoke(
        app,
        ["analyze", "owner/repo", "--package", "npm:repo:1.0.0", "--cache-dir", str(tmp_path), "--head"],
    )

    assert result.exit_code == 0


def test_fetch_command_with_weekly_timeframe(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    from iceberg.cli import app

    html = """
    <article class="Box-row">
      <h2 class="h3 lh-condensed">
        <a href="/owner/repo">repo</a>
      </h2>
      <div class="f6 color-fg-muted mt-2">
        <span class="d-inline-block mr-3"><svg aria-label="star"></svg>1000</span>
      </div>
    </article>
    """

    httpx_mock.add_response(
        url="https://github.com/trending?since=weekly",
        text=html,
    )

    runner = CliRunner()
    result = runner.invoke(app, ["fetch", "--source", "trending", "--since", "weekly", "--cache-dir", str(tmp_path)])

    assert result.exit_code == 0
    assert "Fetched 1 weekly trending" in result.stdout


def test_fetch_command_with_search_source(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    from iceberg.cli import app

    httpx_mock.add_response(
        url="https://api.github.com/search/repositories?q=stars%3A%3E10000&per_page=10&page=1",
        json={
            "items": [
                {
                    "name": "react",
                    "owner": {"login": "facebook"},
                    "html_url": "https://github.com/facebook/react",
                    "description": "A JavaScript library",
                    "language": "JavaScript",
                    "stargazers_count": 220000,
                }
            ]
        },
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["fetch", "--source", "search", "--stars", ">10000", "--limit", "10", "--cache-dir", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "Fetched 1 repositories from search" in result.stdout
    assert "Query: stars:>10000" in result.stdout


def test_fetch_command_with_custom_search_query(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    from iceberg.cli import app

    httpx_mock.add_response(
        url="https://api.github.com/search/repositories?q=language%3Apython+stars%3A%3E5000&per_page=10&page=1",
        json={
            "items": [
                {
                    "name": "requests",
                    "owner": {"login": "psf"},
                    "html_url": "https://github.com/psf/requests",
                    "description": "HTTP library",
                    "language": "Python",
                    "stargazers_count": 50000,
                }
            ]
        },
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["fetch", "--source", "search", "--query", "language:python stars:>5000", "--cache-dir", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "Fetched 1 repositories from search" in result.stdout
    assert "Query: language:python stars:>5000" in result.stdout
