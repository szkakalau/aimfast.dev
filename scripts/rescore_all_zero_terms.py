"""Standalone rescore: fix zero-score terms using merged multi-day signals.
Only runs the rescore pass — does NOT extract new terms or modify existing scores.

Usage: python scripts/rescore_all_zero_terms.py
"""
import json, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

TZ = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parent.parent

# Import pipeline helpers
sys.path.insert(0, str(ROOT / "scripts"))
from generate_trends import (
    compute_score_from_signals,
    load_json,
    save_json,
    load_trend_terms,
    save_trend_terms,
)

sys.path.insert(0, str(ROOT / "scripts"))
from llm_client import chat

BATCH_SIZE = 25
SIGNAL_TOP_N = 200  # Top N signals by score from merged days
SIGNAL_DAYS = 7     # How many days of historical signals to merge


def main():
    # ── Load trend terms ──
    trend_data = load_trend_terms()
    terms = trend_data.get("terms", [])
    zero_terms = [t for t in terms if t.get("score", 0) == 0]
    if not zero_terms:
        print("No zero-score terms found!")
        return
    print(f"Zero-score terms: {len(zero_terms)}/{len(terms)}")

    # ── Merge signals from recent days ──
    today = datetime.now(TZ).date()
    all_signals = []
    for d in range(SIGNAL_DAYS):
        date_str = (today - timedelta(days=d)).strftime("%Y-%m-%d")
        sp = ROOT / "daily" / date_str / "signals.json"
        if not sp.exists():
            continue
        data = load_json(sp)
        signals = data.get("signals", []) if isinstance(data, dict) else data
        all_signals.extend(signals)

    # Deduplicate + keep top N by score
    seen = set()
    deduped = []
    for s in all_signals:
        sid = s.get("id", "")
        if sid and sid not in seen:
            seen.add(sid)
            deduped.append(s)
    deduped.sort(key=lambda s: s.get("score", 0), reverse=True)
    signals = deduped[:SIGNAL_TOP_N]
    print(f"Merged signals: {len(deduped)} unique from {SIGNAL_DAYS} days → top {len(signals)}")

    # ── Build signal summaries + lookups ──
    signal_summaries = []
    for s in signals:
        signal_summaries.append({
            "id": s.get("id", ""),
            "title": s.get("title", "")[:150],
            "summary": s.get("summary", "")[:200],
            "source": s.get("source", ""),
            "tags": s.get("tags", [])[:5],
        })
    signals_by_id = {s["id"]: s for s in signals if s.get("id")}

    # ── Batch rescore ──
    total_batches = (len(zero_terms) + BATCH_SIZE - 1) // BATCH_SIZE
    total_updated = 0

    for i in range(0, len(zero_terms), BATCH_SIZE):
        batch = zero_terms[i:i + BATCH_SIZE]
        batch_idx = i // BATCH_SIZE + 1
        print(f"\nBatch {batch_idx}/{total_batches} ({len(batch)} terms)...", end=" ", flush=True)

        batch_summaries = []
        for t in batch:
            batch_summaries.append({
                "term_id": t["id"],
                "canonical": t["canonical"],
                "summary_en": t.get("summary_en", "")[:200],
                "summary_zh": t.get("summary_zh", "")[:200],
                "category": t.get("category", "General"),
            })

        system_prompt = (
            "You are a semantic matching engine. Given a list of trend terms and a list of signals, "
            "identify which signals are related to each term. A signal is related if it discusses "
            "the same concept, technology, product, or theme — even if the term name does not appear "
            "literally in the signal text. Return only valid JSON."
        )

        user_prompt = f"""For each trend term below, identify which signals (by their "id") are related to it.

A signal is related if it discusses the same concept, technology, product, or theme as the term
— even if the word does not appear verbatim. Use semantic understanding.

Return a JSON array where each element has:
- "term_id": the term ID from the list
- "signal_ids": array of signal IDs that are related (empty array [] if none match)

Only include terms that have at least one matching signal — skip terms with zero matches entirely.

Trend Terms:
{json.dumps(batch_summaries, ensure_ascii=False, indent=2)}

Signals:
{json.dumps(signal_summaries, ensure_ascii=False, indent=2)}

Return ONLY the JSON array, nothing else."""

        try:
            response = chat(system_prompt, user_prompt)
            response = response.strip()
            if response.startswith("```"):
                response = response.split("\n", 1)[1]
                if response.endswith("```"):
                    response = response[:-3]
            mappings = json.loads(response)
        except Exception as e:
            print(f"FAIL: {e}")
            continue

        if not isinstance(mappings, list):
            print("SKIP (bad format)")
            continue

        batch_updated = 0
        for mapping in mappings:
            term_id = mapping.get("term_id", "")
            term = next((t for t in terms if t["id"] == term_id), None)
            if not term or term.get("score", 0) != 0:
                continue

            signal_ids = mapping.get("signal_ids", [])
            matching = [signals_by_id[sid] for sid in signal_ids if sid in signals_by_id]
            if not matching:
                continue

            score = compute_score_from_signals(matching)
            sources = list(set(s.get("source_key", "") for s in matching))
            tags = list(set(tag for s in matching for tag in s.get("tags", [])))[:5]

            term["score"] = score
            term["source_count"] = len(sources)
            term["total_mentions"] = len(matching)
            term["sources"] = sources
            term["tags"] = tags
            batch_updated += 1
            print(f"\n  {term['canonical']} → score={score}, sources={len(sources)}")

        total_updated += batch_updated
        print(f"  → {batch_updated} updated" if batch_updated else "  0 matches")

    # ── Save ──
    if total_updated > 0:
        terms.sort(key=lambda t: t.get("score", 0), reverse=True)
        trend_data["terms"] = terms
        save_trend_terms(trend_data)
        remaining = sum(1 for t in terms if t.get("score", 0) == 0)
        print(f"\nDone: {total_updated} updated, {remaining} still at zero")
    else:
        print("\nNo terms were updated.")


if __name__ == "__main__":
    main()
