"""
管线全面验证脚本 — 检查所有关键组件是否正常
用法: python scripts/validate_pipeline.py
"""
import json
import re
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TODAY = datetime.now().strftime("%Y-%m-%d")

errors: list[str] = []
warnings: list[str] = []
oks: list[str] = []

def main():
    print("=" * 60)
    print(f"AimFast.Dev Pipeline Validation — {TODAY}")
    print("=" * 60)

    # ── 1. Pipeline Health ──
    print("\n[1] Pipeline Health")
    health_path = ROOT / "tracking/pipeline_health.json"
    if health_path.exists():
        h = json.loads(health_path.read_text(encoding="utf-8"))
        ok = h.get("success", False)
        ec = h.get("exit_code", "?")
        dur = h.get("duration_minutes", 0)
        terms_new = h.get("terms", {}).get("new_today", 0)
        terms_total = h.get("terms", {}).get("total", 0)
        sources_ok = h.get("sources", {}).get("successful", 0)
        sources_total = h.get("sources", {}).get("total", 0)
        consec = h.get("consecutive_success_days", 0)
        warns = h.get("warnings", [])

        status = "[OK]" if ok else "[FAIL]"
        print(f"  Status: {status} | exit_code={ec} | duration={dur}min | streak={consec}d")
        print(f"  Terms: {terms_total} total / +{terms_new} new")
        print(f"  Sources: {sources_ok}/{sources_total} successful")
        if warns:
            for w in warns:
                warnings.append(f"Pipeline warning: {w}")
                print(f"  [WARN] {w}")
        if ok:
            oks.append("Pipeline health: SUCCESS")
        else:
            errors.append("Pipeline health: FAILED")
    else:
        errors.append("Pipeline health report missing")

    # ── 2. Daily Data ──
    print("\n[2] Daily Data")
    daily_dir = ROOT / "daily" / TODAY
    if daily_dir.exists():
        files = list(daily_dir.iterdir())
        print(f"  Files: {len(files)}")
        for f in files:
            size_kb = f.stat().st_size / 1024
            print(f"    {f.name}: {size_kb:.0f} KB")
        if any(f.name == "signals.json" for f in files):
            oks.append("Daily signals.json exists")
        else:
            errors.append("Daily signals.json missing")
        if any(f.name == "extracted_terms.json" for f in files):
            oks.append("Daily extracted_terms.json exists")
    else:
        errors.append(f"daily/{TODAY}/ directory missing")

    # ── 3. Tracking Files ──
    print("\n[3] Tracking Files")
    tracking_checks = {
        "trend_terms.json": "Term database",
        "term_scores.json": "Scoring",
        "term_stages.json": "Lifecycle stages",
        "term_index.json": "Index",
        "token_usage.json": "Token usage",
        "opportunities.json": "Opportunities",
        "demand_radar.json": "Demand radar",
        "canonical_terms.json": "Canonical terms",
        "recurring_signals.json": "Recurring signals",
        "workbench_report.json": "Workbench report",
        "pipeline_health.json": "Pipeline health",
    }
    tracking_dir = ROOT / "tracking"
    for fname, desc in tracking_checks.items():
        path = tracking_dir / fname
        if path.exists():
            size_kb = path.stat().st_size / 1024
            flag = ""
            if size_kb < 1:
                flag = " [SMALL]"
                warnings.append(f"{desc} ({fname}) is very small ({size_kb:.0f} KB)")
            print(f"  {desc}: {size_kb:.0f} KB{flag}")
        else:
            errors.append(f"{desc} ({fname}) missing")

    # ── 4. Content Output ──
    print("\n[4] Content Output")
    reports_dir = ROOT / "content/reports"
    today_reports = list(reports_dir.glob(f"{TODAY}*"))
    print(f"  Today reports: {len(today_reports)}")
    for r in today_reports:
        print(f"    {r.name}")

    terms_dir = ROOT / "content/terms"
    term_files = list(terms_dir.glob("*.md"))
    print(f"  Term pages: {len(term_files)}")

    trends_dir = ROOT / "content/trends"
    trend_files = list(trends_dir.glob("*.md"))
    print(f"  Trend pages: {len(trend_files)}")

    if today_reports:
        oks.append(f"Reports generated ({len(today_reports)})")
    else:
        warnings.append("No reports for today")

    if len(term_files) > 100:
        oks.append(f"Sufficient term pages ({len(term_files)})")
    else:
        warnings.append(f"Low term page count ({len(term_files)})")

    # ── 5. SEO / Public ──
    print("\n[5] SEO / Public Files")
    sitemap = ROOT / "public/sitemap.xml"
    if sitemap.exists():
        content = sitemap.read_text(encoding="utf-8")
        urls = re.findall(r"<loc>(.+?)</loc>", content)
        url_count = len(urls)
        unique_count = len(set(urls))
        dups = url_count - unique_count
        print(f"  sitemap.xml: {url_count} URLs, {unique_count} unique")
        if dups > 0:
            errors.append(f"sitemap.xml has {dups} duplicate URLs")
        else:
            oks.append(f"sitemap.xml clean ({unique_count} URLs)")
    else:
        errors.append("sitemap.xml missing")

    dashboard = ROOT / "public/dashboard/data/dashboard.json"
    if dashboard.exists():
        size_kb = dashboard.stat().st_size / 1024
        print(f"  dashboard.json: {size_kb:.0f} KB")
        oks.append("Dashboard data exists")
    else:
        errors.append("dashboard.json missing")

    lp_index = ROOT / "public/lp-index.json"
    if lp_index.exists():
        print(f"  lp-index.json: {lp_index.stat().st_size / 1024:.0f} KB")
        oks.append("LP index exists")

    # ── 6. Collector Scripts ──
    print("\n[6] Collector Scripts")
    scripts_dir = ROOT / "scripts"
    collector_files = sorted(scripts_dir.glob("collect_*.py"))
    print(f"  Collectors: {len(collector_files)}")
    for cf in collector_files:
        name = cf.stem.replace("collect_", "")
        text = cf.read_text(encoding="utf-8")
        lines = len(text.splitlines())
        has_env = "os.getenv" in text or "os.environ" in text
        env_tag = " [ENV]" if has_env else ""
        print(f"    {name}: {lines} lines{env_tag}")

    # ── 7. Stack Overflow v2.0 ──
    print("\n[7] Stack Overflow v2.0")
    so_path = scripts_dir / "collect_stackoverflow.py"
    so_text = so_path.read_text(encoding="utf-8")
    if "api.stackexchange.com" in so_text:
        oks.append("SO uses Stack Exchange API")
        print("  API: Stack Exchange API v2.3")
    else:
        errors.append("SO not migrated to Stack Exchange API")

    if "xml.etree.ElementTree" not in so_text:
        oks.append("SO RSS/XML dependency removed")
        print("  RSS: removed")
    else:
        errors.append("SO still has RSS dependency")

    so_signal_count = 0
    so_raw = ROOT / "raw" / TODAY / "stackoverflow.json"
    if so_raw.exists():
        data = json.loads(so_raw.read_text(encoding="utf-8"))
        so_signal_count = len(data.get("signals", []))
        print(f"  Local test: {so_signal_count} signals")
        if so_signal_count > 0:
            oks.append(f"SO collector produces data ({so_signal_count} signals)")
        else:
            warnings.append("SO collector returned 0 signals")
    else:
        warnings.append("No local SO test data")

    # ── 8. Product Hunt Security ──
    print("\n[8] Product Hunt Security")
    ph_path = scripts_dir / "collect_producthunt.py"
    ph_text = ph_path.read_text(encoding="utf-8")
    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    ph_cfg = config.get("api_keys", {}).get("producthunt", {})
    ph_cid = ph_cfg.get("client_id", "")

    if "os.getenv" in ph_text:
        oks.append("PH collector supports env vars")
        print("  Env var support: yes")
    else:
        errors.append("PH collector missing env var support")

    if ph_cid == "YOUR_PH_CLIENT_ID":
        oks.append("config.json has placeholder (safe)")
        print("  config.json: placeholder (safe)")
    else:
        errors.append("config.json contains real API key!")

    ph_signal_count = 0
    ph_raw = ROOT / "raw" / TODAY / "producthunt.json"
    if ph_raw.exists():
        data = json.loads(ph_raw.read_text(encoding="utf-8"))
        ph_signal_count = len(data.get("signals", []))
        print(f"  Local test: {ph_signal_count} signals")

    # ── 9. Substack ──
    print("\n[9] Substack")
    ss_raw = ROOT / "raw" / TODAY / "substack.json"
    ss_count = 0
    if ss_raw.exists():
        data = json.loads(ss_raw.read_text(encoding="utf-8"))
        ss_count = len(data.get("signals", []))
        pubs = len(set(
            s.get("extra", {}).get("publication", "?")
            for s in data.get("signals", [])
        ))
        print(f"  Local test: {ss_count} articles from {pubs} newsletters")
        if ss_count > 0:
            oks.append(f"Substack produces data ({ss_count} articles)")
    else:
        warnings.append("No local Substack test data")

    # ── 10. Workflow Config ──
    print("\n[10] GitHub Actions Workflow")
    wf_path = ROOT / ".github/workflows/daily-pipeline.yml"
    if wf_path.exists():
        wf_text = wf_path.read_text(encoding="utf-8")
        checks = [
            ("PRODUCTHUNT_CLIENT_ID", "PH client ID injection"),
            ("PRODUCTHUNT_CLIENT_SECRET", "PH client secret injection"),
            ("DEEPSEEK_API_KEY", "DeepSeek API key injection"),
            ("BUTTONDOWN_API_KEY", "Buttondown API key injection"),
        ]
        for key, desc in checks:
            if key in wf_text:
                oks.append(f"Workflow: {desc}")
                print(f"  {desc}: yes")
            else:
                warnings.append(f"Workflow missing: {desc}")
                print(f"  {desc}: MISSING")
    else:
        errors.append("Workflow file missing")

    # ── 11. Token Usage ──
    print("\n[11] Token Usage")
    token_path = tracking_dir / "token_usage.json"
    if token_path.exists():
        t = json.loads(token_path.read_text(encoding="utf-8"))
        total = t.get("total_tokens", 0)
        calls = t.get("calls", 0)
        print(f"  Total: {total:,} tokens / {calls} calls")
        if total > 0:
            oks.append("Token usage tracked")
        else:
            warnings.append("Token usage is 0")
    else:
        warnings.append("token_usage.json missing")

    # ── Summary ──
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)

    if errors:
        print(f"\n[FAIL] {len(errors)} critical issues:")
        for e in errors:
            print(f"  X  {e}")

    if warnings:
        print(f"\n[WARN] {len(warnings)} warnings:")
        for w in warnings:
            print(f"  !  {w}")

    print(f"\n[PASS] {len(oks)} checks passed:")
    for o in oks:
        print(f"  V  {o}")

    print()
    if errors:
        print("OVERALL: [FAIL] Critical issues detected")
        return 1
    elif warnings:
        print("OVERALL: [WARN] Mostly OK, minor issues")
        return 0
    else:
        print("OVERALL: [PASS] Everything is healthy")
        return 0


if __name__ == "__main__":
    sys.exit(main())
