#!/usr/bin/env bash
# KAKAOPC Intel — Daily Pipeline Orchestrator (Linux / CI)
# Usage: bash scripts/daily_run.sh
# GitHub Actions triggers this daily at 00:00 UTC (08:00 CST)

set -euo pipefail

export TZ=Asia/Shanghai

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DATE=$(date +%Y-%m-%d)
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/$DATE.log"

cd "$PROJECT_ROOT"

mkdir -p "$LOG_DIR"

# Resolve Python — prefer python3, then python
PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" &>/dev/null; then
        PYTHON="$candidate"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "[FATAL] Python not found in PATH"
    exit 1
fi

log() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local line="[$timestamp] $1"
    echo "$line"
    echo "$line" >> "$LOG_FILE"
}

log "=== KAKAOPC Intel Daily Pipeline Start ==="
log "Date: $DATE"
log "Project: $PROJECT_ROOT"
log "Python: $($PYTHON --version 2>&1)"

# Day-level lock file to prevent duplicate runs
DAILY_DIR="$PROJECT_ROOT/daily/$DATE"
LOCK_FILE="$DAILY_DIR/.pipeline_done"
mkdir -p "$DAILY_DIR"
if [ -f "$LOCK_FILE" ]; then
    log "Pipeline already completed for $DATE (lock file exists). Exiting."
    exit 0
fi

# ─── Step 1: Signal Collection ───

log ""
log "--- Step 1: Signal Collection ---"

COLLECTORS=(
    "Hacker News:collect_hackernews"
    "GitHub Trending:collect_github"
    "Google Trends:collect_trends"
    "Product Hunt:collect_producthunt"
    "Reddit:collect_reddit"
    "Indie Hackers:collect_indiehackers"
    "V2EX:collect_v2ex"
    "w2solo:collect_w2solo"
    "HuggingFace:collect_huggingface"
)

for entry in "${COLLECTORS[@]}"; do
    name="${entry%%:*}"
    script="${entry##*:}"
    if $PYTHON -m "scripts.$script" 2>&1; then
        log "  [$name] OK"
    else
        log "  [$name] ERROR (exit=$?)"
    fi
done

# ─── Step 2: Signal Processing ───

log ""
log "--- Step 2: Signal Processing ---"

if $PYTHON -m scripts.process_signals 2>&1; then
    log "  [Process] OK"
else
    log "  [Process] FAIL"
fi

# ─── Step 3: Daily Report ───

log ""
log "--- Step 3: Daily Report ---"

if $PYTHON -m scripts.generate_report 2>&1; then
    log "  [Report] OK"
else
    log "  [Report] FAIL"
fi

# ─── Step 4: Planet Article ───

log ""
log "--- Step 4: Planet Article ---"

if $PYTHON -m scripts.generate_article 2>&1; then
    log "  [Article] OK"
else
    log "  [Article] FAIL"
fi

# ─── Step 5: Action Plan ───

log ""
log "--- Step 5: Action Plan ---"

PIPE_FILE="$DAILY_DIR/pipeline.json"
if $PYTHON -m scripts.generate_action 2>&1; then
    if [ -f "$PIPE_FILE" ]; then
        STATUS=$(python3 -c "import json; d=json.load(open('$PIPE_FILE')); print(d['steps']['action'].get('status',''))" 2>/dev/null || echo "")
        if [ "$STATUS" = "skipped" ]; then
            REASON=$(python3 -c "import json; d=json.load(open('$PIPE_FILE')); print(d['steps']['action'].get('reason',''))" 2>/dev/null || echo "")
            log "  [Action] SKIPPED ($REASON)"
        else
            log "  [Action] OK"
        fi
    else
        log "  [Action] OK"
    fi
else
    log "  [Action] FAIL"
fi

# ─── Step 6: Tracking Update ───

log ""
log "--- Step 6: Tracking Update ---"

if $PYTHON -m scripts.update_tracking 2>&1; then
    log "  [Tracking] OK"
else
    log "  [Tracking] FAIL"
fi

# ─── Step 6b: Recurring Signal Tracking ───

log ""
log "--- Step 6b: Recurring Signal Tracking ---"

