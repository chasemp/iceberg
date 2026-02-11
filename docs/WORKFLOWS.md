# Discovery, Analysis, and Publish Workflows

Iceberg uses three distinct workflow streams: **Discovery** (find repos), **Analysis** (analyze stale repos), and **Publish** (deploy SPA).

## Architecture Overview

```
+-----------------------------------------------------+
|                   DISCOVERY                          |
|                  (Weekly)                            |
+-----------------------------------------------------+
| 1. Fetch trending (monthly)                         |
| 2. Fetch search queries (stars>10k, languages)      |
| 3. Fetch GitHub-Ranking (top repos by language)     |
| 4. Dedupe -> ~400-700 unique repos                  |
| 5. Save metadata to cache/repos/                    |
+-----------------------------------------------------+
                         |
                         v
+-----------------------------------------------------+
|                   ANALYSIS                           |
|                   (Daily)                            |
+-----------------------------------------------------+
| 1. Load ALL repos from cache/repos/                 |
| 2. Check staleness (config/staleness.json):         |
|    - Tracked: > 24h                                 |
|    - Popular (stars>10k): > 7 days                  |
|    - Regular: > 30 days                             |
| 3. Prioritize: tracked > popular > regular          |
| 4. Analyze up to batch-size (default 25)            |
| 5. Rate limit: 2s pause every 10 repos              |
+-----------------------------------------------------+
                         |
                         v
+-----------------------------------------------------+
|                   PUBLISH                            |
|              (After analysis)                        |
+-----------------------------------------------------+
| 1. Export data to SPA format                        |
| 2. Deploy to GitHub Pages                           |
+-----------------------------------------------------+
```

## Staleness Configuration

All staleness thresholds are in `config/staleness.json`:

```json
{
  "tiers": {
    "tracked": { "max_age_hours": 24 },
    "popular": { "stars_threshold": 10000, "max_age_days": 7 },
    "regular": { "max_age_days": 30 }
  },
  "min_age_hours": 1,
  "batch_pause_every_n": 10,
  "batch_pause_seconds": 2,
  "default_batch_size": 25
}
```

### Tier Determination

A repo's tier is determined in this order:
1. **Tracked** - repo has "tracked" in its categories (`iceberg track owner/repo`)
2. **Popular** - stars >= `stars_threshold` (default 10,000)
3. **Regular** - everything else

## CLI Commands

### Discovery
```bash
# Run discovery (fetch from all sources, dedupe, save)
iceberg discover -v
```

**Output:**
```
Fetching discovery sources...
  Fetching trending monthly...
  Got 25 repos from trending monthly
  ...

Discovery complete:
  Total fetched:  850
  Unique repos:   670
  Sources saved:  12
```

### Analysis
```bash
# Default: analyze up to 25 stale repos
iceberg run-analysis -v

# Custom batch size
iceberg run-analysis --batch-size 50 -v

# Force re-analysis (ignore staleness)
iceberg run-analysis --force --batch-size 10 -v
```

**Output:**
```
Loading discovered repositories...
Found 670 repos in cache

Stale: 45, Skipped: 625
Analyzing: 25 (batch size: 25)

[1/25] facebook/react (tracked) - tracked, 2.1 days old
  Analyzed: 50,000 LoC
  Dependencies: 850,000 LoC

[2/25] microsoft/vscode (popular) - popular, 8.3 days old
  Analyzed: 1,200,000 LoC
  ...

Analysis complete:
  Analyzed:   25
  Errors:     2
  Skipped:    625
  Remaining:  18
```

### Status
```bash
# Quick overview
iceberg status

# Per-repo age details
iceberg status -v

# Machine-readable
iceberg status --json
```

**Output:**
```
Iceberg Status
========================================
Discovered repos:     670
Analyzed repos:       624 (93.1%)
  With dependencies:  147
  With AI markers:    22
Exported to SPA:      587
Tracked repos:        3

Analysis age:
     < 1 day:  45 repos
    1-7 days:  200 repos
   7-30 days:  340 repos
   > 30 days:  39 repos
  Oldest: owner/repo (42.1 days ago)
```

### Tracking
```bash
# Track a repo (adds "tracked" category to its metadata)
iceberg track facebook/react

# List tracked repos
iceberg list-tracked

# Untrack
iceberg untrack facebook/react
```

Tracked repos are stored as a `"tracked"` category in `cache/repos/{owner}/{repo}.json`, alongside discovery sources like `"github-ranking-top-100-stars"` or `"search"`.

## GitHub Actions Workflows

### discover.yml (Weekly, Monday 6 AM UTC)
```bash
iceberg discover -v
git add cache/discovered/ cache/repos/
git commit && git push
```

### analyze.yml (Daily, 7 AM UTC)
```bash
iceberg run-analysis --batch-size 25 -v
iceberg export
git add cache/projects/ cache/loc/ spa/data/
git commit && git push
```

Supports `workflow_dispatch` inputs: `force` (bool), `batch_size` (string).

### publish.yml (After analysis + push to spa/**)
```bash
iceberg export
# Deploy to GitHub Pages
```

## Rate Limiting

**GitHub API:**
- Without token: 60 requests/hour
- With token: 5,000 requests/hour

**Built-in rate limiting:**
- Analysis: 2s pause every 10 repos (configurable in staleness.json)

```bash
export GITHUB_TOKEN=ghp_your_token_here
```

## Troubleshooting

### Analysis runs too long
Reduce batch size:
```bash
iceberg run-analysis --batch-size 10 -v
```

### Repos not updating
Check staleness:
```bash
iceberg status -v  # Shows per-repo age
```

Force re-analysis:
```bash
iceberg run-analysis --force --batch-size 5 -v
```

Or adjust thresholds in `config/staleness.json`.

### Rate limit exceeded
- Set `GITHUB_TOKEN`
- Reduce `--batch-size`
- Space out runs

## See Also

- [Tracking Guide](TRACKING.md) - Repository tracking
- [Architecture Guide](ARCHITECTURE.md) - System architecture
- [Main README](../README.md) - Getting started
