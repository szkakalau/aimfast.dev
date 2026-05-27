"""
Dashboard Data Generator
Reads daily/ + tracking/ data and writes a JSON bundle for the dashboard.
Output: public/dashboard/data/dashboard.json
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAILY_DIR = ROOT / "daily"
TRACKING_DIR = ROOT / "tracking"
OUTPUT_DIR = ROOT / "public" / "dashboard" / "data"

TZ_SHANGHAI = timezone(timedelta(hours=8))


def collect_dashboard_data() -> dict:
    """Collect all dashboard data."""
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")

    # 1. Today's signals
    today_signals = []
    today_path = DAILY_DIR / today / "signals.json"
    if today_path.exists():
        data = json.loads(today_path.read_text(encoding="utf-8"))
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
    report_path = DAILY_DIR / today / "report.md"
    if report_path.exists():
        report_md = report_path.read_text(encoding="utf-8")

    return {
        "date": today,
        "signals": today_signals,
        "summary": today_summary,
        "history": list(reversed(history)),
        "opportunities": opportunities,
        "report_md": report_md,
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
    print(f"[Dashboard] {len(data['signals'])} signals | {len(data['history'])} days history | {len(data['opportunities'])} opportunities")
    return str(output_path)


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    result = run(today)
    if result:
        print(f"\nDashboard data ready: {result}")
