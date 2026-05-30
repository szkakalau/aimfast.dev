"""
Content Translator — Chinese → English
Translates daily report, article, and jike post to English via DeepSeek.
Output: report-en.md, article-en.md, jike-post-en.md in the same daily dir.
"""
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.llm_client import chat

ROOT = Path(__file__).resolve().parent.parent
DAILY_DIR = ROOT / "daily"

TZ_SHANGHAI = timezone(timedelta(hours=8))

# ── Translation system prompt ──
TRANSLATION_SYSTEM = """You are an expert translator specialized in converting Chinese tech/indie-developer content into natural, idiomatic English. Your translations are read by indie hackers, SaaS founders, and software developers worldwide.

## Core Rules

1. **Preserve ALL markdown formatting** — headers (# ## ###), bold (**), italic (*), tables, code blocks, blockquotes (>), lists, horizontal rules (---), links, and inline code (`) must remain exactly as-is. Only translate the text content.

2. **Preserve ALL numbers** — scores, percentages, counts, dates, prices ($, ¥, USD), and statistics must remain unchanged.

3. **Preserve ALL technical terms** — product names, company names, URLs, API names, programming languages, framework names, and platform names (GitHub, Hacker News, Product Hunt, V2EX, etc.) must stay in their original form.

4. **Natural, idiomatic English** — do NOT produce literal/word-for-word translation. Adapt Chinese expressions, idioms, and colloquialisms to their closest natural English equivalents. The output should read as if originally written by a native English-speaking tech analyst.

5. **Keep the same section structure** — do not add, remove, merge, or reorder sections. Each section's heading stays in the same position.

6. **Tone**: professional but conversational, data-driven, direct. Target reading level: tech-industry professional (same as the Chinese original).

7. **Short paragraphs** — match the original's paragraph breaks. If the Chinese uses short punchy sentences, the English should too.

8. **Handling mixed content**: If you encounter English words/phrases already embedded in the Chinese text, keep them and integrate them naturally into the English sentence flow.

9. **Translate everything to English** — the final output should contain ONLY English text (plus preserved formatting, numbers, and technical terms). No Chinese should remain.

## Examples

Chinese: "## 🔥 本周最值得关注的信号"
English: "## 🔥 This Week's Most Notable Signals"

Chinese: "独立开发者正在从 SaaS 转向内容付费"
English: "Indie developers are shifting from SaaS to paid content"

Chinese: "> ⚠️ 该信号已连续出现 5 天，进入冷却期"
English: "> ⚠️ This signal has appeared for 5 consecutive days — entering cooling period"

Chinese: "| 排名 | 信号 | E-P-A 评分 |"
English: "| Rank | Signal | E-P-A Score |"

## Important

Output ONLY the translated markdown. No preamble, no explanation, no "Here's the translation:" — just the clean translated content.

## SEO Translation Rules (Google Indexing)

1. **Title length**: Keep translated title at 50-70 characters. If the Chinese title is too short or too long, adapt it to fit the optimal SEO length while preserving meaning.
2. **Meta description**: The first paragraph after the title should work as a standalone Google search snippet (150-160 characters). If the Chinese first paragraph doesn't translate well, restructure it to be more descriptive while keeping the core message.
3. **Keywords in translation**: Ensure important English keywords (product names, categories, technical terms) appear naturally in the first 200 words. Don't keyword-stuff — just make sure they're present.
4. **Heading hierarchy**: Preserve H1 → H2 → H3 exactly. Never promote or demote a heading level. Each H2 should have at least 150 words of body text in English (same as Chinese).
5. **Link text**: Translate link descriptions to descriptive English anchor text. Never use "click here" — use descriptive phrases like "view the HN discussion (417 comments)".
6. **Featured snippet optimization**: When translating lists, steps, or definitions, structure them clearly (numbered lists, bold terms followed by explanations) so Google can extract them as featured snippets.
7. **Readability**: Use short English paragraphs (max 4 sentences). Break up long Chinese paragraphs into digestible English chunks. Use active voice. Aim for 8th-grade reading level (Hemingway style)."""

