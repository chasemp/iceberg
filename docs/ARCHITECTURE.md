# Iceberg Architecture

## Overview

Iceberg uses three workflow streams to manage repository data:

```
+-----------------+     +-----------------+     +-----------------+
|    DISCOVER     | --> |     ANALYZE     | --> |     PUBLISH     |
|   (Weekly)      |     |    (Daily)      |     |  (After analyze)|
+-----------------+     +-----------------+     +-----------------+
| Trending        |     | Check staleness |     | Export to SPA   |
| Search          |     | Prioritize      |     | Deploy Pages    |
| GitHub-Ranking  |     | Analyze batch   |     |                 |
| Deduplicate     |     | Rate limit      |     |                 |
| Save metadata   |     | Save results    |     |                 |
+-----------------+     +-----------------+     +-----------------+
```

## Data Flow

### 1. Discovery (Entry Point)

**Input:** GitHub Trending, Search API, GitHub-Ranking
**Output:** Repo metadata in `cache/repos/{owner}/{repo}.json`

```bash
iceberg discover -v
```

Each repo gets a metadata file with discovery sources as categories:
```json
{
  "owner": "facebook",
  "name": "react",
  "stars": 242901,
  "language": "JavaScript",
  "categories": {
    "search": "2026-02-10",
    "github-ranking-top-100-stars": "2026-02-09",
    "github-ranking-javascript": "2026-02-09",
    "tracked": "2026-02-11"
  },
  "last_discovered": "2026-02-10"
}
```

### 2. Tracking (Manual Curation)

Tracking is just another category. When you run `iceberg track owner/repo`, it adds `"tracked": "<date>"` to the repo's categories.

```bash
iceberg track facebook/react    # Adds "tracked" category
iceberg list-tracked             # Lists repos with "tracked" category
iceberg untrack facebook/react   # Removes "tracked" category
```

No separate tracking file. Everything lives in `cache/repos/`.

### 3. Analysis (Keep Fresh)

**Input:** All repos from `cache/repos/`
**Output:** Analysis in `cache/projects/{owner}/{repo}/HEAD.json`

```bash
iceberg run-analysis --batch-size 25 -v
iceberg run-analysis --force --batch-size 10 -v
```

Staleness is determined by tier (configured in `config/staleness.json`):

| Tier | Condition | Max Age |
|------|-----------|---------|
| Tracked | has "tracked" category | 24 hours |
| Popular | stars >= 10,000 | 7 days |
| Regular | everything else | 30 days |

### 4. Publish (Deploy)

**Input:** Cache data
**Output:** SPA-ready JSON in `spa/data/`

```bash
iceberg export
```

## Cache Structure

```
cache/
+-- discovered/              # Discovery snapshots by source
|   +-- trending-monthly/
|   |   +-- 2026-02-10.json
|   +-- search/
|       +-- abc123.json
|
+-- repos/                   # Repo metadata (one file per repo)
|   +-- facebook/
|   |   +-- react.json       # Categories, stars, language, etc.
|   +-- microsoft/
|       +-- vscode.json
|
+-- projects/                # Analysis results
|   +-- facebook/
|       +-- react/
|           +-- HEAD.json    # LoC, deps, ai_markers, cached_at
|
+-- dependencies/            # Dependency trees
+-- loc/                     # Package LoC cache
```

## CLI Commands

| Command | Purpose |
|---------|---------|
| `iceberg discover -v` | Fetch repos from all sources |
| `iceberg run-analysis --batch-size 25 -v` | Analyze stale repos |
| `iceberg run-analysis --force` | Force re-analysis |
| `iceberg export` | Build SPA data |
| `iceberg status` | Project health overview |
| `iceberg status -v` | Per-repo age details |
| `iceberg track owner/repo` | Track a repo |
| `iceberg untrack owner/repo` | Untrack a repo |
| `iceberg list-tracked` | List tracked repos |
| `iceberg analyze owner/repo` | Analyze a single repo |
| `iceberg fetch --source trending` | Fetch from a single source |
| `iceberg backfill-ai` | Backfill AI marker detection |

## GitHub Actions Workflows

| Workflow | Schedule | CLI Equivalent |
|----------|----------|---------------|
| `discover.yml` | Monday 6 AM UTC | `iceberg discover -v` |
| `analyze.yml` | Daily 7 AM UTC | `iceberg run-analysis --batch-size 25 -v` |
| `publish.yml` | After analysis | `iceberg export` + Pages deploy |

## Scalability

```
Discovery: 400-700 unique repos per run
Analysis: 25 repos/day (configurable via --batch-size)
Total dataset: 500-10,000 repos
```

**Rate limits:**
- GitHub API (no token): 60 req/hour
- GitHub API (with token): 5,000 req/hour
- Analysis rate limiting: 2s pause every 10 repos

## See Also

- [Workflows Guide](WORKFLOWS.md) - Detailed workflow usage
- [Tracking Guide](TRACKING.md) - Repository tracking
- [Main README](../README.md) - Getting started
