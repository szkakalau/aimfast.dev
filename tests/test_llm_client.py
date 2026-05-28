"""
Tests for LLM client fallback behavior.
Run: python -m pytest tests/test_llm_client.py -v
"""
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.llm_client import chat


class TestLLMFallback:
    def test_dry_run_returns_template(self):
        """When dry_run=True, the fallback template is returned."""
        result = chat(
            system_prompt="You are a helpful assistant.",
            user_prompt="Tell me about AI.",
            dry_run=True,
        )
        assert len(result) > 0, "Expected non-empty fallback output"
        assert "KAKAOPC" in result, "Fallback should mention KAKAOPC"
        assert "LLM" in result, "Fallback should mention LLM unavailability"

    def test_fallback_is_valid_markdown(self):
        """The fallback output should be valid Markdown."""
        result = chat(
            system_prompt="system",
            user_prompt="user",
            dry_run=True,
        )
        # Should contain markdown elements
        assert result.startswith(">"), "Fallback should start with blockquote"
        assert "---" in result, "Fallback should contain horizontal rule"

    def test_dry_run_does_not_call_api(self):
        """Dry run should return instantly without API key."""
        import time
        start = time.time()
        chat(
            system_prompt="test",
            user_prompt="test",
            dry_run=True,
        )
        elapsed = time.time() - start
        assert elapsed < 1.0, f"Dry run should complete in <1s, took {elapsed:.1f}s"
