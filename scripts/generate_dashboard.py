"""
Dashboard Data Generator
Reads daily/ + tracking/ data and writes a JSON bundle for the dashboard.
Output: public/dashboard/data/dashboard.json
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from scripts.pipeline_status import read as read_pipeline_status

ROOT = Path(__file__).resolve().parent.parent
DAILY_DIR = ROOT / "daily"
TRACKING_DIR = ROOT / "tracking"
OUTPUT_DIR = ROOT / "public" / "dashboard" / "data"

TZ_SHANGHAI = timezone(timedelta(hours=8))


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

    # 2. History (last 14 days)
    history = []
    for i in range(14):
        d = (datetime.now(TZ_SHANGHAI) - timedelta(days=i)).strftime("%Y-%m-%d")
        signals_path = DAILY_DIR / d / "signals.json"
        if signals_path.exists():
            data = json.loads(signals_path.read_text(encoding="utf-8"))
            summary = data.get("summary", {})
            history.append({
                "date": d,
                "total_signals": data.get("total_raw", len(data.get("signals", []))),
                "top_score": summary.get("top_score", 0),
                "avg_score": summary.get("avg_score", 0),
                "action_qualified": summary.get("action_qualified", 0),
                "cross_platform": summary.get("cross_platform_signals", 0),
            })

    # 3. Opportunity tracking
    opportunities = []
    opp_path = TRACKING_DIR / "opportunities.json"
    if opp_path.exists():
        data = json.loads(opp_path.read_text(encoding="utf-8"))
        opportunities = data.get("opportunities", [])

    # 4. Daily report (markdown)
    report_md = ""
    report_path = DAILY_DIR / effective_date / "report.md"
    if report_path.exists():
        report_md = report_path.read_text(encoding="utf-8")

    # 5. Planet article (markdown + metadata)
    article_md = ""
    article_meta = {}
    article_path = DAILY_DIR / effective_date / "article.md"
    article_json_path = DAILY_DIR / effective_date / "article.json"
    if article_path.exists():
        article_md = article_path.read_text(encoding="utf-8")
    if article_json_path.exists():
        article_meta = json.loads(article_json_path.read_text(encoding="utf-8"))

    # 6. Pipeline status (diagnostics for skipped steps)
    pipeline_status = read_pipeline_status(effective_date)

    return {
        "date": effective_date,
        "signals": today_signals,
        "summary": today_summary,
        "history": list(reversed(history)),
        "opportunities": opportunities,
        "report_md": report_md,
        "article_md": article_md,
        "article_meta": article_meta,
        "pipeline": pipeline_status.get("steps", {}),
        "generated_at": datetime.now(TZ_SHANGHAI).isoformat(),
    }


def run(date_str: str | None = None) -> str:
    """Generate dashboard data JSON."""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    print(f"\n{'='*50}")
    print(f"[Dashboard] Data generation — {date}")
    print(f"{'='*50}")

    data = collect_dashboard_data()
    json_str = json.dumps(data, ensure_ascii=False, indent=2)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "dashboard.json"
    output_path.write_text(json_str, encoding="utf-8")
    print(f"[Dashboard] Data saved → {output_path}")
    print(f"[Dashboard] {len(data['signals'])} signals | {len(data['history'])} days history | {len(data['opportunities'])} opportunities | article: {len(data['article_md']):,} chars")
    return str(output_path)


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    result = run(today)
    if result:
        print(f"\nDashboard data ready: {result}")
