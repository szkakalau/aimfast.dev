#!/usr/bin/env bash
# AimFast.Dev — Daily Pipeline Orchestrator (Linux / CI)
# Usage: bash scripts/daily_run.sh
# GitHub Actions triggers this daily at 01:00 UTC (09:00 CST)

set -euo pipefail

# ── Pipeline Exit Code Tracking ─────────────────────────
PIPELINE_EXIT_CODE=1  # default to failure, set to 0 on success
EXIT_CODE_FILE=""
trap '_exit_code=$?; [ -n "$EXIT_CODE_FILE" ] && echo "PIPELINE_EXIT_CODE=$_exit_code" >> "$EXIT_CODE_FILE"; exit $_exit_code' EXIT

export TZ=Asia/Shanghai

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DATE=$(date +%Y-%m-%d)
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/$DATE.log"
EXIT_CODE_FILE="$LOG_DIR/.exit_code"

cd "$PROJECT_ROOT"

mkdir -p "$LOG_DIR"
echo "" > "$EXIT_CODE_FILE"

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

# ── Step Timing ──────────────────────────────────────
STEP_START=0
step_start() { STEP_START=$(date +%s); }
step_end() {
    local name="$1"
    local elapsed=$(($(date +%s) - STEP_START))
    local line="[TIMING] $name: ${elapsed}s"
    echo "$line"
    echo "$line" >> "$LOG_FILE"
    # 超过 5 分钟的步骤标记为 WARN
    if [ $elapsed -gt 300 ]; then
        local warn="[TIMING] ⚠️ $name took ${elapsed}s (>5min)"
        echo "$warn" >&2
        echo "$warn" >> "$LOG_FILE"
    fi
}

# ── Failure Tracking ─────────────────────────────────
FAILED_STEPS=""
track_failure() {
    local step_name="$1"
    FAILED_STEPS="$FAILED_STEPS$step_name, "
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
step_start

COLLECTORS=(
    # ── 慢采集器前置（尽早开始，与后续采集器重叠）──
    "Reddit (11 subs):collect_reddit"
    "Reddit Consumer:collect_reddit_consumer"
    "X/Twitter:collect_x"
    "Substack:collect_substack"
    "HuggingFace:collect_huggingface"
    "GitHub Deep:collect_github"
    "GitHub Releases:collect_github_releases"
    "Semantic Scholar:collect_semanticscholar"
    "YouTube:collect_youtube"
    # ── 中等速度 ──
    "Hacker News:collect_hackernews"
    "Product Hunt:collect_producthunt"
    "DEV Community:collect_devcommunity"
    "V2EX:collect_v2ex"
    "w2solo:collect_w2solo"
    "Lobsters:collect_lobsters"
    "ArXiv:collect_arxiv"
    "豆瓣:collect_douban"
    "npm:collect_npm"
    "PyPI:collect_pypi"
    "Stack Overflow:collect_stackoverflow"
    # "小红书:collect_xiaohongshu"  # 暂禁用 — 未认证模式数据量有限
    # ── 快速采集器 ──
    "Google Trends:collect_trends"
    "Job Trends:collect_job_trends"
    "Product Changelogs:collect_changelogs"
    "Google News:collect_googlenews"
    "掘金:collect_juejin"
    "SegmentFault:collect_segmentfault"
    "OSChina:collect_oschina"
    "Show HN:collect_showhn"
)

# C-end collectors are non-blocking — they may fail due to rate limits or missing auth
C_END_COLLECTORS=("Reddit Consumer" "豆瓣" "小红书" "X/Twitter" "Product Changelogs" "Google News" "GitHub Releases" "npm" "PyPI" "Stack Overflow" "YouTube" "Job Trends" "Substack" "掘金" "SegmentFault" "Semantic Scholar" "OSChina" "Show HN")

# Parallel execution with concurrency cap — tuned for I/O-bound collectors
# 28 collectors × avg 4s each: 6 workers ≈ 20s, 14 workers ≈ 8s
MAX_PARALLEL=14
running=0
collector_total=${#COLLECTORS[@]}
collector_done=0
collector_ok=0
collector_warn=0
collector_error=0

for entry in "${COLLECTORS[@]}"; do
    name="${entry%%:*}"
    script="${entry##*:}"

    # Wait until a slot opens up
    while [ $running -ge $MAX_PARALLEL ]; do
        if wait -n 2>/dev/null; then
            :  # child exited successfully
        fi
        running=$((running - 1))
        collector_done=$((collector_done + 1))
    done

    (
        if $PYTHON -m "scripts.$script" 2>&1; then
            echo "OK"
        else
            rc=$?
            if [[ " ${C_END_COLLECTORS[*]} " =~ " ${name} " ]]; then
                echo "WARN:$rc"
            else
                echo "ERROR:$rc"
            fi
        fi
    ) > "$DAILY_DIR/.collector_${name//\//_}.log" 2>&1 &
    running=$((running + 1))
done

# Wait for remaining background jobs
while [ $running -gt 0 ]; do
    if wait -n 2>/dev/null; then
        :  # child exited successfully
    fi
    running=$((running - 1))
    collector_done=$((collector_done + 1))
done

# Read back collector results and log them
for entry in "${COLLECTORS[@]}"; do
    name="${entry%%:*}"
    log_file="$DAILY_DIR/.collector_${name//\//_}.log"
    if [ -f "$log_file" ]; then
        result=$(tail -1 "$log_file" 2>/dev/null || echo "UNKNOWN")
        case "$result" in
            OK) log "  [$name] OK" ;;
            WARN:*) log "  [$name] WARN (non-blocking C-end collector, exit=${result#WARN:})" ;;
            ERROR:*) log "  [$name] ERROR (exit=${result#ERROR:})" ;;
            *) log "  [$name] UNKNOWN (check $log_file)" ;;
        esac
        rm -f "$log_file"
    else
        log "  [$name] NO_LOG (collector may have crashed)"
    fi
