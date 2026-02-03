# GitHub Actions Workflows

Automated workflows for keeping Iceberg data fresh and deploying to GitHub Pages.

## Workflows Overview

### 1. Daily Discovery (`discovery.yml`)
**Schedule:** Daily at 6 AM UTC  
**Purpose:** Find new trending repos and update current batch

**What it does:**
1. Fetches trending (daily, weekly, monthly)
2. Fetches search results (stars>10k, JS + Python)
3. Analyzes new repos (~20-50 per run)
4. Updates repos in today's discovery
5. Exports to SPA
6. Commits and pushes changes

**Manual trigger:**
```bash
# Via GitHub UI: Actions → Daily Discovery → Run workflow
# Or via CLI:
gh workflow run discovery.yml
```

**Logs:** Uploaded as artifacts (7 day retention)

---

### 2. Weekly Maintenance (`maintenance.yml`)
**Schedule:** Sundays at 8 AM UTC  
**Purpose:** Keep entire dataset fresh

**What it does:**
1. Loads all cached repos (1000s)
2. Filters by staleness strategy
3. Prioritizes: tracked > popular > regular
4. Updates stale repos (max 200/run)
5. Exports to SPA
6. Commits and pushes changes
7. Creates issue on failure

**Manual trigger:**
```bash
# Via GitHub UI with custom max updates:
# Actions → Weekly Maintenance → Run workflow → max_updates: 100

# Or via CLI:
gh workflow run maintenance.yml -f max_updates=100
```

**Logs:** Uploaded as artifacts (14 day retention)

---

### 3. Update Tracked Repos (`update-tracked.yml`)
**Schedule:** Manual (optional: enable cron for daily)  
**Purpose:** Quick updates for tracked repos only

**What it does:**
1. Loads tracked repos from cache/tracked.json
2. Checks for updates (HEAD comparison)
3. Re-analyzes stale tracked repos
4. Exports to SPA
5. Commits and pushes changes

**Manual trigger:**
```bash
gh workflow run update-tracked.yml
```

**Enable daily schedule:**
Uncomment lines 6-8 in `update-tracked.yml`:
```yaml
schedule:
  - cron: '0 12 * * *'  # Noon UTC daily
```

---

### 4. Deploy to Pages (`pages.yml`)
**Trigger:** On push to main (spa/** changes)  
**Purpose:** Deploy SPA to GitHub Pages

**What it does:**
1. Uploads spa/ directory
2. Deploys to GitHub Pages
3. Makes site available at username.github.io/iceberg

---

## Setup Instructions

### 1. Enable GitHub Actions
```bash
# In your repo settings:
Settings → Actions → General → Allow all actions
```

### 2. Configure GitHub Pages
```bash
# In your repo settings:
Settings → Pages
Source: GitHub Actions
```

### 3. Set GitHub Token (Already Available)
The workflows use `${{ secrets.GITHUB_TOKEN }}` which is automatically provided by GitHub Actions. No setup needed!

### 4. Install osv-scanner Locally (Optional)
```bash
# For local testing:
# macOS
brew install osv-scanner

# Linux
curl -sSL https://github.com/google/osv-scanner/releases/download/v1.9.1/osv-scanner_1.9.1_linux_amd64 -o /usr/local/bin/osv-scanner
chmod +x /usr/local/bin/osv-scanner
```

## Monitoring

### View Workflow Runs
```bash
# Via GitHub UI:
Actions tab → Select workflow → View runs

# Via CLI:
gh run list --workflow=discovery.yml --limit 5
gh run view <run-id> --log
```

### Check Logs
```bash
# Download artifacts:
gh run download <run-id>

# View logs:
cat discovery-log/discovery.log
cat maintenance-log/maintenance.log
```

### Issues on Failure
Maintenance workflow automatically creates an issue when it fails. Check:
```
Issues → Label: maintenance
```

## Schedule Details

| Workflow | Day | Time (UTC) | Frequency |
|----------|-----|------------|-----------|
| Discovery | Daily | 6 AM | Every day |
| Maintenance | Sunday | 8 AM | Weekly |
| Tracked | Manual | - | On-demand |
| Pages | Push | - | On spa/ changes |

## Customization

### Change Schedule

Edit the cron expression:
```yaml
schedule:
  - cron: '0 6 * * *'  # Min Hour Day Month Weekday
```

Examples:
```yaml
- cron: '0 */6 * * *'   # Every 6 hours
- cron: '0 0 * * 1'     # Mondays at midnight
- cron: '0 12 1,15 * *' # 1st and 15th of month at noon
```

### Adjust Max Updates

Edit `maintenance.yml`:
```yaml
# Change default
default: '500'  # Instead of 200

# Or pass when triggering:
gh workflow run maintenance.yml -f max_updates=500
```

### Enable/Disable Workflows

```bash
# Disable:
gh workflow disable discovery.yml

# Enable:
gh workflow enable discovery.yml
```

## Cost Estimation

GitHub Actions free tier:
- **Public repos:** Unlimited
- **Private repos:** 2,000 minutes/month

Estimated usage per month:
```
Discovery (daily):
  30 runs × 5 min = 150 minutes

Maintenance (weekly):
  4 runs × 30 min = 120 minutes

Total: ~270 minutes/month (well within free tier)
```

## Troubleshooting

### Workflow not running
**Check:**
1. Actions enabled in settings
2. Cron schedule correct (UTC time)
3. Workflow file in `.github/workflows/`

### Commits not pushing
**Check:**
1. `permissions: contents: write` in workflow
2. Branch protection rules (may need to allow Actions)
3. Check workflow logs for git errors

### osv-scanner fails
**Check:**
1. Installation step succeeded
2. osv-scanner binary is executable
3. Lock files present in repos

### Rate limit exceeded
**Solution:**
1. Use GitHub token (already configured)
2. Reduce max-updates
3. Increase time between runs

### Pages not deploying
**Check:**
1. GitHub Pages enabled in settings
2. Pages workflow has `pages: write` permission
3. spa/data/ directory exists and has data

## Local Testing

Test workflows locally before committing:

```bash
# Install act (GitHub Actions local runner)
brew install act  # macOS
# or download from https://github.com/nektos/act

# Test discovery workflow
act schedule --workflows .github/workflows/discovery.yml

# Test with secrets
act schedule -s GITHUB_TOKEN=$GITHUB_TOKEN --workflows .github/workflows/discovery.yml
```

## Manual Operations

If workflows fail, run manually:

```bash
# Discovery
python scripts/run_discovery.py
python -m iceberg.cli export
git add cache spa/data && git commit -m "Manual discovery" && git push

# Maintenance
python scripts/run_maintenance.py --max-updates=200
python -m iceberg.cli export
git add cache spa/data && git commit -m "Manual maintenance" && git push
```

## See Also

- [Architecture Guide](../../docs/ARCHITECTURE.md)
- [Workflows Guide](../../docs/WORKFLOWS.md)
- [Tracking Guide](../../docs/TRACKING.md)