if $PYTHON -m scripts.track_recurring 2>&1; then
    log "  [Recurring] OK"
else
    log "  [Recurring] FAIL"
fi

# ─── Step 6c: Demand Radar ───

log ""
log "--- Step 6c: Demand Radar ---"

if $PYTHON -m scripts.track_demands 2>&1; then
    log "  [DemandRadar] OK"
else
    log "  [DemandRadar] FAIL"
fi

# ─── Step 7: Landing Page ───

log ""
log "--- Step 7: Landing Page ---"

if $PYTHON -m scripts.generate_landing_page 2>&1; then
    if [ -f "$PIPE_FILE" ]; then
        STATUS=$(python3 -c "import json; d=json.load(open('$PIPE_FILE')); print(d['steps']['lp'].get('status',''))" 2>/dev/null || echo "")
        if [ "$STATUS" = "skipped" ]; then
            REASON=$(python3 -c "import json; d=json.load(open('$PIPE_FILE')); print(d['steps']['lp'].get('reason',''))" 2>/dev/null || echo "")
            log "  [LP] SKIPPED ($REASON)"
        else
            log "  [LP] OK"
        fi
    else
        log "  [LP] OK"
    fi
else
    log "  [LP] FAIL"
fi

# ─── Step 8: Translate Content (zh → en) ───

log ""
log "--- Step 9: Translate Content (zh → en) ---"

if $PYTHON -m scripts.translate_content 2>&1; then
    log "  [Translate] OK"
else
    log "  [Translate] FAIL (non-fatal)"
fi

# ─── Step 10: SEO Content Files ───

log ""
log "--- Step 10: SEO Content Files ---"

if $PYTHON -m scripts.generate_seo_files 2>&1; then
    log "  [SEO] OK"
else
    log "  [SEO] FAIL (non-fatal)"
fi

# ─── Step 11: Dashboard ───

log ""
log "--- Step 11: Dashboard ---"

if $PYTHON -m scripts.generate_dashboard 2>&1; then
    log "  [Dashboard] OK"
else
    log "  [Dashboard] FAIL"
fi

# ─── Step 12: Weekly Report (Sunday only) ───

if [ "$(date +%u)" -eq 7 ]; then
    log ""
    log "--- Step 12: Weekly Report (Sunday trigger) ---"
    if $PYTHON -m scripts.generate_weekly 2>&1; then
        log "  [Weekly] OK"
    else
        log "  [Weekly] FAIL"
    fi
fi

# ─── Step 12b: BuilderPulse 对比 ───

log ""
log "--- Step 12b: BuilderPulse Comparison ---"

if $PYTHON -m scripts.compare_with_builderpulse --date "$DATE" 2>&1; then
    log "  [Compare] OK"
else
    log "  [Compare] FAIL (non-blocking)"
fi

# ─── Step 13: Git commit & push ───

log ""
log "--- Step 13: Deploy Dashboard Data & SEO Content ---"

git add public/dashboard/data/dashboard.json tracking/recurring_signals.json tracking/demand_radar.json public/sitemap.xml content/reports/ content/articles/ public/*/index.html compare/ 2>&1 || true

if git diff --cached --name-only | grep -q .; then
    git config user.email "pipeline@kakaopc-intel.bot"
    git config user.name "KAKAOPC Intel Bot"
    git commit -m "Dashboard data update: $DATE" 2>&1 || true
    log "  [Git] Committed dashboard data for $DATE"

    if git push origin master 2>&1; then
        log "  [Git] Pushed to origin/master → Vercel deploy triggered"
    else
        log "  [Git] Push FAILED"
    fi
else
    log "  [Git] No changes to deploy"
fi

# ─── Summary ───

log ""
log "=== Pipeline Complete ==="

# Write lock file
echo "done" > "$LOCK_FILE"

if [ -d "$DAILY_DIR" ]; then
    log "Output: $(ls -1 "$DAILY_DIR" | tr '\n' ' ')"
fi

log "Log: $LOG_FILE"

# Copy log to daily dir for archival
cp "$LOG_FILE" "$DAILY_DIR/pipeline.log" 2>/dev/null || true
