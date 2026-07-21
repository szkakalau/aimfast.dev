#!/usr/bin/env bash
# AimFast.Dev — Daily Pipeline Orchestrator (Linux / CI)
# Usage: bash scripts/daily_run.sh
# GitHub Actions triggers this daily at 01:00 UTC (09:00 CST)

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
# Must verify with --version (Windows App alias passes `command -v` but fails)
PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" &>/dev/null && "$candidate" --version &>/dev/null 2>&1; then
        PYTHON="$candidate"
        break
    fi
done

# Fallback: explicit paths for Windows Git Bash
if [ -z "$PYTHON" ]; then
    for candidate in \
        "$LOCALAPPDATA/Programs/Python/Python314/python" \
        "$LOCALAPPDATA/Programs/Python/Python313/python" \
        "$LOCALAPPDATA/Programs/Python/Python312/python"; do
        if [ -x "$candidate" ] && "$candidate" --version &>/dev/null 2>&1; then
            PYTHON="$candidate"
            break
        fi
    done
fi

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

log "=== AimFast.Dev Daily Pipeline Start ==="
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
    "GitHub Deep:collect_github"
    "Google Trends:collect_trends"
    "Job Trends:collect_job_trends"
    "Product Hunt:collect_producthunt"
    "DEV Community:collect_devcommunity"
    "Reddit (11 subs):collect_reddit"
    "Reddit Consumer:collect_reddit_consumer"
    "V2EX:collect_v2ex"
    "w2solo:collect_w2solo"
    "HuggingFace:collect_huggingface"
    "Lobsters:collect_lobsters"
    "ArXiv:collect_arxiv"
    "豆瓣:collect_douban"
    # "小红书:collect_xiaohongshu"  # 暂禁用 — 未认证模式数据量有限
    "X/Twitter:collect_x"
    "Substack:collect_substack"
    "Product Changelogs:collect_changelogs"
    "Google News:collect_googlenews"
    "GitHub Releases:collect_github_releases"
    # ── 新增信源: 包管理 + 开发者社区（2026-07-16） ──
    "npm:collect_npm"
    "PyPI:collect_pypi"
    "Stack Overflow:collect_stackoverflow"
    "YouTube:collect_youtube"
    # ── 新增信源: 中文开发者生态（2026-07-22） ──
    "掘金:collect_juejin"
    "SegmentFault:collect_segmentfault"
    # ── 新增信源: 学术深度 + 内容增强（2026-07-22 Phase 3） ──
    "Semantic Scholar:collect_semanticscholar"
)

# C-end collectors are non-blocking — they may fail due to rate limits or missing auth
C_END_COLLECTORS=("Reddit Consumer" "豆瓣" "小红书" "X/Twitter" "Product Changelogs" "Google News" "GitHub Releases" "npm" "PyPI" "Stack Overflow" "YouTube" "Job Trends" "Substack" "掘金" "SegmentFault" "Semantic Scholar")

for entry in "${COLLECTORS[@]}"; do
    name="${entry%%:*}"
    script="${entry##*:}"
    if $PYTHON -m "scripts.$script" 2>&1; then
        log "  [$name] OK"
    else
        # C-end collectors: warn instead of error
        if [[ " ${C_END_COLLECTORS[*]} " =~ " ${name} " ]]; then
            log "  [$name] WARN (non-blocking C-end collector, exit=$?)"
        else
            log "  [$name] ERROR (exit=$?)"
        fi
    fi
done

# ═══ Step 1.5: Term Extraction (NLP Entity Extraction + Cross-Source Term DB) ═══

log ""
log "--- Step 1.5: Term Extraction (LLM NER + Cross-Source DB) ---"

if $PYTHON -m scripts.extract_terms 2>&1; then
    log "  [TermExtract] OK"
else
    log "  [TermExtract] WARN (non-fatal — term index not updated)"
fi

# ═══ Step 1.6: Term Normalization (Entity Dedup + Canonical Mapping) ═══

log ""
log "--- Step 1.6: Term Normalization (Canonical Mapping) ---"

if $PYTHON -m scripts.normalize_terms 2>&1; then
    log "  [Norm] OK"
else
    log "  [Norm] WARN (non-fatal — normalization skipped)"
fi

# ═══ Step 1.7: Term Lifecycle Classification (Age → Stage Mapping) ═══

log ""
log "--- Step 1.7: Term Lifecycle (Age → Nascent/Emergent/Validating/Rising) ---"

if $PYTHON -m scripts.classify_terms 2>&1; then
    log "  [Stages] OK"
else
    log "  [Stages] WARN (non-fatal)"
fi

# ═══ Step 1.8: Term Scoring (Multi-Factor Score → Visibility Ranking) ═══

log ""
log "--- Step 1.8: Term Scoring (source_count + growth + authority + mentions + freshness) ---"

