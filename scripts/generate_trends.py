"""
Trend Discovery Pipeline
Reads daily signals, extracts emerging terms via LLM, maintains trend_terms.json,
and generates research reports for high-scoring terms.

Usage: python scripts/generate_trends.py [--dry-run] [--max-terms 30]
"""
import json
import sys
import os
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

TZ_SHANGHAI = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parent.parent
TRACKING_FILE = ROOT / "tracking" / "trend_terms.json"
CONTENT_DIR = ROOT / "content" / "trends"
TEMPLATES_DIR = ROOT / "templates"

# Stage thresholds (days since first_seen)
STAGE_THRESHOLDS = [
    (7, "nascent"),
    (30, "emergent"),
    (90, "validating"),
    (float("inf"), "rising"),
]


def load_json(path: Path) -> dict | list:
    if not path.exists():
        return {} if path.suffix == ".json" else []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_trend_terms() -> dict:
    """Load existing trend terms tracking file."""
    default = {"updated_at": "", "terms": []}
    data = load_json(TRACKING_FILE)
    if isinstance(data, list):
        return default
    return {**default, **data}


def save_trend_terms(data: dict):
    data["updated_at"] = datetime.now(TZ_SHANGHAI).isoformat()
    save_json(TRACKING_FILE, data)


def compute_stage(first_seen_str: str, today: datetime) -> str:
    """Determine stage based on age in days."""
    try:
        first_seen = datetime.strptime(first_seen_str, "%Y-%m-%d").replace(tzinfo=TZ_SHANGHAI)
        age_days = (today - first_seen).days
        for threshold, stage in STAGE_THRESHOLDS:
            if age_days <= threshold:
                return stage
        return "rising"
    except (ValueError, TypeError):
        return "nascent"


def compute_score_from_signals(matching_signals: list[dict]) -> int:
    """Score a term based on its matching signals (reuses existing signal scoring)."""
    if not matching_signals:
        return 0
    avg_score = sum(s.get("score", 0) for s in matching_signals) / len(matching_signals)
    source_count = len(set(s.get("source_key", "") for s in matching_signals))
    total_engagement = sum(s.get("engagement", {}).get("total", 0) for s in matching_signals)
    cross_platform = sum(1 for s in matching_signals if s.get("cross_platform_count", 0) > 0)

    score = (
        avg_score * 0.3
        + min(source_count * 8, 30)
        + min(total_engagement * 0.5, 20)
        + min(cross_platform * 10, 20)
    )
    return min(round(score), 100)


def extract_terms_from_signals(signals: list[dict]) -> list[dict]:
    """
    Extract emerging tech terms from today's signals using LLM.
    Falls back to keyword-based extraction if LLM is unavailable.
    """
    # Build a compact signal summary for the LLM prompt
    signal_summaries = []
    for s in signals[:100]:  # Top 100 by score
        signal_summaries.append({
            "title": s.get("title", ""),
            "summary": s.get("summary", ""),
            "source": s.get("source", ""),
            "tags": s.get("tags", []),
            "score": s.get("score", 0),
        })

    user_prompt = f"""从以下今日采集的技术社区 signals 中，提取新出现的技术术语、产品名、或概念。

规则：
1. 只提取近 30 天内首次在技术社区出现的词
2. 忽略已知通用词汇（如 "AI", "React", "Python", "API", "OpenAI" 等）
3. 每个词返回 JSON 格式：canonical（规范化名称）、category（分类）、summary_zh（一句话中文摘要）、summary_en（一句话英文摘要）
4. 最多提取 20 个词，按重要性排序
5. 只返回 JSON array，不要其他文字

Signals:
{json.dumps(signal_summaries, ensure_ascii=False, indent=2)}"""

    system_prompt = "You extract emerging tech terms from community signals. Return only valid JSON array."

    # Try LLM extraction
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from llm_client import chat

        response = chat(system_prompt, user_prompt)
        # Extract JSON from response (handle markdown code blocks)
        response = response.strip()
        if response.startswith("```"):
            response = response.split("\n", 1)[1]
            if response.endswith("```"):
                response = response[:-3]
        terms = json.loads(response)
        if isinstance(terms, list) and len(terms) > 0 and isinstance(terms[0], dict):
            return terms
    except Exception as e:
        print(f"  [trends] LLM extraction failed: {e}, falling back to keyword method")

    # Fallback: tag-based extraction
    return _extract_terms_keyword_fallback(signals)


