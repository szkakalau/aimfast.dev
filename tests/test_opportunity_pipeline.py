"""Unit tests for generate_opportunity.py and generate_trends.py helpers."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from generate_trends import _normalize_category
from generate_opportunity import should_analyze, load_research_content


# ── _normalize_category (generate_trends.py) ──

def test_normalize_category_known_lowercase():
    assert _normalize_category("product") == "Productivity"
    assert _normalize_category("project") == "OpenSource"
    assert _normalize_category("infrastructure") == "Infra"
    assert _normalize_category("opensource") == "OpenSource"
    assert _normalize_category("aimodel") == "AIModel"
    assert _normalize_category("aiagent") == "AIAgent"
    assert _normalize_category("aiapp") == "AIApp"
    assert _normalize_category("dx") == "DX"
    assert _normalize_category("consumer") == "Consumer"
    assert _normalize_category("industry") == "Industry"
    assert _normalize_category("design") == "Design"


def test_normalize_category_known_titlecase():
    assert _normalize_category("Productivity") == "Productivity"
    assert _normalize_category("OpenSource") == "OpenSource"
    assert _normalize_category("AIModel") == "AIModel"
    assert _normalize_category("AIAgent") == "AIAgent"
    assert _normalize_category("AIApp") == "AIApp"
    assert _normalize_category("DX") == "DX"
    assert _normalize_category("Consumer") == "Consumer"
    assert _normalize_category("Industry") == "Industry"
    assert _normalize_category("Design") == "Design"
    # legacy mappings
    assert _normalize_category("AI/LLM") == "AIModel"
    assert _normalize_category("HotTopic") == "Industry"
    assert _normalize_category("DevTools") == "DevTools"
    assert _normalize_category("TechConcept") == "TechConcept"
    assert _normalize_category("Infra") == "Infra"


def test_normalize_category_unknown():
    assert _normalize_category("Blockchain") == "Blockchain"
    assert _normalize_category("lowercaseunknown") == "Lowercaseunknown"


def test_normalize_category_empty():
    assert _normalize_category("") == "General"
    assert _normalize_category(None) == "General"


def test_normalize_category_whitespace():
    assert _normalize_category("  product  ") == "Productivity"
    assert _normalize_category("  aiagent  ") == "AIAgent"


def test_normalize_category_llm_variants():
    """LLM may return categories with spaces or mixed case."""
    assert _normalize_category("ai model") == "AIModel"
    assert _normalize_category("AI Model") == "AIModel"
    assert _normalize_category("ai agent") == "AIAgent"
    assert _normalize_category("open source") == "OpenSource"
    assert _normalize_category("Open Source") == "OpenSource"
    assert _normalize_category("dev tools") == "DevTools"
    assert _normalize_category("hot topic") == "Industry"
    assert _normalize_category("tech concept") == "TechConcept"


def test_normalize_category_legacy_aliases():
    """Legacy LLM output patterns map correctly to new categories."""
    assert _normalize_category("LLM") == "AIModel"
    assert _normalize_category("Agent") == "AIAgent"
    assert _normalize_category("OSS") == "OpenSource"


# ── should_analyze (generate_opportunity.py) ──

def test_should_analyze_below_min_score():
    term = {"score": 30}
    assert should_analyze(term, force=False, min_score=60) is False
    assert should_analyze(term, force=False, min_score=30) is True
    assert should_analyze(term, force=False, min_score=0) is True


def test_should_analyze_already_has_opportunity():
    term = {"score": 80, "opportunity_score": 75}
    assert should_analyze(term, force=False, min_score=0) is False


def test_should_analyze_force_re_analyze():
    term = {"score": 80, "opportunity_score": 75}
    assert should_analyze(term, force=True, min_score=0) is True


def test_should_analyze_new_term():
    term = {"score": 50}
    assert should_analyze(term, force=False, min_score=0) is True


def test_should_analyze_zero_score_term():
    term = {"score": 0}
    assert should_analyze(term, force=False, min_score=0) is True


# ── load_research_content (generate_opportunity.py) ──

def test_load_research_content_fallback_summary():
    term = {
        "summary_en": "An emerging trend in AI tooling.",
        "summary_zh": "AI 工具领域的新兴趋势。",
        "sources": ["GitHub", "Reddit"],
        "tags": ["ai", "tools"],
    }
    content = load_research_content(term)
    assert "Summary (EN):" in content
    assert "An emerging trend" in content
    assert "Summary (ZH):" in content
    assert "GitHub, Reddit" in content
    assert "Tags: ai, tools" in content


def test_load_research_content_no_data():
    term = {}
    assert load_research_content(term) == ""


def test_load_research_content_summary_only_en():
    term = {
        "summary_en": "A test trend.",
        "summary_zh": "",
        "sources": [],
        "tags": [],
    }
    content = load_research_content(term)
    assert "Summary (EN): A test trend." in content
    assert "Summary (ZH)" not in content
    assert "Sources:" not in content
    assert "Tags:" not in content
