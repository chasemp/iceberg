# Iceberg

> The code you see is just the tip of the iceberg

Visualize the FLOSS "iceberg effect" - showing how dependencies make up the bulk of modern codebases.

## Installation

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/chasemp/iceberg.git
cd iceberg

# Install dependencies
uv sync

# The CLI is now available
uv run iceberg --help
```

## Usage

### Fetch Trending Repositories

```bash
# Fetch top 10 trending repos
uv run iceberg fetch

# Fetch top 5 trending repos
uv run iceberg fetch --limit 5

# Output as JSON
uv run iceberg fetch --json
```

### Analyze Repository Dependencies

```bash
# Analyze a repository's dependency footprint
uv run iceberg analyze facebook/react --package npm:react:18.2.0

# Output as JSON
uv run iceberg analyze facebook/react --package npm:react:18.2.0 --json
```

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_cli.py
```

### Type Checking

```bash
# Run mypy strict type checking
uv run mypy --strict src/
```

## Architecture

- **models.py**: Immutable Pydantic domain models
- **github.py**: GitHub trending page scraper
- **depsdev.py**: deps.dev API client
- **cache.py**: JSON-based caching layer
- **calculator.py**: Transitive dependency LoC calculation
- **cli.py**: Typer CLI interface

## Cache

Data is cached in the `cache/` directory:
- `cache/trending/`: Daily trending repos
- `cache/loc/`: Package LoC metrics
- `cache/dependencies/`: Package dependency graphs

## Technology Stack

- **Python 3.12**: Modern Python with strict type hints
- **uv**: Fast Python package manager
- **Pydantic**: Data validation and serialization
- **Typer**: Type-driven CLI framework
- **httpx**: Modern HTTP client
- **BeautifulSoup4**: HTML parsing
- **pytest**: Testing framework

## License

MIT
