# Discovery and Maintenance Workflows

Iceberg separates data collection into two distinct workflows: **Discovery** (find new) and **Maintenance** (keep fresh).

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    DISCOVERY RUN                         │
│                     (Daily)                              │
├─────────────────────────────────────────────────────────┤
│ 1. Fetch trending (daily, weekly, monthly)              │
│ 2. Fetch search queries (stars>10k, languages)          │
│ 3. Dedupe → ~50-100 unique repos                        │
│ 4. For each repo:                                        │
│    • NEW → analyze                                       │
│    • EXISTS + in today's batch → check updates          │
│    • EXISTS + analyzed < 24h → skip                     │
│ 5. Mark with discovery metadata                         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                   MAINTENANCE RUN                        │
│                 (Weekly/Monthly)                         │
├─────────────────────────────────────────────────────────┤
│ 1. Load ALL cached repos                                │
│ 2. Filter by staleness:                                 │
│    • Skip if analyzed < 24h                             │
│    • Skip if in yesterday's discovery                   │
│    • Prioritize: tracked > popular > regular            │
│ 3. Check for updates (HEAD comparison)                  │
│ 4. Re-analyze stale repos (max 200/run)                 │
│ 5. Batch with rate limiting                             │
└─────────────────────────────────────────────────────────┘
```

## Staleness Strategy

### Tracked Repos (Manual)
```
Check: Daily
Update if: > 1 day old AND HEAD changed
Priority: Highest
```

### Popular Repos (stars > 10k)
```
Check: Weekly  
Update if: > 7 days old
Priority: Medium
```

### Regular Repos
```
Check: Monthly
Update if: > 30 days old
Priority: Low
```

### Old Discoveries (> 90 days)
```
Check: Quarterly
Update if: > 90 days old
Priority: Lowest
```

## Metadata Fields

Added to `cache/projects/owner/repo/HEAD.json`:

```json
{
  "owner": "facebook",
  "repo": "react",
  "loc": 50000,
  "cached_at": "2026-02-02T12:00:00Z",
  "commit_hash": "abc12345",
  
  // Discovery metadata
  "last_discovered": "2026-02-02",
  "discovery_source": "trending-weekly",
  "tracked": false,
  "maintenance_priority": "medium"
}
```

## Usage

### Daily Discovery
```bash
# Run discovery (finds new + updates current batch)
python scripts/run_discovery.py

# With verbose output
python scripts/run_discovery.py --verbose
```

**Output:**
```
🔍 DISCOVERY RUN
Date: 2026-02-02
============================================================

📡 Fetching discovery sources...
  Fetching trending daily...
  ✓ Got 25 repos from trending daily
  Fetching trending weekly...
  ✓ Got 25 repos from trending weekly
  ...

📊 Total repos fetched: 175
📊 Unique repos: 87

🔬 ANALYZING REPOS
============================================================

⏭️  facebook/react - analyzed 2.3h ago
🔍 new-org/new-repo - new repo
  ✓ Analyzed: 12,000 LoC
  ✓ Dependencies: 850,000 LoC

🔄 old-org/stale-repo - needs update: new commits
  ✓ Updated: 5,000 LoC

📊 DISCOVERY SUMMARY
============================================================
Discovered: 87 unique repos
Analyzed: 23
Skipped: 62
Errors: 2
```

### Weekly/Monthly Maintenance
```bash
# Run maintenance (checks all cached repos)
python scripts/run_maintenance.py

# Limit updates per run
python scripts/run_maintenance.py --max-updates=100

# With verbose output
python scripts/run_maintenance.py --verbose
```

**Output:**
```
🔧 MAINTENANCE RUN
Date: 2026-02-09 10:00:00 UTC
Max updates: 200
============================================================

📂 Loading cached repositories...
Loaded 1,234 cached repos

🔍 Filtering by staleness criteria...
Found 156 stale repos

📊 Prioritizing by maintenance strategy...
  Tracked: 10
  High priority: 5
  Medium priority: 45
  Low priority: 96

🔄 UPDATING REPOS
============================================================

🔄 tracked/repo - new commits (cached: abc12345, current: def67890)
  ✓ Updated: 15,000 LoC
  ✓ Dependencies: 2,500,000 LoC

⏭️  popular/repo - up to date

📊 MAINTENANCE SUMMARY
============================================================
Total cached: 1,234
Checked for staleness: 156
Updated: 45
Skipped (up to date): 101
Errors: 10
```

## Recommended Schedules

### GitHub Actions (Automated)

```yaml
# .github/workflows/discovery.yml
name: Daily Discovery
on:
  schedule:
    - cron: '0 6 * * *'  # 6 AM UTC daily
