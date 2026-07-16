"""
Dashboard Data Generator
Reads daily/ + tracking/ data and writes a JSON bundle for the dashboard.
Output: public/dashboard/data/dashboard.json
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.pipeline_status import read as read_pipeline_status

ROOT = Path(__file__).resolve().parent.parent
DAILY_DIR = ROOT / "daily"
TRACKING_DIR = ROOT / "tracking"
OUTPUT_DIR = ROOT / "public" / "dashboard" / "data"

TZ_SHANGHAI = timezone(timedelta(hours=8))


def _collect_archive(max_days: int = 60) -> list[dict]:
    """Collect report.md, article.md, article.json for all available dates (newest first).

    Merged with any pre-existing dashboard.json archive to preserve history when
    daily/ directory is absent or incomplete (e.g. fresh clone, CI, Vercel build).
    """
    # ── 1. Collect fresh entries from daily/ ──
    fresh_entries: dict[str, dict] = {}
    if DAILY_DIR.exists():
        for date_dir in sorted(DAILY_DIR.iterdir(), reverse=True):
            if not date_dir.is_dir():
                continue
            date_str = date_dir.name

            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                continue

            report_path = date_dir / "report.md"
            article_path = date_dir / "article.md"
            article_json_path = date_dir / "article.json"

            has_report = report_path.exists()
            has_article = article_path.exists()

            if not has_report and not has_article:
                continue

            report_en_path = date_dir / "report-en.md"
            article_en_path = date_dir / "article-en.md"
            has_report_en = report_en_path.exists()
            has_article_en = article_en_path.exists()

            try:
                entry = {
                    "date": date_str,
                    "report_md": report_path.read_text(encoding="utf-8") if has_report else "",
                    "article_md": article_path.read_text(encoding="utf-8") if has_article else "",
                    "report_md_en": report_en_path.read_text(encoding="utf-8") if has_report_en else "",
                    "article_md_en": article_en_path.read_text(encoding="utf-8") if has_article_en else "",
                    "article_meta": json.loads(article_json_path.read_text(encoding="utf-8"))
                                    if article_json_path.exists() else None,
                    "has_report": has_report,
                    "has_article": has_article,
                }
                fresh_entries[date_str] = entry
            except Exception as e:
                print(f"[Dashboard] [WARN] Skipping {date_str} in archive: {e}")
                continue

    # ── 2. Inherit entries from existing dashboard.json (survives git clone / CI) ──
    existing_path = OUTPUT_DIR / "dashboard.json"
    inherited = 0
    if existing_path.exists():
        try:
            old_data = json.loads(existing_path.read_text(encoding="utf-8"))
            old_archive = old_data.get("archive", [])
            for old_entry in old_archive:
                old_date = old_entry.get("date", "")
                if old_date and old_date not in fresh_entries:
                    fresh_entries[old_date] = old_entry
                    inherited += 1
        except Exception as e:
            print(f"[Dashboard] [WARN] Could not inherit archive from existing dashboard.json: {e}")

    if inherited:
        print(f"[Dashboard] [inherit] Restored {inherited} archive entries from previous dashboard.json")

    # ── 3. Sort newest-first, cap at max_days ──
    sorted_entries = sorted(fresh_entries.values(), key=lambda e: e["date"], reverse=True)
    return sorted_entries[:max_days]


def _find_latest_date() -> str | None:
    """Find the most recent date that has signals.json in daily/."""
    if not DAILY_DIR.exists():
        return None
    dates = sorted(
        [d.name for d in DAILY_DIR.iterdir() if d.is_dir() and (d / "signals.json").exists()],
        reverse=True,
    )
    return dates[0] if dates else None


def collect_dashboard_data() -> dict:
    """Collect all dashboard data. Falls back to latest available date if today has no data."""
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")

    # Resolve effective date: use today if data exists, else fall back to latest
    today_path = DAILY_DIR / today / "signals.json"
    if today_path.exists():
        effective_date = today
    else:
        latest = _find_latest_date()
        effective_date = latest or today

    # 1. Signals (from effective date)
    today_signals = []
    signals_path = DAILY_DIR / effective_date / "signals.json"
    if signals_path.exists():
        data = json.loads(signals_path.read_text(encoding="utf-8"))
        today_signals = data.get("signals", [])[:30]
        today_summary = data.get("summary", {})
    else:
        today_summary = {}

    # 2. History (last 14 days) — fresh from daily/ + inherited from existing JSON
    history_by_date: dict[str, dict] = {}
    for i in range(14):
        d = (datetime.now(TZ_SHANGHAI) - timedelta(days=i)).strftime("%Y-%m-%d")
        signals_path = DAILY_DIR / d / "signals.json"
        if signals_path.exists():
            try:
                data = json.loads(signals_path.read_text(encoding="utf-8"))
                summary = data.get("summary", {})
                history_by_date[d] = {
                    "date": d,
                    "total_signals": data.get("total_raw", len(data.get("signals", []))),
                    "top_score": summary.get("top_score", 0),
                    "avg_score": summary.get("avg_score", 0),
                    "action_qualified": summary.get("action_qualified", 0),
                    "cross_platform": summary.get("cross_platform_signals", 0),
                }
            except Exception as e:
                print(f"[Dashboard] [WARN] Skipping history {d}: {e}")

    # Inherit history from existing dashboard.json for dates missing in daily/
    existing_dashboard = OUTPUT_DIR / "dashboard.json"
    if existing_dashboard.exists():
        try:
            old = json.loads(existing_dashboard.read_text(encoding="utf-8"))
            for h in old.get("history", []):
                hd = h.get("date", "")
                if hd and hd not in history_by_date:
                    history_by_date[hd] = h
        except Exception:
            pass

    history = [history_by_date[d] for d in sorted(history_by_date, reverse=True)]

    # 3. Opportunity tracking
    opportunities = []
    opp_path = TRACKING_DIR / "opportunities.json"
    if opp_path.exists():
        data = json.loads(opp_path.read_text(encoding="utf-8"))
        opportunities = data.get("opportunities", [])

    # 3b. Recurring signals tracking
    recurring_signals = []
    rec_path = TRACKING_DIR / "recurring_signals.json"
    if rec_path.exists():
        try:
            data = json.loads(rec_path.read_text(encoding="utf-8"))
            recurring_signals = data.get("recurring", [])
        except Exception as e:
            print(f"[Dashboard] [WARN] Failed to read recurring_signals.json: {e}")

    # 3c. Demand radar
    demand_radar = {}
    radar_path = TRACKING_DIR / "demand_radar.json"
    if radar_path.exists():
        try:
            demand_radar = json.loads(radar_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[Dashboard] [WARN] Failed to read demand_radar.json: {e}")

    # 3d. Workbench report
    workbench_report = {}
    wb_path = TRACKING_DIR / "workbench_report.json"
    if wb_path.exists():
        try:
            workbench_report = json.loads(wb_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[Dashboard] [WARN] Failed to read workbench_report.json: {e}")

    # 3e. Bets / decision log
    bets_data = {}
    bets_path = TRACKING_DIR / "bets.json"
    if bets_path.exists():
        try:
            bets_data = json.loads(bets_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[Dashboard] [WARN] Failed to read bets.json: {e}")

    # 3f. Watchlist
    watchlist_data = {}
    wl_path = TRACKING_DIR / "watchlist.json"
    if wl_path.exists():
        try:
            watchlist_data = json.loads(wl_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[Dashboard] [WARN] Failed to read watchlist.json: {e}")

    # 3g. Lessons (failure knowledge base)
    lessons_data = []
    lessons_path = TRACKING_DIR / "lessons.json"
    if lessons_path.exists():
        try:
            lessons_raw = json.loads(lessons_path.read_text(encoding="utf-8"))
            lessons_data = lessons_raw.get("lessons", [])
        except Exception as e:
            print(f"[Dashboard] [WARN] Failed to read lessons.json: {e}")

    # 3h. Competitor tracking targets (for Dashboard UI)
    competitor_targets = []
    ct_path = TRACKING_DIR / "competitor_targets.json"
    if ct_path.exists():
        try:
            ct_data = json.loads(ct_path.read_text(encoding="utf-8"))
            competitor_targets = ct_data.get("targets", [])
        except Exception as e:
            print(f"[Dashboard] [WARN] Failed to read competitor_targets.json: {e}")

    # 3i. Competitor intelligence (LLM-generated daily)
    competitor_intel = {}
    ci_path = DAILY_DIR / effective_date / "competitor_intel.json"
    if ci_path.exists():
        try:
            competitor_intel = json.loads(ci_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[Dashboard] [WARN] Failed to read competitor_intel.json: {e}")

    # 4. Daily report (markdown) — bilingual: zh (default) + en (optional)
    report_md = ""
    report_md_en = ""
    report_path = DAILY_DIR / effective_date / "report.md"
    report_en_path = DAILY_DIR / effective_date / "report-en.md"
    if report_path.exists():
        report_md = report_path.read_text(encoding="utf-8")
    if report_en_path.exists():
        report_md_en = report_en_path.read_text(encoding="utf-8")

    # 4b. Decision (structured, from report LLM extraction — feeds Dashboard 今日决策 card)
    decision = {}
    decision_path = DAILY_DIR / effective_date / "decision.json"
    if decision_path.exists():
        try:
            decision = json.loads(decision_path.read_text(encoding="utf-8"))
            print(f"[Dashboard] Decision data loaded: {decision.get('product_name', 'unnamed')}")
        except Exception as e:
            print(f"[Dashboard] [WARN] Failed to read decision.json: {e}")

    # 5. Planet article (markdown + metadata) — bilingual
    article_md = ""
    article_md_en = ""
    article_meta = {}
    article_path = DAILY_DIR / effective_date / "article.md"
    article_en_path = DAILY_DIR / effective_date / "article-en.md"
    article_json_path = DAILY_DIR / effective_date / "article.json"
    if article_path.exists():
        article_md = article_path.read_text(encoding="utf-8")
    if article_en_path.exists():
        article_md_en = article_en_path.read_text(encoding="utf-8")
    if article_json_path.exists():
        article_meta = json.loads(article_json_path.read_text(encoding="utf-8"))

    # 6. Pipeline status (diagnostics for skipped steps)
    pipeline_status = read_pipeline_status(effective_date)

    # 7. Archive (all available historical reports + articles)
    archive = _collect_archive(max_days=60)
    # Trim archive content to keep dashboard.json under ~500KB
    for entry in archive:
        if entry.get("report_md"):
            entry["report_md"] = entry["report_md"][:1500]
        if entry.get("report_md_en"):
            entry["report_md_en"] = entry["report_md_en"][:1500]
        if entry.get("article_md"):
            entry["article_md"] = entry["article_md"][:1000]
        if entry.get("article_md_en"):
            entry["article_md_en"] = entry["article_md_en"][:1000]

    return {
        "date": effective_date,
        "signals": today_signals,
        "summary": today_summary,
        "history": list(reversed(history)),
        "opportunities": opportunities,
        "recurring_signals": recurring_signals,
        "demand_radar": demand_radar,
        "workbench": workbench_report,
        "bets": bets_data.get("bets", []),
        "lessons": lessons_data,
        "watchlist": watchlist_data.get("watched", []),
        "competitor_targets": competitor_targets,
        "competitor_intel": competitor_intel,
        "decision": decision,
        "report_md": report_md,
        "report_md_en": report_md_en,
        "article_md": article_md,
        "article_md_en": article_md_en,
        "article_meta": article_meta,
        "pipeline": pipeline_status.get("steps", {}),
        "archive": archive,
        "generated_at": datetime.now(TZ_SHANGHAI).isoformat(),
    }


def _save_trend_history_snapshot(date_str: str) -> int:
    """Generate daily trend snapshot for watchlist delta computation.

    Reads tracking/trend_terms.json and writes a slim JSON array
    (id, canonical, category, stage, score, total_mentions) to
    public/dashboard/data/history/trends_{date_str}.json.
    Returns the number of terms written, or 0 on failure.
    """
    history_dir = OUTPUT_DIR / "history"
    snapshot_path = history_dir / f"trends_{date_str}.json"
    if snapshot_path.exists():
        return -1  # already exists

    terms_path = TRACKING_DIR / "trend_terms.json"
    if not terms_path.exists():
        print("[Dashboard] [History] trend_terms.json not found, skipping snapshot")
        return 0

    try:
        data = json.loads(terms_path.read_text(encoding="utf-8"))
        terms = data.get("terms", []) if isinstance(data, dict) else data
    except Exception as e:
        print(f"[Dashboard] [History] Failed to read trend_terms.json: {e}")
        return 0

    history_terms = []
    for t in terms:
        history_terms.append({
            "id": t.get("id", ""),
            "canonical": t.get("canonical", ""),
            "category": t.get("category", "General"),
            "stage": t.get("stage", "nascent"),
            "score": t.get("score", 0),
            "total_mentions": t.get("total_mentions", 0),
        })
    history_terms.sort(key=lambda t: t["score"], reverse=True)

    history_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(
        json.dumps(history_terms, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[Dashboard] [History] Snapshot saved → trends_{date_str}.json ({len(history_terms)} terms)")
    return len(history_terms)


def run(date_str: str | None = None) -> str:
    """Generate dashboard data JSON."""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    print(f"\n{'='*50}")
    print(f"[Dashboard] Data generation — {date}")
    print(f"{'='*50}")

    data = collect_dashboard_data()

    # ── 防御性校验：archive 异常时告警（但继续写入，不阻塞管道）──
    archive_count = len(data.get("archive", []))
    history_count = len(data.get("history", []))
    daily_dir_count = len([d for d in DAILY_DIR.iterdir() if d.is_dir()]) if DAILY_DIR.exists() else 0
    if archive_count < 3 and daily_dir_count < 3:
        # Only warn when we have reason to expect more (enough daily dirs exist)
        pass
    elif archive_count < 3 and daily_dir_count >= 3:
        print(f"[Dashboard] [WARN] WARNING: archive 仅 {archive_count} 条，但 daily/ 下有 {daily_dir_count} 个日期目录 — 可能存在上游数据缺失（report.md/article.md 未生成）")
    if history_count < 3 and daily_dir_count >= 3:
        print(f"[Dashboard] [WARN] WARNING: history 仅 {history_count} 条，但 daily/ 下有 {daily_dir_count} 个日期目录 — 检查 signals.json 是否完整")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    output_path = OUTPUT_DIR / "dashboard.json"
    output_path.write_text(json_str, encoding="utf-8")
    demand_count = len(data.get('demand_radar', {}).get('demands', []))
    print(f"[Dashboard] Data saved → {output_path}")
    art_zh = len(data['article_md'])
    art_en = len(data['article_md_en'])
    intel_count = len(data.get('competitor_intel', {}).get('targets', []))
    print(f"[Dashboard] {len(data['signals'])} signals | {len(data['history'])} days history | {len(data['opportunities'])} opportunities | {len(data['recurring_signals'])} recurring | {demand_count} demands | {intel_count} competitor intel | article: {art_zh} chars (zh) / {art_en} chars (en)")

    # ── Trend history snapshot for watchlist delta computation ──
    _save_trend_history_snapshot(date)

    return str(output_path)


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    result = run(today)
    if result:
        print(f"\nDashboard data ready: {result}")
