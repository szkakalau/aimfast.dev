"""
Backfill trend history snapshots from git history.

Reads tracking/trend_terms.json from past git commits (one per day marked
"Dashboard data update"), extracts id/canonical/category/stage/score/total_mentions,
and writes public/dashboard/data/history/trends_YYYY-MM-DD.json for each date.

Usage: python scripts/backfill_history.py
"""
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HISTORY_DIR = ROOT / "public" / "dashboard" / "data" / "history"
TRACKING_FILE = "tracking/trend_terms.json"

TZ_SHANGHAI = timezone(timedelta(hours=8))


def get_dated_commits() -> list[tuple[str, str]]:
    """Get (date_str, commit_hash) pairs from git log of trend_terms.json."""
    result = subprocess.run(
        ["git", "log", "--oneline", "--format=%H %ad", "--date=short", "--", TRACKING_FILE],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT),
    )
    if result.returncode != 0:
        print(f"[backfill] git log failed: {result.stderr}")
        return []

    commits = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split()
        commit_hash = parts[0]
        date_str = parts[1]
        commits.append((date_str, commit_hash))

    # Keep only the LAST commit per date (end-of-day state)
    seen = {}
    for date_str, commit_hash in commits:
        if date_str not in seen:
            seen[date_str] = commit_hash
    return [(d, h) for d, h in seen.items()]


def extract_trends_from_commit(commit_hash: str, date_str: str) -> list[dict]:
    """Extract trend terms from a specific git commit."""
    result = subprocess.run(
        ["git", "show", f"{commit_hash}:{TRACKING_FILE}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT),
    )
    if result.returncode != 0:
        print(f"  [backfill] git show failed for {commit_hash} ({date_str}): {result.stderr}")
        return []

    if not result.stdout:
        print(f"  [backfill] git show returned empty for {commit_hash} ({date_str})")
        return []

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"  [backfill] JSON parse failed for {date_str}: {e}")
        return []

    terms = data.get("terms", []) if isinstance(data, dict) else data

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

    # Sort by score descending (consistent with today's file)
    history_terms.sort(key=lambda t: t["score"], reverse=True)
    return history_terms


def main():
    print("[backfill] Scanning git history for trend_terms.json snapshots...")
    commits = get_dated_commits()
    print(f"[backfill] Found {len(commits)} dated commits")

    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    generated = 0
    skipped = 0
    for date_str, commit_hash in sorted(commits):
        output_path = HISTORY_DIR / f"trends_{date_str}.json"
        if output_path.exists():
            print(f"  [backfill] Skip {date_str} — already exists")
            skipped += 1
            continue

        terms = extract_trends_from_commit(commit_hash, date_str)
        if not terms:
            continue

        output_path.write_text(
            json.dumps(terms, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"  [backfill] Generated trends_{date_str}.json ({len(terms)} terms)")
        generated += 1

    print(f"\n[backfill] Done: {generated} generated, {skipped} skipped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