if $PYTHON -m scripts.score_terms 2>&1; then
    log "  [Scores] OK"
else
    log "  [Scores] WARN (non-fatal)"
fi

# ═══ Step 1.9: Term Research Reports (AI-Generated Deep Dive for High-Score Terms) ═══

log ""
log "--- Step 1.9: Term Research Reports (12-section opportunity analysis) ---"

if $PYTHON -m scripts.generate_term_research 2>&1; then
    log "  [Research] OK"
else
    log "  [Research] WARN (non-fatal)"
fi

# ─── Step 2: Signal Processing ───

log ""
log "--- Step 2: Signal Processing ---"

if $PYTHON -m scripts.process_signals 2>&1; then
    log "  [Process] OK"
else
    log "  [Process] FAIL"
fi

# ─── Step 2.5: Enrich Top Signals with /last30days ───

log ""
log "--- Step 2.5: Community Enrichment (/last30days) ---"

if $PYTHON -m scripts.enrich_signals 2>&1; then
    log "  [Enrich] OK"
else
    log "  [Enrich] WARN (non-fatal)"
fi

# ─── Step 2.6: Cross-Source Term Validation ───

log ""
log "--- Step 2.6: Cross-Source Term Validation ---"

if $PYTHON -m scripts.cross_validate_terms 2>&1; then
    log "  [CrossVal] OK"
else
    log "  [CrossVal] WARN (non-fatal)"
fi

# ─── Step 3: Daily Report ───

log ""
log "--- Step 3: Daily Report ---"

if $PYTHON -m scripts.generate_report 2>&1; then
    log "  [Report] OK"
else
    log "  [Report] FAIL"
fi

# ─── Step 3.5: Trend Discovery ───

log ""
log "--- Step 3.5: Trend Discovery ---"

if $PYTHON -m scripts.generate_trends 2>&1; then
    log "  [Trends] OK"
else
    log "  [Trends] FAIL (non-fatal)"
fi

# ─── Step 3.5b: Save trend terms snapshot for Dashboard history ───
log ""
log "--- Step 3.5b: Trend History Snapshot ---"
HISTORY_DIR="public/dashboard/data/history"
mkdir -p "$HISTORY_DIR"
if [ -f tracking/trend_terms.json ]; then
    DATE=${DATE_OVERRIDE:-$(date +%Y-%m-%d)}
    # Extract lightweight snapshot: only fields needed by Dashboard Watchlist delta computation
    $PYTHON -c "
import json, sys
with open('tracking/trend_terms.json') as f:
    data = json.load(f)
snapshot = [
    {
        'id': t['id'],
        'canonical': t['canonical'],
        'category': t.get('category', ''),
        'stage': t.get('stage', 'nascent'),
        'score': t.get('score', 0),
        'total_mentions': t.get('total_mentions', 0),
    }
    for t in data.get('terms', [])
]
with open(f'$HISTORY_DIR/trends_${DATE}.json', 'w') as f:
    json.dump(snapshot, f)
print(f'  [History] Saved {len(snapshot)} terms to trends_${DATE}.json')
" 2>&1
    log "  [History] OK"
else
    log "  [History] SKIP (tracking/trend_terms.json not found)"
fi

# ─── Step 3.6: Opportunity Analysis ───

log ""
log "--- Step 3.6: Opportunity Analysis ---"

if $PYTHON -m scripts.generate_opportunity 2>&1; then
    log "  [Opportunity] OK"
else
    log "  [Opportunity] FAIL (non-fatal)"
fi

# --- Step 4: Planet Article (DISABLED) ---
# 星球文章生成已禁用 — config.json distribution.planet_article.enabled = false

log ""
log "--- Step 4: Planet Article (DISABLED) ---"
log "  [Article] DISABLED — planet_article generation turned off in config.json"

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

# ─── Step 6d: Workbench Report ───

log ""
log "--- Step 6d: Workbench Report ---"

if $PYTHON -m scripts.update_workbench 2>&1; then
    log "  [Workbench] OK"
else
    log "  [Workbench] FAIL"
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

    # Weekly community deep-dive (30-day lookback on the week's hottest topic)
    if $PYTHON -m scripts.enrich_signals --weekly 2>&1; then
        log "  [WeeklyEnrich] OK"
    else
        log "  [WeeklyEnrich] WARN (non-fatal)"
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

git add public/dashboard/data/dashboard.json tracking/recurring_signals.json tracking/demand_radar.json tracking/trend_terms.json public/sitemap.xml content/reports/ content/articles/ content/trends/ public/*/index.html compare/ daily/*/signals.json 2>&1 || true

if git diff --cached --name-only | grep -q .; then
    git config user.email "pipeline@aimfast.dev"
    git config user.name "AimFast.Dev Bot"
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
