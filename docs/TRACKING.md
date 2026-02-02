# Repository Tracking and Updates

Iceberg now supports tracking repositories for continuous updates and detecting when cached data is stale.

## Quick Start

```bash
# Track a specific repository
iceberg track facebook/react

# Check all repos for updates
python scripts/analyze_all_discovered.py --update

# Update only tracked repos
python scripts/update_tracked.py

# List tracked repos
iceberg list-tracked
```

## Features Overview

### 1. Manual Tracking
Add specific repos to monitor continuously, beyond trending/search.

### 2. Update Detection  
Compare cached commit hashes with current HEAD to detect stale data.

### 3. Smart Re-analysis
Only re-analyze repos when new commits are detected.

## Commands

### Track Repositories

```bash
# Add to tracking list
iceberg track owner/repo

# Remove from tracking
iceberg untrack owner/repo

# List all tracked
iceberg list-tracked
iceberg list-tracked --json
```

### Update Repositories

```bash
# Check discovered repos for updates
python scripts/analyze_all_discovered.py --update

# Update tracked repos only
python scripts/update_tracked.py

# Force re-analysis (all repos)
python scripts/analyze_all_discovered.py --force
```

## Workflow Integration

Recommended daily workflow:

```bash
#!/bin/bash

# Fetch new trending repos
iceberg fetch --source trending --since daily --limit 25

# Check for updates
python scripts/analyze_all_discovered.py --update
python scripts/update_tracked.py

# Export to SPA
iceberg export

# Commit changes (if using GitHub Pages)
git add cache spa/data
git commit -m "Update analysis data"
git push
```

## How Update Detection Works

1. **Fetch current HEAD**: Get latest commit hash from GitHub
2. **Compare with cache**: Check cached commit hash
3. **Detect changes**: If different, re-analysis needed
4. **Update**: Clone and analyze new version

## Storage

Tracked repos stored in `cache/tracked.json`:

```json
{
  "repositories": [
    {
      "owner": "facebook",
      "repo": "react", 
      "added_at": "2026-02-02T23:00:00+00:00"
    }
  ],
  "updated_at": "2026-02-02T23:00:00+00:00"
}
```

## Best Practices

- **Set GITHUB_TOKEN** for higher rate limits
- **Track selectively** - focus on important repos
- **Run --update daily** to keep data fresh
- **Use --force sparingly** - it re-analyzes everything

## Troubleshooting

**"could not fetch current HEAD"**
- Network issue or GitHub rate limit
- Set GITHUB_TOKEN environment variable

**Update not detected**
- Force re-analysis: `iceberg analyze owner/repo`
- Or clear cache: `rm -rf cache/projects/owner/repo`

**Too slow**
- Focus on tracked repos: `python scripts/update_tracked.py`
- Use --update less frequently (e.g., weekly)
