"""
Generate deep_analysis.json for the Dashboard Deep Analysis section.

Reads the 19 high-score (≥70) trend terms and their research markdown files,
extracts key sections for Dashboard cards: TAM, MVP blueprint, pricing, risk, action plan.

Output: public/dashboard/data/deep_analysis.json

Usage: python scripts/generate_dashboard_deep_analysis.py
"""
import json
import re
from pathlib import Path
from datetime import datetime, timezone, timedelta

TZ_SHANGHAI = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parent.parent
TRENDS_DIR = ROOT / "content" / "trends"
TRACKING_FILE = ROOT / "tracking" / "trend_terms.json"
OUTPUT_DIR = ROOT / "public" / "dashboard" / "data"
OUTPUT_FILE = OUTPUT_DIR / "deep_analysis.json"

# Sections to extract (english names as keys, used in card display)
SECTION_KEYS = {
    "tam": ["TAM & Market Size", "TAM &amp; Market Size"],
    "mvp": ["MVP Blueprint"],
    "business_model": ["Business Model"],
    "risk": ["Risk Assessment"],
    "action": ["Action Plan"],
    "what": ["What is it"],
    "why_now": ["Why now"],
    "competitive": ["Competitive Landscape"],
}

MIN_SCORE = 70
MAX_TERMS = 19


def extract_section(body: str, section_names: list[str]) -> str:
    """Extract the content of a named ## section from markdown body."""
    lines = body.split("\n")
    in_section = False
    content: list[str] = []

    for line in lines:
        if line.startswith("## "):
            # Check if this is our target section
            section_title = line[3:].strip()
            # Normalize HTML entities for matching
            normalized = section_title.replace("&amp;", "&")
            if any(name == section_title or name == normalized for name in section_names):
                in_section = True
                continue
            elif in_section:
                # Hit next section — stop
                break
        elif in_section:
            content.append(line)

    return "\n".join(content).strip()


def extract_first_paragraph(text: str) -> str:
    """Extract first non-empty paragraph from text."""
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("-"):
            # Remove markdown formatting for plain text summary
            clean = re.sub(r"\*\*([^*]+)\*\*", r"\1", stripped)
            clean = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", clean)
            clean = re.sub(r"`([^`]+)`", r"\1", clean)
            if len(clean) > 30:
                return clean[:300]
    return text[:300]


def main():
    if not TRACKING_FILE.exists():
        print("[deep_analysis] trend_terms.json not found")
        return

    trends = json.loads(TRACKING_FILE.read_text(encoding="utf-8"))
    high_score_terms = [
        t for t in trends["terms"]
        if t.get("score", 0) >= MIN_SCORE
    ]
    high_score_terms.sort(key=lambda t: t.get("score", 0), reverse=True)
    high_score_terms = high_score_terms[:MAX_TERMS]

    deep_items = []

    for term in high_score_terms:
        slug = term["id"].replace("trend-", "")
        zh_path = TRENDS_DIR / f"{slug}.md"
        en_path = TRENDS_DIR / f"{slug}-en.md"

        zh_body = zh_path.read_text(encoding="utf-8") if zh_path.exists() else ""
        en_body = en_path.read_text(encoding="utf-8") if en_path.exists() else ""

        # Extract sections from EN report for Dashboard display
        extracted = {}
        for key, names in SECTION_KEYS.items():
            text = extract_section(en_body, names)
            if not text:
                text = extract_section(zh_body, names)
            extracted[key] = text

        # Build a one-line "why this matters" from the Why Now section
        why_now = extracted.get("why_now", "")
        why_summary = extract_first_paragraph(why_now)

        item = {
            "id": term["id"],
            "slug": slug,
            "canonical": term["canonical"],
            "category": term.get("category", ""),
            "stage": term.get("stage", "nascent"),
            "score": term.get("score", 0),
            "opportunity_score": term.get("opportunity_score", 0),
            "market_score": term.get("market_score", 0),
            "competition_score": term.get("competition_score", 0),
            "demand_score": term.get("demand_score", 0),
            "source_count": term.get("source_count", 0),
            "total_mentions": term.get("total_mentions", 0),
            "growth_pct": term.get("growth_pct", 0),
            "summary_zh": term.get("summary_zh", ""),
            "summary_en": term.get("summary_en", ""),
            "why_summary": why_summary,
            "tam": extracted.get("tam", ""),
            "mvp_blueprint": extracted.get("mvp", ""),
            "business_model": extracted.get("business_model", ""),
            "risk_assessment": extracted.get("risk", ""),
            "action_plan": extracted.get("action", ""),
            "suggested_products": term.get("suggested_products", []),
            "tags": term.get("tags", []),
            "generated_at": datetime.now(TZ_SHANGHAI).isoformat(),
        }
        deep_items.append(item)

    output = {
        "updated_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "total": len(deep_items),
        "items": deep_items,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[deep_analysis] Generated {len(deep_items)} deep analysis cards -> {OUTPUT_FILE}")
    for item in deep_items:
        has_tam = "Y" if item["tam"] else "N"
        has_mvp = "Y" if item["mvp_blueprint"] else "N"
        print(f"  [{item['score']}] {item['canonical']:<40} TAM:{has_tam} MVP:{has_mvp}")


if __name__ == "__main__":
    main()