done

step_end "Step1: Collectors (${#COLLECTORS[@]} sources)"

# ─── Step 2: Signal Processing ───

log ""
log "--- Step 2: Signal Processing ---"
step_start

if $PYTHON -m scripts.process_signals 2>&1; then
    log "  [Process] OK"
else
    log "  [Process] FAIL"
    track_failure "ProcessSignals"
fi

step_end "Step2: ProcessSignals"

# ═══ Step 2.1: Term Extraction (NLP Entity Extraction + Cross-Source Term DB) ═══
# Moved AFTER process_signals so fallback to daily/{date}/signals.json works (bottleneck #5 fix)

log ""
log "--- Step 2.1: Term Extraction (LLM NER + Cross-Source DB) ---"
step_start

if $PYTHON -m scripts.extract_terms 2>&1; then
    log "  [TermExtract] OK"
else
    log "  [TermExtract] WARN (non-fatal — term index not updated)"
    track_failure "TermExtract"
fi

step_end "Step2.1: TermExtract"

# ═══ Step 2.2-2.4: Term Normalization + Classification + Scoring (local) ═══

log ""
log "--- Step 2.2-2.4: Term Normalization + Classification + Scoring ---"
step_start

if $PYTHON -m scripts.normalize_terms 2>&1; then
    log "  [Norm] OK"
else
    log "  [Norm] WARN (non-fatal — normalization skipped)"
fi

if $PYTHON -m scripts.classify_terms 2>&1; then
    log "  [Stages] OK"
else
    log "  [Stages] WARN (non-fatal)"
fi

if $PYTHON -m scripts.score_terms 2>&1; then
    log "  [Scores] OK"
else
    log "  [Scores] WARN (non-fatal)"
fi

step_end "Step2.2-2.4: Norm+Classify+Score"

# ═══ Step 2.5: Term Research Reports (DEPRECATED — kept for backward compat) ═══

log ""
log "--- Step 2.5: Term Research Reports (DEPRECATED, fast no-op) ---"

if $PYTHON -m scripts.generate_term_research 2>&1; then
    log "  [Research] OK"
else
    log "  [Research] WARN (non-fatal)"
fi

# ─── Step 2.6: Enrich Top Signals with /last30days ───

log ""
log "--- Step 2.5: Community Enrichment (/last30days) ---"
step_start

if $PYTHON -m scripts.enrich_signals 2>&1; then
    log "  [Enrich] OK"
else
    log "  [Enrich] WARN (non-fatal)"
    track_failure "Enrich"
fi

step_end "Step2.5: Enrich"

# ─── Step 2.6: Cross-Source Term Validation ───

log ""
log "--- Step 2.6: Cross-Source Term Validation ---"
step_start

if $PYTHON -m scripts.cross_validate_terms 2>&1; then
    log "  [CrossVal] OK"
else
    log "  [CrossVal] WARN (non-fatal)"
    track_failure "CrossVal"
fi

step_end "Step2.6: CrossVal"

# ─── Step 3: Daily Report ───

log ""
log "--- Step 3: Daily Report ---"
step_start

if $PYTHON -m scripts.generate_report 2>&1; then
    log "  [Report] OK"
else
    log "  [Report] FAIL"
    track_failure "DailyReport"
fi

step_end "Step3: DailyReport"

# ─── Step 3.5: Trend Discovery ───

log ""
log "--- Step 3.5: Trend Discovery ---"
step_start