def _extract_terms_keyword_fallback(signals: list[dict]) -> list[dict]:
    """Keyword-based fallback when LLM is unavailable. Limited but functional."""
    # Collect all tags from high-scoring signals
    tag_counts: dict[str, int] = {}
    for s in signals:
        if s.get("score", 0) < 40:
            continue
        for tag in s.get("tags", []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    # Take top tags that appear multiple times and look like product/tech names
    terms = []
    seen = set()
    for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1]):
        if count < 3 or tag in seen:
            continue
        seen.add(tag)
        # Filter out generic tags
        generic = {"ai", "api", "react", "python", "javascript", "typescript",
                    "web", "mobile", "frontend", "backend", "devops", "cloud",
                    "open-source", "indie-dev", "product-launch", "show-hn",
                    "article", "news", "tutorial", "startup", "saas"}
        if tag.lower() in generic:
            continue

        terms.append({
            "canonical": tag.replace("-", " ").title(),
            "category": "DevTools",
            "summary_zh": f"与 {tag} 相关的新兴趋势，今日出现在多个技术社区信源中。",
            "summary_en": f"An emerging trend related to {tag}, appearing across multiple tech community sources today.",
        })

    return terms[:20]


def merge_terms(existing: list[dict], extracted: list[dict], signals: list[dict], today: datetime) -> list[dict]:
    """Merge extracted terms into existing, updating existing terms and adding new ones."""
    today_str = today.strftime("%Y-%m-%d")
    term_index: dict[str, int] = {}
    for i, t in enumerate(existing):
        term_index[t["id"]] = i
        # Normalize key for matching
        canonical_lower = t["canonical"].lower()
        term_index[canonical_lower] = i
        for alias in t.get("aliases", []):
            term_index[alias.lower()] = i

    for extracted_term in extracted:
        canonical = extracted_term.get("canonical", "").strip()
        if not canonical:
            continue

        # Try to match with existing term
        key = canonical.lower()
        if key in term_index:
            # Update existing term
            idx = term_index[key]
            t = existing[idx]
            t["last_seen"] = today_str
            t["total_mentions"] += 1

            # Update sources
            signal_sources = list(set(s.get("source_key", "") for s in signals if s.get("score", 0) > 0))
            for src in signal_sources:
                if src not in t["sources"]:
                    t["sources"].append(src)

            t["source_count"] = len(t["sources"])

            # Recalculate growth (simple: mentions this week vs total)
            age_days = (today - datetime.strptime(t["first_seen"], "%Y-%m-%d").replace(tzinfo=TZ_SHANGHAI)).days
            if age_days > 0:
                t["growth_pct"] = round((t["total_mentions"] / max(age_days, 1)) * 100)

            t["stage"] = compute_stage(t["first_seen"], today)
            t["score"] = max(t["score"], compute_score_from_signals(
                [s for s in signals if canonical.lower() in s.get("summary", "").lower()]
            ))
        else:
            # New term
            new_id = f"trend-{canonical.lower().replace(' ', '-')[:40]}"
            slug = new_id.replace("trend-", "")

            matching_signals = [
                s for s in signals
                if canonical.lower() in s.get("summary", "").lower()
                or canonical.lower() in s.get("title", "").lower()
            ]

            signal_sources = list(set(s.get("source_key", "") for s in matching_signals))
            score = compute_score_from_signals(matching_signals)

            new_term = {
                "id": new_id,
                "canonical": canonical,
                "aliases": [],
                "first_seen": today_str,
                "last_seen": today_str,
                "stage": "nascent",
                "score": score,
                "source_count": len(signal_sources),
                "total_mentions": len(matching_signals),
                "sources": signal_sources,
                "growth_pct": 100,
                "category": extracted_term.get("category", "General"),
                "tags": list(set(tag for s in matching_signals for tag in s.get("tags", [])))[:5],
                "summary_zh": extracted_term.get("summary_zh", ""),
                "summary_en": extracted_term.get("summary_en", ""),
                "research_md_path": f"content/trends/{slug}.md",
            }
            existing.append(new_term)
            term_index[key] = len(existing) - 1

    # Sort by score descending
    existing.sort(key=lambda t: t.get("score", 0), reverse=True)
    return existing


