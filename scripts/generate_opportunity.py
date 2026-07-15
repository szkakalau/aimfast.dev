"""
Opportunity Analysis Pipeline (Step 3.6)
Reads trend terms with research reports, runs LLM opportunity analysis,
and updates trend_terms.json with market/competition/demand scores.

Usage: python scripts/generate_opportunity.py [--dry-run] [--force]
"""
import json
import sys
import os
import argparse
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

TZ_SHANGHAI = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parent.parent
TRACKING_FILE = ROOT / "tracking" / "trend_terms.json"
CONTENT_DIR = ROOT / "content" / "trends"
TEMPLATE_FILE = ROOT / "templates" / "opportunity_analysis_prompt.md"

# Default minimum score for analysis (CLI --min-score overrides).
# Set to 0 so ALL terms get opportunity data — low-scored terms
# can still be perfect solo-dev opportunities (blue ocean + fast MVP).
MIN_SCORE_FOR_ANALYSIS = 0


def load_json(path: Path) -> dict | list:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_trend_terms() -> dict:
    data = load_json(TRACKING_FILE)
    if isinstance(data, list):
        return {"updated_at": "", "terms": []}
    return data


def save_trend_terms(data: dict):
    data["updated_at"] = datetime.now(TZ_SHANGHAI).isoformat()
    save_json(TRACKING_FILE, data)


def load_template() -> str:
    """Load the opportunity analysis prompt template."""
    if TEMPLATE_FILE.exists():
        return TEMPLATE_FILE.read_text(encoding="utf-8")
    print(f"[opportunity] Template not found: {TEMPLATE_FILE}")
    return ""


def load_research_content(term: dict) -> str:
    """Load research markdown content for a term, with fallback to summary fields."""
    research_md_path = term.get("research_md_path", "")
    full_path = ROOT / research_md_path if research_md_path else None

    if full_path and full_path.exists():
        content = full_path.read_text(encoding="utf-8")
        content = re.sub(r'^---[\s\S]*?---\n*', '', content).strip()
        if len(content) > 3000:
            content = content[:3000] + "\n\n... (truncated)"
        return content

    # Fallback: build context from summaries + sources when no research report exists
    parts = []
    summary_en = term.get("summary_en", "").strip()
    summary_zh = term.get("summary_zh", "").strip()
    if summary_en:
        parts.append(f"Summary (EN): {summary_en}")
    if summary_zh:
        parts.append(f"Summary (ZH): {summary_zh}")
    sources = term.get("sources", [])
    if sources:
        parts.append(f"Sources: {', '.join(sources[:8])}")
    tags = term.get("tags", [])
    if tags:
        parts.append(f"Tags: {', '.join(tags[:10])}")

    if not parts:
        return ""

    return "(No deep research report yet — evaluate based on summaries below)\n\n" + "\n".join(parts)


def build_prompt(term: dict, research_content: str) -> str:
    """Build the LLM prompt from template and term data."""
    template = load_template()
    if not template:
        return ""

    replacements = {
        "{canonical}": term.get("canonical", ""),
        "{category}": term.get("category", "General"),
        "{research_content}": research_content or "(No research report yet)",
        "{sources}": ", ".join(term.get("sources", [])),
        "{stage}": term.get("stage", "nascent"),
        "{score}": str(term.get("score", 0)),
        "{source_count}": str(term.get("source_count", 0)),
        "{total_mentions}": str(term.get("total_mentions", 0)),
        "{growth_pct}": str(term.get("growth_pct", 0)),
    }

    for key, value in replacements.items():
        template = template.replace(key, value)

    return template


def analyze_opportunity(term: dict, research_content: str) -> dict | None:
    """Run LLM opportunity analysis for a single term. Returns parsed result or None."""
    user_prompt = build_prompt(term, research_content)
    if not user_prompt:
        return None

    system_prompt = (
        "You are an opportunity analyst for indie developers. "
        "You evaluate tech trends and output structured JSON with market scores, "
        "competition analysis, demand assessment, and product suggestions. "
        "Return ONLY valid JSON. No markdown, no explanation outside the JSON."
    )

    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from llm_client import chat

        response = chat(system_prompt, user_prompt, temperature=0.7, max_tokens=2048)

        # Extract JSON from response — handle possible markdown wrapping
        response = response.strip()
        # Remove markdown code fences if present
        if response.startswith("```"):
            lines = response.split("\n")
            # Remove first line (```json or ```)
            lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response = "\n".join(lines)

        result = json.loads(response)

        # Validate required fields
        required = ["opportunity_score", "market_score", "competition_score",
                     "demand_score", "seo_difficulty"]
        for field in required:
            if field not in result:
                print(f"  [opportunity] Missing field '{field}' in LLM response")
                return None

        # Clamp scores to 0-100
        for field in required + ["revenue_potential"]:
            if field in result and isinstance(result[field], (int, float)):
                if field == "revenue_potential":
                    result[field] = max(1, min(5, int(result[field])))
                else:
                    result[field] = max(0, min(100, int(result[field])))

        return result

    except json.JSONDecodeError as e:
        print(f"  [opportunity] Failed to parse LLM JSON: {e}")
        print(f"  [opportunity] Raw response (first 200 chars): {response[:200]}")
        return None
    except Exception as e:
        print(f"  [opportunity] LLM call failed: {e}")
        return None


