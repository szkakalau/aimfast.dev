"""
Migrate existing trend terms from 7-category to 12-category system.

Old → New mapping:
  AI/LLM     → AIModel | AIAgent | AIApp
  Product    → Productivity | Consumer | AIApp | DevTools
  HotTopic   → DX | Industry | Design | Consumer | Infra
  Project    → OpenSource
  DevTools   → DevTools (unchanged)
  Infra      → Infra (unchanged)
  TechConcept → TechConcept (unchanged)

Usage: python scripts/migrate_categories.py [--dry-run]
"""

import json
import re
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta
from defaults import atomic_write_json

TZ_SHANGHAI = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parent.parent

FILES = [
    ROOT / "public" / "trends.json",
    ROOT / "tracking" / "trend_terms.json",
]


def classify_term(canonical: str, summary_en: str, old_cat: str) -> str:
    """Map a term to the new 12-category system using keyword heuristics."""
    text = f"{canonical} {summary_en}".lower()

    # ── Specific overrides for edge cases ──
    overrides = {
        "ai agent self-edit traceability": "AIAgent",
        "ai agent hallucination and traceability": "AIAgent",
        "instantvideos.org": "AIApp",
        "homegames": "Consumer",
        "l9gpu": "Infra",
        "ai agent play and exploration": "DX",
        "ai agent productivity burnout": "Industry",
        "local-first file sharing": "TechConcept",
    }
    key = canonical.lower().strip()
    if key in overrides:
        return overrides[key]

    # ── AI/LLM → split into AIModel / AIAgent / AIApp ──
    if old_cat == "AI/LLM":
        # Model names, releases, inference, compression, routing
        if any(kw in text for kw in [
            "gpt-", "grok", "leanstral", "bonsai", "model release", "model training",
            "llm api", "unmetered", "on-device", "inference", "low-bit compression",
            "deterministic routing", "sampling for llm", "code generation quality",
            "large model", "benchmark", "rl-trained",
        ]):
            return "AIModel"
        # Agent, SDK, protocol, MCP, control plane
        if any(kw in text for kw in [
            "agent sdk", "mcp ", "protocol", "livekit", "control plane",
            "agent security", "agent tutorial", "agent runtime", "agent bug",
            "agent framework", "agent tool",
        ]):
            return "AIAgent"
        # AI-powered applications
        if any(kw in text for kw in [
            "ai-powered", "ai video", "ai short", "ai procedural",
            "ai-assisted", "ai tutor", "ocr correction", "speechanalyzer",
            "world model", "autonomous driving", "smart home",
            "procedural modeling", "production pipeline",
        ]):
            return "AIApp"
        # AI Gateway — route to AIAgent (it's agent infrastructure)
        if "gateway" in text:
            return "AIAgent"
        return "AIAgent"  # default for AI/LLM terms

    # ── Product → split into Productivity / Consumer / AIApp / DevTools ──
    if old_cat == "Product":
        if any(kw in text for kw in [
            "ai video", "ai-generated", "ai tutor", "ai tattoo", "ai passport",
            "instant video", "ai-powered video", "ai-driven", "browser video editor",
            "agent app builder", "ai agent wait",
        ]):
            return "AIApp"
        if any(kw in text for kw in [
            "reminder", "game boy", "e ink", "home automation", "pet ",
            "taptap", "pulpie",
        ]):
            return "Consumer"
        if any(kw in text for kw in [
            "cli", "sdk", "api", "debug", "l9gpu", "container loading",
            "excel-compatible", "agent runtime",
        ]):
            return "DevTools"
        if any(kw in text for kw in [
            "note", "transfer", "file sharing", "pinyin", "input method",
            "captchainbox", "markwise", "orzma", "sidenote", "rnet",
            "webdrop", "peek-", "sageport", "muse spark",
        ]):
            return "Productivity"
        return "Productivity"  # default for Product

    # ── HotTopic → split into DX / Industry / Design / Consumer / Infra ──
    if old_cat == "HotTopic":
        if any(kw in text for kw in [
            "home automation", "home assistant", "smart home", "zigbee",
            "iot",
        ]):
            return "Consumer"
        if any(kw in text for kw in [
            "kubernetes", "k8s", "leap second", "dns", "network",
        ]):
            return "Infra"
        if any(kw in text for kw in [
            "design", "ux ", "ui ", "accessibility", "a11y", "content flagging",
        ]):
            return "Design"
        if any(kw in text for kw in [
            "coding", "code generation", "code review", "debugging", "vibe coding",
            "no-code", "ai coding tool", "ai coding assistant", "web-to-app",
            "anti-pattern", "ai code", "code quality", "ai-clone",
        ]):
            return "DX"
        if any(kw in text for kw in [
            "alienated", "indie development", "real cost", "open-source",
            "open source", "sustainable funding", "engineer role",
            "hiring signal", "productivity burnout", "one-person business",
            "business template", "ai agent hallucination", "traceability",
            "external brain", "cognitive decline", "over-reliance",
            "ai agent play", "agent exploration", "funding shift",
            "funding model", "sustainable",
        ]):
            return "Industry"
        return "Industry"  # default for HotTopic

    # ── Project → OpenSource ──
    if old_cat == "Project":
        return "OpenSource"

    # ── Unchanged categories ──
    if old_cat in ("DevTools", "Infra", "TechConcept"):
        return old_cat

    # ── Unknown — keep as-is ──
    return old_cat


def main():
    parser = argparse.ArgumentParser(description="Migrate categories from 7 to 12")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, don't write")
    args = parser.parse_args()

    for filepath in FILES:
        if not filepath.exists():
            print(f"[migrate] File not found, skipping: {filepath}")
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        terms = data.get("terms", [])
        changes: list[tuple[str, str, str]] = []
        new_dist: dict[str, int] = {}

        for term in terms:
            old_cat = term.get("category", "Unknown")
            canonical = term.get("canonical", "")
            summary_en = term.get("summary_en", "")
            new_cat = classify_term(canonical, summary_en, old_cat)
            term["category"] = new_cat

            new_dist[new_cat] = new_dist.get(new_cat, 0) + 1
            if old_cat != new_cat:
                changes.append((canonical, old_cat, new_cat))

        print(f"\n{'='*70}")
        print(f"File: {filepath.name}")
        print(f"{'='*70}")
        print(f"Total terms: {len(terms)}")
        print(f"Changed: {len(changes)}")
        print()

        if changes:
            print("Reclassifications:")
            for canonical, old, new in changes:
                print(f"  {canonical:<40s} {old:<12s} → {new}")

        print(f"\nNew distribution ({len(new_dist)} categories):")
        for cat, count in sorted(new_dist.items(), key=lambda x: -x[1]):
            bar = "█" * max(1, count // 2)
            print(f"  {cat:<16s} {count:3d}  {bar}")

        if not args.dry_run:
            data["updated_at"] = datetime.now(TZ_SHANGHAI).isoformat()
            atomic_write_json(filepath, data)
            print(f"\n[migrate] OK Saved to {filepath}")
        else:
            print("\n[migrate] DRY RUN - no file written")

    if not args.dry_run:
        print("\n[migrate] Migration complete. Run tests to verify.")


if __name__ == "__main__":
    main()