def generate_research_report(term: dict) -> bool:
    """Generate a research report for a term via LLM. Returns True if successful."""
    slug = term["id"].replace("trend-", "")
    output_path = CONTENT_DIR / f"{slug}.md"

    # Skip if already generated and term hasn't changed stage
    if output_path.exists():
        return False

    # Load prompt template
    template_path = TEMPLATES_DIR / "trend_research_prompt.md"
    if template_path.exists():
        template = template_path.read_text(encoding="utf-8")
    else:
        template = _default_research_prompt()

    user_prompt = template.replace("{canonical}", term["canonical"])
    user_prompt = user_prompt.replace("{category}", term.get("category", "General"))
    user_prompt = user_prompt.replace("{summary_zh}", term.get("summary_zh", ""))
    user_prompt = user_prompt.replace("{summary_en}", term.get("summary_en", ""))
    user_prompt = user_prompt.replace("{sources}", ", ".join(term.get("sources", [])))
    user_prompt = user_prompt.replace("{first_seen}", term.get("first_seen", ""))
    user_prompt = user_prompt.replace("{stage}", term.get("stage", "nascent"))
    user_prompt = user_prompt.replace("{score}", str(term.get("score", 0)))
    user_prompt = user_prompt.replace("{source_count}", str(term.get("source_count", 0)))
    user_prompt = user_prompt.replace("{total_mentions}", str(term.get("total_mentions", 0)))

    system_prompt = "You write technical trend research reports for indie developers. Use Chinese (zh-CN)."

    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from llm_client import chat

        report = chat(system_prompt, user_prompt)
        CONTENT_DIR.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        return True
    except Exception as e:
        print(f"  [trends] Failed to generate report for {term['canonical']}: {e}")
        return False


def _default_research_prompt() -> str:
    return """Write a comprehensive trend research report for the term "{canonical}" in category {category}.

Structure the report with these 8 sections (use ## for section headers):

## What is it
Explain what {canonical} is in simple terms. Define the concept clearly.

## Why now
Why is this term emerging now? What changed in the market or technology landscape?

## Who's behind it
Key companies, people, or organizations driving this trend.

## Market signals
Cross-platform evidence: {sources}. First seen {first_seen}. Current stage: {stage}. Score: {score}/100.

## Commercial opportunities
How could indie developers or small teams build products around this trend?

## Related terms
Connect to adjacent trends and concepts.

## SEO opportunity
Search volume estimates, key long-tail keywords, competition level.

## Product ideas
2-3 specific product ideas indie developers could build to capitalize on this trend.

Write in Chinese (zh-CN). Be specific and actionable. Avoid generic advice."""


def main():
    parser = argparse.ArgumentParser(description="Generate trend terms from daily signals")
    parser.add_argument("--dry-run", action="store_true", help="Don't write files")
    parser.add_argument("--max-terms", type=int, default=30, help="Max terms to extract")
    parser.add_argument("--date", type=str, help="Date to process (default: today)")
    args = parser.parse_args()

    today = datetime.now(TZ_SHANGHAI)
    if args.date:
        today = datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=TZ_SHANGHAI)

    date_str = today.strftime("%Y-%m-%d")
    signals_path = ROOT / "daily" / date_str / "signals.json"

    if not signals_path.exists():
        print(f"[trends] No signals found for {date_str}, skipping")
        return

    # Load data
    signals_raw = load_json(signals_path)
    if isinstance(signals_raw, dict):
        signals = signals_raw.get("signals", [])
    elif isinstance(signals_raw, list):
        signals = signals_raw
    else:
        signals = []
    print(f"[trends] Loaded {len(signals)} signals for {date_str}")

    trend_data = load_trend_terms()
    existing_terms = trend_data.get("terms", [])
    print(f"[trends] Loaded {len(existing_terms)} existing trend terms")

    # Extract new terms
    print("[trends] Extracting new terms from signals...")
    extracted = extract_terms_from_signals(signals)
    print(f"[trends] Extracted {len(extracted)} candidate terms")

    # Merge
    updated_terms = merge_terms(existing_terms, extracted, signals, today)
    new_count = len(updated_terms) - len(existing_terms)
    print(f"[trends] Merged: {len(updated_terms)} total ({new_count} new)")

    # Generate research reports for high-score terms without reports
    reports_generated = 0
    for term in updated_terms:
        if term.get("score", 0) >= 60:
            slug = term["id"].replace("trend-", "")
            report_path = CONTENT_DIR / f"{slug}.md"
            if not report_path.exists():
                print(f"[trends] Generating research report for {term['canonical']} (score={term['score']})...")
                if not args.dry_run:
                    if generate_research_report(term):
                        reports_generated += 1

    print(f"[trends] Generated {reports_generated} new research reports")

    # Save
    trend_data["terms"] = updated_terms
    if not args.dry_run:
        save_trend_terms(trend_data)
        print(f"[trends] Saved {len(updated_terms)} terms to {TRACKING_FILE}")
    else:
        print("[trends] DRY RUN — no files written")

    # Summary
    stages = {"nascent": 0, "emergent": 0, "validating": 0, "rising": 0}
    for t in updated_terms:
        stages[t.get("stage", "nascent")] = stages.get(t.get("stage", "nascent"), 0) + 1
    print(f"[trends] Stage breakdown: {stages}")
    print("[trends] Done")


if __name__ == "__main__":
    main()
