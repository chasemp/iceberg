# Repository Tracking

Track specific repositories for priority analysis with shorter staleness thresholds.

## Quick Start

```bash
# Track a repository
iceberg track facebook/react

# List tracked repos
iceberg list-tracked

# Check project status
iceberg status

# Run analysis (tracked repos get priority)
iceberg run-analysis -v
```

## How It Works

Tracking is stored as a `"tracked"` category in the repo's metadata file (`cache/repos/{owner}/{repo}.json`), alongside discovery sources:

```json
{
  "owner": "facebook",
  "name": "react",
  "stars": 242901,
  "categories": {
    "search": "2026-02-10",
    "github-ranking-top-100-stars": "2026-02-09",
    "tracked": "2026-02-11"
  }
}
```

Tracked repos get:
- **Shorter staleness threshold**: 24 hours (vs 7 days for popular, 30 for regular)
- **Higher priority**: Analyzed first in each batch
- **Visibility**: Shown in `iceberg status` output

## Commands

### Track a Repository
```bash
iceberg track owner/repo
```

If the repo doesn't have metadata yet (not previously discovered), a minimal metadata file is created.

### Untrack a Repository
```bash
iceberg untrack owner/repo
```

Removes the `"tracked"` category but preserves all other metadata and discovery sources.

### List Tracked Repos
```bash
iceberg list-tracked
iceberg list-tracked --json
```

### Check Status
```bash
iceberg status
```

Shows tracked count alongside discovered, analyzed, and exported counts.

## Staleness Tiers

Configured in `config/staleness.json`:

| Tier | Condition | Max Age | Priority |
|------|-----------|---------|----------|
| **Tracked** | has "tracked" category | 24 hours | Highest |
| Popular | stars >= 10,000 | 7 days | Medium |
| Regular | everything else | 30 days | Lowest |

When `iceberg run-analysis` runs, it processes repos in tier order: all stale tracked repos first, then popular, then regular.

## Workflow Integration

The daily analysis workflow (`analyze.yml`) automatically handles tracked repos with priority. No separate workflow needed.

```bash
# Tracked repos analyzed first, then popular, then regular
iceberg run-analysis --batch-size 25 -v
```

To force immediate re-analysis of everything:
```bash
iceberg run-analysis --force --batch-size 10 -v
```

## Troubleshooting

**"not being tracked"**
- Check spelling: `iceberg list-tracked`
- Re-track: `iceberg track owner/repo`

**Tracked repo not analyzed**
- Check batch size: tracked repos are prioritized but still limited by `--batch-size`
- Force it: `iceberg run-analysis --force --batch-size 5 -v`

**Update not detected**
- Force re-analysis: `iceberg analyze owner/repo`
- Or clear cache: `rm -rf cache/projects/owner/repo`

## See Also

- [Workflows Guide](WORKFLOWS.md) - Workflow details
- [Architecture Guide](ARCHITECTURE.md) - System architecture