jobs:
  discover:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run discovery
        run: python scripts/run_discovery.py
      - name: Export to SPA
        run: python -m iceberg.cli export
      - name: Commit changes
        run: |
          git add cache spa/data
          git commit -m "Daily discovery $(date +%Y-%m-%d)" || exit 0
          git push
```

```yaml
# .github/workflows/maintenance.yml
name: Weekly Maintenance
on:
  schedule:
    - cron: '0 8 * * 0'  # 8 AM UTC Sundays
jobs:
  maintain:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run maintenance
        run: python scripts/run_maintenance.py --max-updates=200
      - name: Export to SPA
        run: python -m iceberg.cli export
      - name: Commit changes
        run: |
          git add cache spa/data
          git commit -m "Weekly maintenance $(date +%Y-%m-%d)" || exit 0
          git push
```

### Manual (Local Development)

```bash
# Monday: Discovery
python scripts/run_discovery.py

# Sunday: Maintenance  
python scripts/run_maintenance.py

# After either: Export
python -m iceberg.cli export

# Optional: Commit
git add cache spa/data
git commit -m "Update data"
git push
```

## Comparison: Old vs New

### Before (Single Script)
```bash
# analyze_all_discovered.py
# - Checks ALL discovered repos every time
# - No distinction between new and updates
# - No prioritization
# - Can re-analyze same repos repeatedly
```

### After (Separated Workflows)
```bash
# Discovery: Focuses on today's batch
python scripts/run_discovery.py
# - Only touches repos in today's discovery
# - Marks with metadata
# - Fast (50-100 repos)

# Maintenance: Handles entire dataset
python scripts/run_maintenance.py
# - Checks ALL repos
# - Filtered by staleness
# - Prioritized updates
# - Configurable batch size
```

## Decision Tree

**When to run Discovery?**
- ✅ Daily (automated)
- ✅ After fetching new trending/search results
- ✅ Want to find new repos

**When to run Maintenance?**
- ✅ Weekly (tracked + popular repos)
- ✅ Monthly (all repos)
- ✅ After clearing cache
- ✅ Want to freshen entire dataset

**When to use old scripts?**
- `analyze_all_discovered.py` → Use for one-time backfill
- `update_tracked.py` → Use for quick tracked-only updates

## Rate Limiting

Both scripts respect GitHub rate limits:

**Without token:**
```
- 60 requests/hour
- ~1 repo/minute
```

**With token:**
```bash
export GITHUB_TOKEN=ghp_your_token_here

# Now: 5000 requests/hour
# ~80 repos/minute
```

**Built-in rate limiting:**
- Discovery: No delays (processes current batch only)
- Maintenance: 2s pause every 10 updates

## Troubleshooting

### Discovery runs too slow
**Problem:** Fetching many sources
**Solution:** Reduce sources in `run_discovery.py`
```python
# Comment out less important sources
# for timeframe in ["daily", "weekly", "monthly"]:
for timeframe in ["daily"]:  # Just daily
```

### Maintenance runs too long
**Problem:** Too many stale repos
**Solution:** Reduce max-updates
```bash
python scripts/run_maintenance.py --max-updates=50
```

### Repos not updating
**Problem:** Staleness threshold not met
**Solution:** 
- Check metadata: `cat cache/projects/owner/repo/HEAD.json`
- Force update: `iceberg analyze owner/repo`
- Or adjust thresholds in `run_maintenance.py`

### Rate limit exceeded
**Problem:** Too many requests
**Solution:**
- Set `GITHUB_TOKEN`
- Reduce `max-updates`
- Space out runs

## Advanced: Custom Staleness

Edit `scripts/run_maintenance.py`:

```python
def should_check_for_updates(repo: dict[str, Any]) -> tuple[bool, str]:
    # ...
    
    # Custom: Check tracked repos every 6 hours
    if tracked and days_old > 0.25:  # 0.25 days = 6 hours
        return (True, f"tracked, {days_old:.1f} days old")
    
    # Custom: Aggressive updates for high-priority
    elif priority == "high" and days_old > 3:
        return (True, f"high priority, {days_old:.1f} days old")
```

## See Also

- [Tracking Guide](TRACKING.md) - Manual repo tracking
- [Main README](../README.md) - Getting started
- [CLI Reference](CLI.md) - All commands
