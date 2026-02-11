# GitHub Actions Workflows

Automated workflows for keeping Iceberg data fresh and deploying to GitHub Pages.

## Workflows Overview

### 1. Weekly Discovery (`discover.yml`)
**Schedule:** Monday at 6 AM UTC
**Purpose:** Find new repos from trending, search, and ranking sources

**What it does:**
1. Fetches trending (monthly)
2. Fetches search results (stars>10k, JS + Python)
3. Fetches GitHub-Ranking (top repos by language)
4. Deduplicates and saves metadata
5. Commits discovery data

**Manual trigger:**
```bash
# Via GitHub UI: Actions > Weekly Discovery > Run workflow
# Or via CLI:
gh workflow run discover.yml
```

**Logs:** Uploaded as artifacts (7 day retention)

---

### 2. Daily Analysis (`analyze.yml`)
**Schedule:** Daily at 7 AM UTC
**Purpose:** Analyze repos with new or stale data

**What it does:**
1. Loads all discovered repos
2. Checks staleness against `config/staleness.json` thresholds
3. Prioritizes: tracked > popular > regular
4. Analyzes up to 25 stale repos (configurable)
5. Exports to SPA format
6. Commits analysis + SPA data
7. Creates issue on failure

**Manual trigger:**
```bash
# Default (25 repos):
gh workflow run analyze.yml

# Custom batch size + force:
gh workflow run analyze.yml -f batch_size=50 -f force=true
```

**Logs:** Uploaded as artifacts (7 day retention)

---

### 3. Publish to GitHub Pages (`publish.yml`)
**Trigger:** After analysis completes + push to `spa/**`
**Purpose:** Deploy SPA to GitHub Pages

**What it does:**
1. Runs `iceberg export` to build SPA data
2. Deploys spa/ directory to GitHub Pages
3. Site available at username.github.io/iceberg

**Manual trigger:**
```bash
gh workflow run publish.yml
```

---

## Setup Instructions

### 1. Enable GitHub Actions
```
Settings > Actions > General > Allow all actions
```

### 2. Configure GitHub Pages
```
Settings > Pages > Source: GitHub Actions
```

### 3. GitHub Token
The workflows use `${{ secrets.GITHUB_TOKEN }}` which is automatically provided. No setup needed.

### 4. Install osv-scanner Locally (Optional)
```bash
# macOS
brew install osv-scanner

# Or via Go
go install github.com/google/osv-scanner/v2/cmd/osv-scanner@latest
```

## CLI Equivalents

Each workflow runs the same CLI commands you can use locally:

| Workflow | CLI Command |
|----------|-------------|
| Discovery | `iceberg discover -v` |
| Analysis | `iceberg run-analysis --batch-size 25 -v` |
| Publish | `iceberg export` |
| Status | `iceberg status` (check project health) |

## Monitoring

### View Workflow Runs
```bash
gh run list --workflow=analyze.yml --limit 5
gh run view <run-id> --log
```

### Check Logs
```bash
gh run download <run-id>
cat analyze-log/analyze.log
```

### Issues on Failure
Analysis workflow creates an issue when it fails. Check:
```
Issues > Label: automation
```

## Schedule Details

| Workflow | Day | Time (UTC) | Frequency |
|----------|-----|------------|-----------|
| Discovery | Monday | 6 AM | Weekly |
| Analysis | Daily | 7 AM | Every day |
| Publish | After analysis | - | Automatic |

## Staleness Thresholds

Configured in `config/staleness.json`:

| Tier | Condition | Max Age |
|------|-----------|---------|
| Tracked | `iceberg track owner/repo` | 24 hours |
| Popular | stars > 10,000 | 7 days |
| Regular | everything else | 30 days |

## Manual Operations

If workflows fail, run the same commands locally:

```bash
# Discovery
iceberg discover -v

# Analysis
iceberg run-analysis --batch-size 25 -v

# Force re-analysis
iceberg run-analysis --force --batch-size 10 -v

# Export
iceberg export

# Check status
iceberg status -v
```

## See Also

- [Architecture Guide](../../docs/ARCHITECTURE.md)
- [Workflows Guide](../../docs/WORKFLOWS.md)
- [Tracking Guide](../../docs/TRACKING.md)
