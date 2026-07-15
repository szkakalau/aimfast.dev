"""
One-time fix: normalize category casing in trend_terms.json.

Fixes:
  - "product" → "Productivity" (legacy mapping)
  - "project" → "OpenSource" (legacy mapping)
  - "infrastructure" → "Infra"
  - "ai/llm" → "AIModel" (legacy mapping)
  - "hottopic" → "Industry" (legacy mapping)
  - Any other lowercase → title case matching the canonical set

Usage: python scripts/fix_category_case.py [--dry-run]
"""
import json
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from defaults import atomic_write_json

TZ_SHANGHAI = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parent.parent
TRACKING_FILE = ROOT / "tracking" / "trend_terms.json"

# Canonical category set (matching LLM prompt in generate_trends.py)
CANONICAL_CATEGORIES = {
    "aimodel": "AIModel",
    "ai model": "AIModel",
    "ai/llm": "AIModel",
    "llm": "AIModel",
    "aiagent": "AIAgent",
    "ai agent": "AIAgent",
    "agent": "AIAgent",
    "aiapp": "AIApp",
    "ai app": "AIApp",
    "techconcept": "TechConcept",
    "devtools": "DevTools",
    "infra": "Infra",
    "infrastructure": "Infra",
    "opensource": "OpenSource",
    "open source": "OpenSource",
    "project": "OpenSource",
    "dx": "DX",
    "productivity": "Productivity",
    "product": "Productivity",
    "consumer": "Consumer",
    "industry": "Industry",
    "hottopic": "Industry",
    "design": "Design",
}

# Additional normalization: title-case any unknown categories
# (handles future LLM variations we haven't seen yet)


def normalize_category(cat: str) -> str:
    """Normalize a category string to canonical form."""
    if not cat or not cat.strip():
        return "General"
    cat = cat.strip()
    key = cat.lower()
    if key in CANONICAL_CATEGORIES:
        return CANONICAL_CATEGORIES[key]
    # Unknown category: apply title casing as fallback
    return cat[0].upper() + cat[1:]


def main():
    parser = argparse.ArgumentParser(description="Fix category casing in trend_terms.json")
    parser.add_argument("--dry-run", action="store_true", help="Don't write file")
    args = parser.parse_args()

    if not TRACKING_FILE.exists():
        print(f"[fix-category] File not found: {TRACKING_FILE}")
        return

    with open(TRACKING_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    terms = data.get("terms", [])
    fixed = 0
    changes: list[tuple[str, str, str]] = []

    for term in terms:
        old_cat = term.get("category", "")
        new_cat = normalize_category(old_cat)
        if old_cat != new_cat:
            changes.append((term.get("canonical", "?"), old_cat, new_cat))
            term["category"] = new_cat
            fixed += 1

    if fixed == 0:
        print("[fix-category] All categories already normalized — nothing to fix")
        return

    print(f"[fix-category] {fixed} terms with non-canonical categories:")
    for canonical, old, new in changes:
        print(f"  {canonical:40s}  {old:20s} → {new}")

    if not args.dry_run:
        data["updated_at"] = datetime.now(TZ_SHANGHAI).isoformat()
        atomic_write_json(TRACKING_FILE, data)
        print(f"\n[fix-category] Atomically saved to {TRACKING_FILE}")
    else:
        print("\n[fix-category] DRY RUN — no file written")

    # Print final distribution
    dist: dict[str, int] = {}
    for term in terms:
        c = term.get("category", "Unknown")
        dist[c] = dist.get(c, 0) + 1
    print("\n[fix-category] Final category distribution:")
    for cat, count in sorted(dist.items(), key=lambda x: -x[1]):
        print(f"  {cat:20s} {count:3d}")


if __name__ == "__main__":
    main()
