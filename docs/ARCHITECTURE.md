# Iceberg Architecture: Discovery, Tracking, and Maintenance

## Overview

Iceberg uses a three-tier approach to keep repository data fresh:

```
┌──────────────────┐
│    DISCOVERY     │  Find new repos (trending, search)
│     (Daily)      │  Update current batch only
└────────┬─────────┘
         │
         ├─────────► Cache with metadata
         │           (last_discovered, priority)
         │
┌────────▼─────────┐
│    TRACKING      │  Manually add important repos
│   (On-demand)    │  Mark as high priority
└────────┬─────────┘
         │
         ├─────────► Enhanced cache
         │           (tracked: true)
         │
┌────────▼─────────┐
│   MAINTENANCE    │  Check ALL repos for staleness
│  (Weekly/Monthly)│  Prioritize updates
└──────────────────┘
```

## Data Flow

### 1. Discovery (Entry Point)

**Input:**
- GitHub Trending (daily, weekly, monthly)
- GitHub Search (stars>10k, language filters)

**Process:**
```
Fetch sources → Dedupe → Check staleness → Analyze new/stale
```

**Output:**
- New repos analyzed
- Current batch updated
- Metadata saved:
  - `last_discovered: "2026-02-02"`
  - `discovery_source: "trending-weekly"`
  - `maintenance_priority: "medium"`

**Command:**
```bash
python scripts/run_discovery.py
```

### 2. Tracking (Manual Curation)

**Input:**
- User-specified repos

**Process:**
```
iceberg track owner/repo → Mark tracked → Add to tracking list
```

**Output:**
- Repo added to `cache/tracked.json`
- Analyzed on demand
- Metadata enhanced:
  - `tracked: true`
  - `maintenance_priority: "high"`

**Commands:**
```bash
iceberg track facebook/react
iceberg list-tracked
iceberg untrack facebook/react
```

### 3. Maintenance (Keep Fresh)

**Input:**
- ALL cached repos (discovered + tracked)

**Process:**
```
Load cache → Filter by staleness → Prioritize → Check updates → Re-analyze
```

**Staleness Rules:**
- Tracked (high): > 1 day old
- Popular (medium): > 7 days old
- Regular (low): > 30 days old
- Old: > 90 days old

**Output:**
- Stale repos updated
- Fresh data maintained
- Batch limited (default: 200/run)

**Command:**
```bash
python scripts/run_maintenance.py
python scripts/run_maintenance.py --max-updates=100
```

## Cache Structure

```
cache/
├── discovered/              # Discovery snapshots
│   ├── trending-daily/
│   │   └── 2026-02-02.json
│   ├── trending-weekly/
│   │   └── 2026-02-02.json
│   └── search/
│       └── xyz123.json
│
├── tracked.json             # Manually tracked repos
│   {
│     "repositories": [
│       {"owner": "facebook", "repo": "react", ...}
│     ]
│   }
│
├── projects/                # Analyzed repos
│   └── owner/repo/
│       └── HEAD.json        # WITH METADATA
│           {
│             "owner": "facebook",
│             "repo": "react",
│             "loc": 50000,
│             "cached_at": "2026-02-02T12:00:00Z",
│             "commit_hash": "abc12345",
│             
│             // Discovery metadata
│             "last_discovered": "2026-02-02",
│             "discovery_source": "trending-weekly",
│             "tracked": true,
│             "maintenance_priority": "high"
│           }
│
├── dependencies/            # Dep trees
└── loc/                     # Package LoC
```

## Workflow Comparison

### Discovery vs Maintenance

| Aspect | Discovery | Maintenance |
|--------|-----------|-------------|
| **Frequency** | Daily | Weekly/Monthly |
| **Scope** | Current batch (50-100) | ALL repos (1000s) |
| **Purpose** | Find new | Keep fresh |
| **Checks** | In today's discovery | Entire dataset |
| **Updates** | New + overlaps | Stale only |
| **Time** | 5-10 min | 30-60 min |
| **Metadata** | Sets initial | Preserves |

### When to Use Each