# Content-specific temperature settings
TRANSLATION_CONFIG = {
    "report.md": {"temperature": 0.3, "max_tokens": 8192, "label": "Report"},
    "article.md": {"temperature": 0.5, "max_tokens": 8192, "label": "Article"},
    "jike-post.md": {"temperature": 0.5, "max_tokens": 4096, "label": "Jike Post"},
}


def translate_content(content: str, content_type: str) -> str:
    """Translate Chinese markdown content to English."""
    config = TRANSLATION_CONFIG.get(content_type, {"temperature": 0.4, "max_tokens": 8192})

    # Build user prompt with the content
    user_prompt = f"Translate the following Chinese {config['label'].lower()} to natural, idiomatic English. Preserve ALL markdown formatting, numbers, and technical terms exactly.\n\n---\n\n{content}"

    result = chat(
        system_prompt=TRANSLATION_SYSTEM,
        user_prompt=user_prompt,
        temperature=config["temperature"],
        max_tokens=config["max_tokens"],
    )

    return result


def translate_file(input_path: Path, output_path: Path, content_type: str) -> bool:
    """Translate a single file. Returns True on success."""
    if not input_path.exists():
        print(f"  [{content_type}] Source file not found: {input_path}")
        return False

    content = input_path.read_text(encoding="utf-8")
    if not content.strip():
        print(f"  [{content_type}] Source file is empty, skipping")
        return False

    print(f"  [{content_type}] Translating ({len(content):,} chars)...")

    try:
        translated = translate_content(content, content_type)
    except Exception as e:
        print(f"  [{content_type}] LLM call failed: {e}")
        return False

    if not translated or not translated.strip():
        print(f"  [{content_type}] Translation returned empty")
        return False

    # Basic sanity check: translation should not be mostly Chinese
    chinese_chars = sum(1 for c in translated if '一' <= c <= '鿿')
    total_chars = len(translated.replace(' ', '').replace('\n', ''))
    if total_chars > 0 and chinese_chars / max(total_chars, 1) > 0.3:
        print(f"  [{content_type}] WARN: Translation still contains {chinese_chars} Chinese characters ({chinese_chars/max(total_chars,1)*100:.0f}%) -- possible LLM issue")

    output_path.write_text(translated, encoding="utf-8")
    print(f"  [{content_type}] Saved -> {output_path} ({len(translated):,} chars)")

    return True


def run(date_str: str | None = None) -> dict:
    """Translate all daily content to English. Returns summary dict."""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")

    print(f"\n{'='*50}")
    print(f"[Translate] Content translation (zh → en) — {date}")
    print(f"{'='*50}")

    date_dir = DAILY_DIR / date
    if not date_dir.exists():
        print(f"[Translate] No daily dir for {date}, nothing to translate")
        return {"date": date, "results": {}}

    targets = [
        ("report.md", "report-en.md"),
        ("article.md", "article-en.md"),
        ("jike-post.md", "jike-post-en.md"),
    ]

    results = {}
    success_count = 0

    for src_name, dst_name in targets:
        content_type = src_name
        src_path = date_dir / src_name
        dst_path = date_dir / dst_name

        ok = translate_file(src_path, dst_path, content_type)
        results[src_name] = "ok" if ok else "skipped"
        if ok:
            success_count += 1

    print(f"\n[Translate] Done: {success_count}/{len(targets)} files translated")

    return {"date": date, "results": results}


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")

    # Support date argument for manual runs
    date_arg = sys.argv[1] if len(sys.argv) > 1 else today
    result = run(date_arg)

    ok_count = sum(1 for v in result["results"].values() if v == "ok")
    if ok_count == 0:
        print("\n[Translate] WARN: No files were translated -- check if source files exist")
        sys.exit(0)  # Not a fatal error — sources may not exist yet
    else:
        print(f"\n[Translate] OK: {ok_count} English files ready for dashboard")