def apply_opportunity_to_term(term: dict, analysis: dict):
    """Apply opportunity analysis results to a term dict (mutates in place)."""
    field_mapping = {
        "opportunity_score": "opportunity_score",
        "market_score": "market_score",
        "competition_score": "competition_score",
        "demand_score": "demand_score",
        "seo_difficulty": "seo_difficulty",
        "suggested_products": "suggested_products",
        "estimated_dev_days": "estimated_dev_days",
        "revenue_potential": "revenue_potential",
        "risk_factors_en": "risk_factors_en",
        "risk_factors_zh": "risk_factors_zh",
        "opportunity_summary_en": "opportunity_summary_en",
        "opportunity_summary_zh": "opportunity_summary_zh",
    }

    for src_key, dest_key in field_mapping.items():
        if src_key in analysis:
            term[dest_key] = analysis[src_key]


def should_analyze(term: dict, force: bool, min_score: int = 0) -> bool:
    """Determine if a term needs opportunity analysis."""
    score = term.get("score", 0)
    if score < min_score:
        return False

    # Skip if already analyzed (unless --force)
    if not force and term.get("opportunity_score") is not None:
        return False

    return True


def main():
    parser = argparse.ArgumentParser(description="Generate opportunity analysis for trend terms")
    parser.add_argument("--dry-run", action="store_true", help="Don't write files")
    parser.add_argument("--force", action="store_true", help="Re-analyze even if already scored")
    parser.add_argument("--min-score", type=int, default=MIN_SCORE_FOR_ANALYSIS,
                        help=f"Minimum score to analyze (default: {MIN_SCORE_FOR_ANALYSIS})")
    parser.add_argument("--max-daily", type=int, default=20,
                        help="Max terms to analyze per run (default: 20)")
    args = parser.parse_args()

    trend_data = load_trend_terms()
    terms = trend_data.get("terms", [])
    print(f"[opportunity] Loaded {len(terms)} trend terms")
    print(f"[opportunity] Min score: {args.min_score}, Max daily: {args.max_daily}, Force: {args.force}")

    # Priority order:
    #   1. Terms without opportunity data (never analyzed)
    #   2. Terms first seen recently (past 7 days)
    #   3. Older terms
    # This ensures new terms get analyzed first while backlog fills in gradually.
    today_str = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    cutoff_new = (datetime.now(TZ_SHANGHAI) - timedelta(days=7)).strftime("%Y-%m-%d")

    candidates = [t for t in terms if should_analyze(t, args.force, args.min_score)]

    def _priority(term: dict) -> tuple[int, int]:
        has_opp = 0 if term.get("opportunity_score") is None else 1
        is_new = 0 if term.get("first_seen", "") >= cutoff_new else 1
        return (has_opp, is_new)

    candidates.sort(key=_priority)
    candidates = candidates[:args.max_daily]

    if not candidates:
        print("[opportunity] No terms to analyze (all up to date or below threshold)")
        return

    print(f"[opportunity] {len(candidates)} terms queued for analysis "
          f"(of {len([t for t in terms if should_analyze(t, args.force, args.min_score)])} total candidates)")

    analyzed = 0
    skipped = 0
    failed = 0

    for term in candidates:
        canonical = term.get("canonical", "unknown")

        print(f"[opportunity] Analyzing: {canonical} (score={term.get('score', 0)})")

        research_content = load_research_content(term)
        if not research_content:
            print(f"  [opportunity] No content available (no summary nor research report), skipping")
            skipped += 1
            continue

        analysis = analyze_opportunity(term, research_content)

        if analysis:
            print(f"  [opportunity] → opportunity_score={analysis.get('opportunity_score')}, "
                  f"market={analysis.get('market_score')}, "
                  f"competition={analysis.get('competition_score')}, "
                  f"demand={analysis.get('demand_score')}, "
                  f"seo={analysis.get('seo_difficulty')}, "
                  f"revenue={analysis.get('revenue_potential')}★")

            if not args.dry_run:
                apply_opportunity_to_term(term, analysis)
            analyzed += 1
        else:
            print(f"  [opportunity] Analysis failed for {canonical}")
            failed += 1

    # Save
    trend_data["terms"] = terms
    if not args.dry_run:
        save_trend_terms(trend_data)
        print(f"[opportunity] Saved to {TRACKING_FILE}")
    else:
        print("[opportunity] DRY RUN — no files written")

    print(f"[opportunity] Done: {analyzed} analyzed, {skipped} skipped, {failed} failed")


if __name__ == "__main__":
    main()