**Use Discovery when:**
- ✅ Want to find new trending repos
- ✅ Daily automated run
- ✅ Just fetched new data

**Use Maintenance when:**
- ✅ Want to freshen entire dataset
- ✅ Weekly/monthly run
- ✅ Have many cached repos

**Use Tracking when:**
- ✅ Specific repo to monitor
- ✅ Important project
- ✅ Not in trending/search

## Complete Workflow Example

### Initial Setup
```bash
# Day 1: Discovery run
python scripts/run_discovery.py
# → Analyzed 87 repos from trending/search

# Add important tracked repos
iceberg track your-org/important-repo
iceberg track another-org/critical-project

# Analyze tracked repos
python scripts/update_tracked.py

# Export to SPA
iceberg export
```

### Daily Operations
```bash
# Every morning: Discovery
python scripts/run_discovery.py
# → Checks trending, updates overlaps, finds new

# Export latest
iceberg export

# Commit to GitHub Pages
git add cache spa/data
git commit -m "Daily discovery $(date +%Y-%m-%d)"
git push
```

### Weekly Maintenance
```bash
# Sunday: Full maintenance
python scripts/run_maintenance.py
# → Checks all 1,234 cached repos
# → Updates 45 stale repos

# Export updated data
iceberg export

# Commit
git add cache spa/data
git commit -m "Weekly maintenance"
git push
```

## Metadata Evolution

### New Repo (Discovery)
```json
{
  "owner": "new-org",
  "repo": "new-repo",
  "loc": 5000,
  "cached_at": "2026-02-02T12:00:00Z",
  "commit_hash": "abc12345",
  
  // Added by discovery
  "last_discovered": "2026-02-02",
  "discovery_source": "trending-daily",
  "tracked": false,
  "maintenance_priority": "low"
}
```

### After Tracking
```json
{
  // ... same fields ...
  
  // Updated by tracking
  "tracked": true,
  "maintenance_priority": "high"
}
```

### After Maintenance
```json
{
  // ... same fields ...
  
  // Updated timestamp after re-analysis
  "cached_at": "2026-02-09T10:30:00Z",
  "commit_hash": "def67890",  // New commit
  
  // Metadata preserved
  "last_discovered": "2026-02-02",
  "tracked": true,
  "maintenance_priority": "high"
}
```

## Scalability

### Current Scale
```
Discovery: 50-100 repos/day
Tracked: 10-50 repos
Maintenance: 200 repos/run
Total dataset: 1,000-10,000 repos
```

### Limits
```
GitHub API (no token): 60 req/hour
GitHub API (with token): 5,000 req/hour

Discovery time: ~5-10 min
Maintenance time: ~30-60 min (200 repos)
```

### Optimization Strategies

**For large datasets:**
```bash
# 1. Reduce discovery sources
#    Edit run_discovery.py, comment out sources

# 2. Limit maintenance updates
python scripts/run_maintenance.py --max-updates=50

# 3. Increase staleness thresholds
#    Edit run_maintenance.py, adjust days_old checks

# 4. Run maintenance less frequently
#    Weekly → Monthly

# 5. Set GitHub token
export GITHUB_TOKEN=ghp_your_token
```

## Scripts Reference

### Core Workflows
| Script | Purpose | Frequency | Time |
|--------|---------|-----------|------|
| `run_discovery.py` | Find new + update batch | Daily | 5-10min |
| `run_maintenance.py` | Keep all repos fresh | Weekly | 30-60min |
| `update_tracked.py` | Update tracked only | As needed | 1-5min |

### Legacy Scripts (Still Useful)
| Script | Purpose | When to Use |
|--------|---------|-------------|
| `analyze_all_discovered.py` | Backfill all | After cache clear |
| `analyze_all_discovered.py --update` | Check all for updates | One-time update |
| `analyze_all_discovered.py --force` | Re-analyze all | New feature added |

## See Also

- [Workflows Guide](WORKFLOWS.md) - Detailed usage
- [Tracking Guide](TRACKING.md) - Manual tracking
- [Main README](../README.md) - Getting started
