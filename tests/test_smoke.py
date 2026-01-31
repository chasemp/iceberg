def test_imports_work() -> None:
    import pydantic
    import typer
    import httpx
    import bs4
    import pytest

    assert pydantic is not None
    assert typer is not None
    assert httpx is not None
    assert bs4 is not None
    assert pytest is not None
