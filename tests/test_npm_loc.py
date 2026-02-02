from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock


def test_fetch_npm_package_tarball(httpx_mock: HTTPXMock) -> None:
    """Test fetching package tarball from npm registry."""
    from iceberg.npm_loc import fetch_npm_tarball

    # Mock npm registry response
    httpx_mock.add_response(
        url="https://registry.npmjs.org/lodash/4.17.21",
        json={
            "dist": {
                "tarball": "https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz"
            }
        },
    )

    # Mock tarball download (simplified - just return some bytes)
    httpx_mock.add_response(
        url="https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz",
        content=b"fake tarball content",
    )

    tarball_data = fetch_npm_tarball("lodash", "4.17.21")

    assert tarball_data is not None
    assert len(tarball_data) > 0


def test_count_loc_in_tarball(tmp_path: Path) -> None:
    """Test counting LoC from extracted tarball."""
    from iceberg.npm_loc import count_loc_in_directory

    # Create test files
    js_file = tmp_path / "index.js"
    js_file.write_text("""
// Comment
function test() {
    return 42;
}
module.exports = test;
""")

    another_file = tmp_path / "utils.js"
    another_file.write_text("const x = 1;\nconst y = 2;\n")

    loc = count_loc_in_directory(tmp_path)

    # Should count actual code lines (excluding comments and blank lines)
    assert loc > 0


def test_get_npm_package_loc(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    """Test full flow of getting LoC from npm package."""
    from iceberg.npm_loc import get_npm_package_loc

    # Mock registry
    httpx_mock.add_response(
        url="https://registry.npmjs.org/test-pkg/1.0.0",
        json={
            "dist": {
                "tarball": "https://registry.npmjs.org/test-pkg/-/test-pkg-1.0.0.tgz"
            }
        },
    )

    # Mock tarball with actual tar.gz content (minimal)
    import io
    import tarfile

    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode='w:gz') as tar:
        # Create a simple file
        file_data = b"function test() { return 42; }\n"
        file_info = tarfile.TarInfo(name="package/index.js")
        file_info.size = len(file_data)
        tar.addfile(file_info, io.BytesIO(file_data))

    httpx_mock.add_response(
        url="https://registry.npmjs.org/test-pkg/-/test-pkg-1.0.0.tgz",
        content=tar_buffer.getvalue(),
    )

    result = get_npm_package_loc("test-pkg", "1.0.0", cache_dir=tmp_path)

    assert result is not None
    assert result["loc"] > 0
    assert result["source"] == "npm_tarball"
    assert "tarball_url" in result["metadata"]


def test_get_npm_package_loc_handles_network_error(
    httpx_mock: HTTPXMock, tmp_path: Path
) -> None:
    """Test graceful handling of network errors."""
    from iceberg.npm_loc import get_npm_package_loc

    httpx_mock.add_exception(Exception("Network error"))

    result = get_npm_package_loc("test-pkg", "1.0.0", cache_dir=tmp_path)

    assert result is None


def test_enhanced_loc_metrics_with_metadata() -> None:
    """Test that LocMetrics stores comprehensive metadata."""
    from iceberg.models import LocMetrics, PackageIdentifier

    pkg = PackageIdentifier(system="npm", name="test", version="1.0.0")

    metrics = LocMetrics(
        package=pkg,
        total_lines=1000,
        source="npm_tarball",
        cached_at="2026-02-02T12:00:00Z",
        source_url="https://registry.npmjs.org/test/-/test-1.0.0.tgz",
        fetch_method="tarball_download_and_count",
    )

    assert metrics.source == "npm_tarball"
    assert metrics.source_url == "https://registry.npmjs.org/test/-/test-1.0.0.tgz"
    assert metrics.fetch_method == "tarball_download_and_count"