if $PYTHON -m scripts.generate_trends --rescore 2>&1; then
    log "  [Trends] OK"
else
    log "  [Trends] FAIL (non-fatal)"
    track_failure "Trends"
fi

step_end "Step3.5: Trends"

# ─── Step 3.5b: Save trend terms snapshot for Dashboard history ───
log ""
log "--- Step 3.5b: Trend History Snapshot ---"
step_start
HISTORY_DIR="public/dashboard/data/history"
mkdir -p "$HISTORY_DIR"
if [ -f tracking/trend_terms.json ]; then
    DATE=${DATE_OVERRIDE:-$(date +%Y-%m-%d)}
    # Extract lightweight snapshot: only fields needed by Dashboard Watchlist delta computation
    $PYTHON -c "
import json, sys
with open('tracking/trend_terms.json', encoding='utf-8') as f:
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
with open(f'$HISTORY_DIR/trends_${DATE}.json', 'w', encoding='utf-8') as f:
    json.dump(snapshot, f)
print(f'  [History] Saved {len(snapshot)} terms to trends_${DATE}.json')
" 2>&1
    log "  [History] OK"
else
    log "  [History] SKIP (tracking/trend_terms.json not found)"
    track_failure "HistorySnapshot"
fi

step_end "Step3.5b: HistorySnapshot"

# ─── Step 3.6: Opportunity Analysis ───

log ""
log "--- Step 3.6: Opportunity Analysis ---"
step_start

if $PYTHON -m scripts.generate_opportunity 2>&1; then
    log "  [Opportunity] OK"
else
    log "  [Opportunity] FAIL (non-fatal)"
    track_failure "Opportunity"
fi

step_end "Step3.6: Opportunity"

# ─── Step 3.7: Extract Term Relations ───

log ""
log "--- Step 3.7: Extract Term Relations ---"
step_start

if $PYTHON scripts/extract_related_terms.py --date "$DATE" 2>&1; then
    log "  [Relations] OK"
else
    log "  [Relations] FAIL (non-fatal)"
fi

step_end "Step3.7: Relations"

# --- Step 4: Planet Article (DISABLED) ---

log ""
log "--- Step 4: Planet Article (DISABLED) ---"
log "  [Article] DISABLED — planet_article generation turned off in config.json"

# ─── Step 5: Action Plan ───

log ""
log "--- Step 5: Action Plan ---"
step_start

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
    track_failure "Action"
fi

step_end "Step5: Action"

# ─── Step 6: Tracking Update ───

log ""
log "--- Step 6: Tracking Update ---"
step_start

if $PYTHON -m scripts.update_tracking 2>&1; then
    log "  [Tracking] OK"
else
    log "  [Tracking] FAIL"
    track_failure "Tracking"
fi

step_end "Step6: Tracking"

# ─── Step 6b: Recurring Signal Tracking ───

log ""
log "--- Step 6b: Recurring Signal Tracking ---"
step_start

if $PYTHON -m scripts.track_recurring 2>&1; then
    log "  [Recurring] OK"
else
    log "  [Recurring] FAIL"
    track_failure "Recurring"
fi

step_end "Step6b: Recurring"

# ─── Step 6c: Demand Radar ───

log ""
log "--- Step 6c: Demand Radar ---"
step_start

if $PYTHON -m scripts.track_demands 2>&1; then
    log "  [DemandRadar] OK"
else
    log "  [DemandRadar] FAIL"
    track_failure "DemandRadar"
fi

step_end "Step6c: DemandRadar"

# ─── Step 6d: Workbench Report ───

log ""
log "--- Step 6d: Workbench Report ---"
step_start

if $PYTHON -m scripts.update_workbench 2>&1; then
    log "  [Workbench] OK"
else
    log "  [Workbench] FAIL"
    track_failure "Workbench"
fi

step_end "Step6d: Workbench"

# ─── Step 7: Landing Page ───

log ""
log "--- Step 7: Landing Page ---"
step_start

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
    track_failure "LandingPage"
fi

step_end "Step7: LandingPage"

# ─── Step 8: Translate Content (zh → en) ───

log ""
log "--- Step 9: Translate Content (zh → en) ---"
step_start

if $PYTHON -m scripts.translate_content 2>&1; then
    log "  [Translate] OK"
else
    log "  [Translate] FAIL (non-fatal)"
    track_failure "Translate"
fi

step_end "Step8: Translate"

# ─── Step 10: SEO Content Files ───

log ""
log "--- Step 10: SEO Content Files ---"
step_start

if $PYTHON -m scripts.generate_seo_files 2>&1; then
    log "  [SEO] OK"
