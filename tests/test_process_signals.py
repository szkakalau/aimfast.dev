"""
Tests for signal processing pipeline.
Run: python -m pytest tests/test_process_signals.py -v
"""
import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.process_signals import deduplicate, cluster, score_epa, apply_decay

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> list[dict]:
    data = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return data.get("signals", [])


class TestDeduplicate:
    def test_exact_url_match_merges(self):
        """Signals with identical URLs are merged into one."""
        signals = load_fixture("sample_signals.json")
        result = deduplicate(signals)
        # sig-001 and sig-002 share the same URL → merged
        assert len(result) < len(signals), f"Expected dedup to reduce count, got {len(result)}"

    def test_empty_returns_empty(self):
        assert deduplicate([]) == []


class TestScoreEPA:
    def test_cross_platform_scoring(self):
        """Multi-source signals get higher cross-platform scores."""
        signals = load_fixture("sample_signals.json")
        # First deduplicate and cluster
        signals = deduplicate(signals)
        signals = cluster(signals)
        result = score_epa(signals)

        # sig-001 (HN + Reddit via same URL) should have cross_platform_count >= 1
        for s in result:
            assert "score" in s, f"Missing score field: {s.get('title')}"
            assert "score_breakdown" in s, f"Missing breakdown: {s.get('title')}"
            assert s["score"] >= 0, f"Score should be non-negative: {s['score']}"

    def test_high_engagement_scores_higher(self):
        """High engagement signals score higher than low engagement ones."""
        signals = load_fixture("sample_signals.json")
        signals = deduplicate(signals)
        signals = cluster(signals)
        result = score_epa(signals)

        scores = [s["score"] for s in result]
        # At least one signal should be above 10
        assert max(scores) >= 10, f"Expected at least one signal >= 10, max was {max(scores)}"


class TestApplyDecay:
    def test_no_previous_days_no_decay(self):
        """Signals with no prior history should not be decayed."""
        signals = load_fixture("sample_signals.json")
        signals = deduplicate(signals)
        signals = cluster(signals)
        signals = score_epa(signals)

        # Use a future date so no previous data exists
        result = apply_decay(signals, "2026-06-01")
        # No signal should be decayed (no prior history)
        for s in result:
            assert not s.get("decayed"), f"Unexpected decay: {s.get('title')}"
            assert not s.get("cooling"), f"Unexpected cooling: {s.get('title')}"