else
    log "  [SEO] FAIL (non-fatal)"
    track_failure "SEO"
fi

step_end "Step10: SEO"

# ─── Step 11: Dashboard ───

log ""
log "--- Step 11: Dashboard ---"
step_start

if $PYTHON -m scripts.generate_dashboard 2>&1; then
    log "  [Dashboard] OK"
else
    log "  [Dashboard] FAIL"
    track_failure "Dashboard"
fi

# Deep Analysis cards (extract from high-score trend reports)
if $PYTHON scripts/generate_dashboard_deep_analysis.py 2>&1; then
    log "  [DeepAnalysis] OK"
else
    log "  [DeepAnalysis] FAIL (non-fatal)"
fi

step_end "Step11: Dashboard"

# ─── Step 12: Weekly Report (Sunday only) ───

if [ "$(date +%u)" -eq 7 ]; then
    log ""
    log "--- Step 12: Weekly Report (Sunday trigger) ---"
    step_start
    if $PYTHON -m scripts.generate_weekly 2>&1; then
        log "  [Weekly] OK"
    else
        log "  [Weekly] FAIL"
        track_failure "Weekly"
    fi

    # Weekly community deep-dive (30-day lookback on the week's hottest topic)
    if $PYTHON -m scripts.enrich_signals --weekly 2>&1; then
        log "  [WeeklyEnrich] OK"
    else
        log "  [WeeklyEnrich] WARN (non-fatal)"
    fi
    step_end "Step12: Weekly"
fi

# ─── Step 12b: BuilderPulse 对比 ───

log ""
log "--- Step 12b: BuilderPulse Comparison ---"
step_start

if $PYTHON -m scripts.compare_with_builderpulse --date "$DATE" 2>&1; then
    log "  [Compare] OK"
else
    log "  [Compare] FAIL (non-blocking)"
    track_failure "BuilderPulse"
fi

step_end "Step12b: BuilderPulse"

# ─── Step 13b: Pipeline Health Dashboard ───
# Write exit code BEFORE health check runs — the trap only fires on script exit,
# which happens after this step.  Without this, pipeline_health.py always reads
# an empty .exit_code file and reports false negatives.

log ""
log "--- Step 13b: Pipeline Health Dashboard ---"

# Persist current failure state for the health script to consume
if [ -z "$FAILED_STEPS" ]; then
    echo "PIPELINE_EXIT_CODE=0" > "$EXIT_CODE_FILE"
else
    echo "PIPELINE_EXIT_CODE=1" > "$EXIT_CODE_FILE"
fi
# Also copy the log so timing parser can find it (normally done at script exit)
cp "$LOG_FILE" "$DAILY_DIR/pipeline.log" 2>/dev/null || true

step_start

if $PYTHON scripts/pipeline_health.py 2>&1; then
    log "  [Health] OK"
else
    log "  [Health] WARN (non-fatal)"
    track_failure "PipelineHealth"
fi

step_end "Step13b: PipelineHealth"

# ─── Step 13: Git commit & push ───

log ""
log "--- Step 13: Deploy Dashboard Data & SEO Content ---"

git add public/dashboard/data/dashboard.json tracking/recurring_signals.json tracking/demand_radar.json tracking/trend_terms.json tracking/pipeline_health.json public/sitemap.xml content/reports/ content/articles/ content/trends/ public/*/index.html compare/ daily/*/signals.json daily/*/extracted_terms.json 2>&1 || true

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
    log ""
    log "--- Pipeline Diagnostics ---"
    log "Failed steps: ${FAILED_STEPS:-none}"
    for f in tracking/trend_terms.json tracking/term_index.json tracking/token_usage.json content/trends/ public/dashboard/data/dashboard.json; do
        if [ -f "$f" ]; then
            log "[DIAG] $f: $(wc -c < "$f") bytes"
        else
            log "[DIAG] $f: MISSING"
        fi
    done
    # Count generated content files
    TREND_COUNT=$(find content/trends/ -name "*.md" -newer "$DAILY_DIR" 2>/dev/null | wc -l)
    log "[DIAG] Recently modified trend files: $TREND_COUNT"
fi

# ─── Summary ───

log ""
PIPELINE_EXIT_CODE=0
log "=== Pipeline Complete ==="
log "Failed steps: ${FAILED_STEPS:-none}"

# Write lock file
echo "done" > "$LOCK_FILE"

if [ -d "$DAILY_DIR" ]; then
    log "Output: $(ls -1 "$DAILY_DIR" | tr '\n' ' ')"
fi

log "Log: $LOG_FILE"

# Copy log to daily dir for archival
cp "$LOG_FILE" "$DAILY_DIR/pipeline.log" 2>/dev/null || true
