"""
Trend Discovery Pipeline
Reads daily signals, extracts emerging terms via LLM, maintains trend_terms.json,
and generates research reports using dynamic percentile thresholds.

Report tiers (based on score percentile rank within the day's terms):
  Top 25%  → Full research report (LLM, 8 sections, 2000+ words)
  25%–80%  → SEO brief (LLM, 3 sections, 200-300 words, unique content)
  Bottom 20% → No HTML page (JSON tracking only, score < 10 also skipped)

Briefs are auto-upgraded to full reports when a term's score enters the top 25%.

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


def compute_percentile_thresholds(terms: list[dict]) -> tuple[float, float]:
    """Compute dynamic score thresholds based on percentile distribution.

    Returns (full_report_threshold, brief_threshold) where:
      - full_report_threshold: top 25% of scores
      - brief_threshold: top 80% of scores

    When all terms have low scores, the thresholds reflect the actual
    distribution rather than arbitrary fixed numbers.
    """
    scores = sorted([t.get("score", 0) for t in terms], reverse=True)
    if not scores:
        return 100.0, 100.0
    n = len(scores)
    full_idx = max(0, min(n - 1, int(n * 0.25)))
    brief_idx = max(0, min(n - 1, int(n * 0.80)))
    return float(scores[full_idx]), float(scores[brief_idx])


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

    user_prompt = f"""从以下今日采集的技术社区 signals 中，提取值得追踪的新兴主题。

范围：新概念、新技术、新产品、热门讨论 — 都可以。

提取原则（重要）：
1. 优先提取在多个信号中反复出现的主题（≥2 个独立信源讨论同一概念/产品）
2. 对于新产品/项目：仅当它是某新兴方向的代表时才提取（如多个信号在讨论同一个新范式），而非孤立的"我做了个 App"帖
3. 对于热门讨论：判断讨论量是否值得追踪，单个低分帖子不算
4. 忽略已知通用技术词汇（如 "AI", "React", "Python", "API", "OpenAI", "LLM", "GPT" 等）
5. 最多提取 20 个词，按重要性和讨论度排序。如果没有足够质量的候选，宁可返回少一些

分类体系（category 字段）：
- AIModel: AI & LLM model releases（模型发布、benchmark、权重/API 新模型）
- AIAgent: Agent frameworks, SDKs & protocols（Agent 框架、MCP 协议、Agent 工具链）
- AIApp: AI-powered applications（AI 驱动的应用产品、垂直 AI 工具）
- DevTools: Developer tools & platforms（开发者工具/平台）
- Infra: Cloud, networking, infrastructure（基础设施/云计算/网络）
- OpenSource: Open source projects（值得关注的开源项目/社区）
- DX: Developer experience, methodology, coding trends（开发体验、编程方法论、技术文化讨论）
- Productivity: Productivity & workflow tools（效率工具/工作流）
- Consumer: Consumer products, hardware, IoT（消费产品/硬件/IoT）
- TechConcept: Emerging tech concepts & paradigms（新兴技术概念/范式）
- Industry: Market trends, funding, industry shifts（市场趋势、融资、行业变动、商业策略）
- Design: Design methodology, UX, accessibility（设计方法论、UX、无障碍）

**重要**：category 字段必须精确使用上述 12 个值之一，大小写必须完全匹配。

字段说明（每个元素必须包含以下 5 个字段）：
- canonical: 英文术语名称（MUST be in English — 如果原始信号是中文，翻译为简洁的英文术语。如 "哒哒哒" → "Taptap Break Reminder"，"飞投" → "WebDrop LAN Transfer"。确保英文名自然、可读。）
- canonical_zh: 中文术语名称（如果原始信号有中文名则保留，否则为空字符串）
- category: 分类标签
- summary_zh: 一句话中文摘要，说明为什么值得追踪
- summary_en: 一句话英文摘要（必须填写！不可为空。如果原始信号是中文，翻译成英文。）

只返回 JSON array，不要其他文字。

Signals:
{json.dumps(signal_summaries, ensure_ascii=False, indent=2)}"""

    system_prompt = "You extract emerging themes from tech community signals — new concepts, technologies, products, and hot discussions. IMPORTANT: The 'canonical' field MUST be in English for every entry. If the original signal uses a Chinese name, translate it to a natural, readable English equivalent. The 'canonical_zh' field stores the Chinese name if one exists. Both 'summary_en' and 'summary_zh' are required — never leave summary_en empty. Return only valid JSON array."

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
            # Post-process: ensure canonical is English
            terms = _ensure_english_canonical(terms)
            return terms
    except Exception as e:
        print(f"  [trends] LLM extraction failed: {e}, falling back to keyword method")

    # Fallback: tag-based extraction
    return _extract_terms_keyword_fallback(signals)


def _has_chinese(text: str) -> bool:
    """Check if text contains Chinese characters."""
    return any('一' <= c <= '鿿' or '㐀' <= c <= '䶿' for c in text)


def _ensure_english_canonical(terms: list[dict]) -> list[dict]:
    """Post-process: if canonical contains Chinese, translate to English via LLM."""
    chinese_terms = [t for t in terms if _has_chinese(t.get("canonical", ""))]
    if not chinese_terms:
        return terms

    print(f"  [trends] Found {len(chinese_terms)} Chinese canonical names, translating...")
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from llm_client import chat

        chinese_names = [t["canonical"] for t in chinese_terms]
        translate_prompt = f"""Translate these Chinese tech product/term names to concise, natural English equivalents.
Return a JSON object mapping each Chinese name to its English translation.

Chinese names:
{json.dumps(chinese_names, ensure_ascii=False)}

Example translations:
- "哒哒哒" → "Taptap Break Reminder"
- "飞投" → "WebDrop LAN Transfer"
- "AI Agent 自编辑溯源问题" → "AI Agent Self-Editing Provenance"
- "AI 编程工具作为招聘信号" → "AI Coding Tools as Hiring Signals"

Return ONLY a JSON object: {{"chinese_name": "english translation", ...}}"""

        response = chat(
            "You are a translator specializing in Chinese→English tech terminology. Return only valid JSON.",
            translate_prompt,
        )
        response = response.strip()
        if response.startswith("```"):
            response = response.split("\n", 1)[1]
            if response.endswith("```"):
                response = response[:-3]
        translations = json.loads(response)

        if isinstance(translations, dict):
            for t in terms:
                cn = t.get("canonical", "")
                if cn in translations and translations[cn]:
                    t["canonical_zh"] = cn  # Preserve original Chinese as canonical_zh
                    t["canonical"] = translations[cn]
                    print(f"  [trends]   Translated: '{cn}' → '{translations[cn]}'")
    except Exception as e:
        print(f"  [trends] Canonical translation failed: {e}, keeping original names")

    return terms


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
            "canonical_zh": "",
            "category": "DevTools",
            "summary_zh": f"与 {tag} 相关的新兴趋势，今日出现在多个技术社区信源中。",
            "summary_en": f"An emerging trend related to {tag}, appearing across multiple tech community sources today.",
        })

    return terms[:20]


def _make_slug_id(canonical: str, fallback_idx: int = 0) -> str:
    """Generate a URL-safe English slug from canonical name.

    If the canonical contains Chinese characters, extracts the ASCII portion
    (e.g. 'GPT-5.6 / Grok-4.5' from '超大模型发布与测试（GPT-5.6 / Grok-4.5）').
    Falls back to a hash-based ID if no ASCII content is found.
    """
    import re, hashlib, unicodedata

    # If already English, just slugify
    if not _has_chinese(canonical):
        slug = re.sub(r'[^\w\s\-.]', '', canonical.lower()).strip()
        slug = re.sub(r'[-\s]+', '-', slug)[:50]
        return f"trend-{slug}"

    # Mixed Chinese + English — extract ASCII/English parts
    # Match Latin words, numbers, common tech abbreviations
    ascii_parts = re.findall(r'[A-Za-z0-9]+(?:[.\-+/][A-Za-z0-9]+)*', canonical)
    if ascii_parts:
        # Join significant parts (skip Chinese punctuation context)
        meaningful = [p for p in ascii_parts if len(p) >= 2 or p.isdigit()]
        if meaningful:
            slug = '-'.join(p.lower() for p in meaningful)[:50]
            return f"trend-{slug}"

    # Pure Chinese — use hash-based fallback
    h = hashlib.md5(canonical.encode()).hexdigest()[:8]
    return f"trend-term-{h}"


def _normalize_category(cat: str) -> str:
    """Normalize category to canonical form (title case, handle known variants)."""
    if not cat or not cat.strip():
        return "General"
    cat = cat.strip()
    mapping = {
        # AI family
        "aimodel": "AIModel",
        "ai model": "AIModel",
        "ai/llm": "AIModel",
        "llm": "AIModel",
        "aiagent": "AIAgent",
        "ai agent": "AIAgent",
        "agent": "AIAgent",
        "aiapp": "AIApp",
        "ai app": "AIApp",
        # Other categories
        "product": "Productivity",
        "project": "OpenSource",
        "opensource": "OpenSource",
        "open source": "OpenSource",
        "oss": "OpenSource",
        "infra": "Infra",
        "infrastructure": "Infra",
        "techconcept": "TechConcept",
        "tech concept": "TechConcept",
        "devtools": "DevTools",
        "dev tools": "DevTools",
        "hottopic": "Industry",
        "hot topic": "Industry",
        "dx": "DX",
        "productivity": "Productivity",
        "consumer": "Consumer",
        "industry": "Industry",
        "design": "Design",
        "general": "General",
    }
    key = cat.lower()
    if key in mapping:
        return mapping[key]
    return cat[0].upper() + cat[1:]


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
            # Update canonical_zh if newly provided
            cn_zh = extracted_term.get("canonical_zh", "").strip()
            if cn_zh and not t.get("canonical_zh"):
                t["canonical_zh"] = cn_zh
            # Update summary_en if existing is empty
            new_summary_en = extracted_term.get("summary_en", "").strip()
            if new_summary_en and not t.get("summary_en"):
                t["summary_en"] = new_summary_en
        else:
            # New term
            new_id = _make_slug_id(canonical)
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
                "canonical_zh": extracted_term.get("canonical_zh", "").strip(),
                "aliases": [],
                "first_seen": today_str,
                "last_seen": today_str,
                "stage": "nascent",
                "score": score,
                "source_count": len(signal_sources),
                "total_mentions": len(matching_signals),
                "sources": signal_sources,
                "growth_pct": 100,
                "category": _normalize_category(extracted_term.get("category", "General")),
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


def _is_brief(filepath: Path) -> bool:
    """Detect if an existing report file is a template brief (not a full research report).

    Template briefs have 'status: tracking' in frontmatter or '追踪阶段' in the body.
    Full research reports have neither marker.
    """
    if not filepath.exists():
        return False
    try:
        head = filepath.read_text(encoding="utf-8")[:800]
    except Exception:
        return False
    return "status: tracking" in head or "追踪阶段" in head


def generate_research_report(term: dict) -> int:
    """Generate research reports for a term via LLM — BOTH Chinese and English.
    Returns count of new files written (0-2)."""
    slug = term["id"].replace("trend-", "")
    zh_path = CONTENT_DIR / f"{slug}.md"
    en_path = CONTENT_DIR / f"{slug}-en.md"

    written = 0

    # Load prompt template
    template_path = TEMPLATES_DIR / "trend_research_prompt.md"
    if template_path.exists():
        template = template_path.read_text(encoding="utf-8")
    else:
        template = _default_research_prompt()

    # ── Chinese report ──
    if not zh_path.exists():
        user_prompt_zh = template.replace("{canonical}", term["canonical"])
        user_prompt_zh = user_prompt_zh.replace("{category}", term.get("category", "General"))
        user_prompt_zh = user_prompt_zh.replace("{summary_zh}", term.get("summary_zh", ""))
        user_prompt_zh = user_prompt_zh.replace("{summary_en}", term.get("summary_en", ""))
        user_prompt_zh = user_prompt_zh.replace("{sources}", ", ".join(term.get("sources", [])))
        user_prompt_zh = user_prompt_zh.replace("{first_seen}", term.get("first_seen", ""))
        user_prompt_zh = user_prompt_zh.replace("{stage}", term.get("stage", "nascent"))
        user_prompt_zh = user_prompt_zh.replace("{score}", str(term.get("score", 0)))
        user_prompt_zh = user_prompt_zh.replace("{source_count}", str(term.get("source_count", 0)))
        user_prompt_zh = user_prompt_zh.replace("{total_mentions}", str(term.get("total_mentions", 0)))

        system_prompt_zh = "You write technical trend research reports for indie developers. Use Chinese (zh-CN)."

        try:
            sys.path.insert(0, str(ROOT / "scripts"))
            from llm_client import chat

            report_zh = chat(system_prompt_zh, user_prompt_zh)
            CONTENT_DIR.mkdir(parents=True, exist_ok=True)
            zh_path.write_text(report_zh, encoding="utf-8")
            written += 1
            print(f"  [trends] Generated ZH research report for {term['canonical']}")
        except Exception as e:
            print(f"  [trends] Failed to generate ZH report for {term['canonical']}: {e}")
    else:
        # Still mark as "already exists" for clarity
        pass

    # ── English report ──
    if not en_path.exists():
        en_system = "You write technical trend research reports for indie developers. Use natural, idiomatic English. Target audience: indie hackers, SaaS founders, and software developers worldwide."

        en_template = template.replace(
            "Write a comprehensive trend research report",
            "Write a comprehensive trend research report in English"
        )
        user_prompt_en = en_template.replace("{canonical}", term["canonical"])
        user_prompt_en = user_prompt_en.replace("{category}", term.get("category", "General"))
        user_prompt_en = user_prompt_en.replace("{summary_zh}", term.get("summary_zh", ""))
        user_prompt_en = user_prompt_en.replace("{summary_en}", term.get("summary_en", ""))
        user_prompt_en = user_prompt_en.replace("{sources}", ", ".join(term.get("sources", [])))
        user_prompt_en = user_prompt_en.replace("{first_seen}", term.get("first_seen", ""))
        user_prompt_en = user_prompt_en.replace("{stage}", term.get("stage", "nascent"))
        user_prompt_en = user_prompt_en.replace("{score}", str(term.get("score", 0)))
        user_prompt_en = user_prompt_en.replace("{source_count}", str(term.get("source_count", 0)))
        user_prompt_en = user_prompt_en.replace("{total_mentions}", str(term.get("total_mentions", 0)))

        try:
            sys.path.insert(0, str(ROOT / "scripts"))
            from llm_client import chat

            report_en = chat(en_system, user_prompt_en)
            en_path.write_text(report_en, encoding="utf-8")
            written += 1
            print(f"  [trends] Generated EN research report for {term['canonical']}")
        except Exception as e:
            print(f"  [trends] Failed to generate EN report for {term['canonical']}: {e}")

    return written


def generate_seo_brief(term: dict) -> int:
    """Generate LLM SEO short report for medium-score terms (25th-80th percentile).

    3 sections — What is it / Why now / Who should care — each ~2-3 sentences.
    Every page is LLM-generated with unique content (no templates — Google penalizes
    near-duplicate pages).

    Returns count of new files written (0-2)."""
    slug = term["id"].replace("trend-", "")
    zh_path = CONTENT_DIR / f"{slug}.md"
    en_path = CONTENT_DIR / f"{slug}-en.md"

    canonical = term.get("canonical", "")
    category = term.get("category", "General")
    first_seen = term.get("first_seen", "")
    score = term.get("score", 0)
    stage = term.get("stage", "nascent")
    total_mentions = term.get("total_mentions", 0)
    sources = ", ".join(term.get("sources", []))
    summary_zh = term.get("summary_zh", "")
    summary_en = term.get("summary_en", "")
    now_str = datetime.now(TZ_SHANGHAI).strftime('%Y-%m-%d %H:%M')

    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    written = 0

    # ── Chinese SEO brief ──
    if not zh_path.exists():
        system_zh = "你为独立开发者撰写简洁的技术趋势简报（中文）。每条内容必须基于提供的数据，不可编造。"
        user_zh = f"""写一篇关于 "{canonical}" 的中文短简报。3 个小节，每节 2-3 句。

已知数据：
- 分类: {category}
- 首次发现: {first_seen}
- 评分: {score}/100
- 阶段: {stage}
- 信源: {sources}
- 提及次数: {total_mentions}
- 摘要: {summary_zh}

用 ## 作为小节标题：

## 这是什么
用 2-3 句解释 {canonical} 是什么。

## 为什么现在出现
解释为什么这个术语现在值得关注。引用具体数据：{total_mentions} 次提及，来源包括 {sources}。

## 谁应该关注
哪些开发者/创业者/产品人最应该追踪这个趋势。

基于提供的数据写作，保持事实准确。总计 200-300 字。"""

        try:
            sys.path.insert(0, str(ROOT / "scripts"))
            from llm_client import chat

            report = chat(system_zh, user_zh)
            header = f"""---
title: "{canonical}"
category: {category}
first_seen: {first_seen}
score: {score}
stage: {stage}
status: tracking
generated: {now_str} CST
---

"""
            zh_path.write_text(header + report, encoding="utf-8")
            written += 1
            print(f"  [trends] Generated ZH SEO brief for {canonical}")
        except Exception as e:
            print(f"  [trends] Failed ZH SEO brief for {canonical}: {e}")

    # ── English SEO brief ──
    if not en_path.exists():
        en_system = "You write concise trend briefings in English for indie developers and SaaS founders. Every claim must be grounded in the provided data — do not fabricate."
        user_en = f"""Write a short trend briefing for "{canonical}" in English. 3 sections, 2-3 sentences each.

Known data:
- Category: {category}
- First seen: {first_seen}
- Score: {score}/100
- Stage: {stage}
- Sources: {sources}
- Mentions: {total_mentions}
- Summary: {summary_en}

Use ## for section headers:

## What is it
2-3 sentences explaining what {canonical} is.

## Why now
Why this term matters now. Reference the data: {total_mentions} mentions across {sources}.

## Who should care
Which indie developers, founders, or product people should track this.

Ground every claim in the provided data. Total ~200-300 words."""

        try:
            report = chat(en_system, user_en)
            header = f"""---
title: "{canonical}"
category: {category}
first_seen: {first_seen}
score: {score}
stage: {stage}
status: tracking
generated: {now_str} CST
---

"""
            en_path.write_text(header + report, encoding="utf-8")
            written += 1
            print(f"  [trends] Generated EN SEO brief for {canonical}")
        except Exception as e:
            print(f"  [trends] Failed EN SEO brief for {canonical}: {e}")

    return written


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

    # Compute dynamic percentile thresholds
    full_threshold, brief_threshold = compute_percentile_thresholds(updated_terms)
    print(f"[trends] Percentile thresholds: full report ≥{full_threshold:.0f}, SEO brief ≥{brief_threshold:.0f}")

    # ── Three-tier report generation ──
    #   Top 25%     → full research report (LLM, 8 sections)
    #   25%–80%     → SEO brief (LLM, 3 sections, unique content)
    #   Bottom 20%  → no HTML page (JSON tracking only)
    #   score < 10  → absolute minimum quality gate (noise rejection)
    reports_generated = 0
    briefs_generated = 0
    upgraded = 0

    for term in updated_terms:
        score = term.get("score", 0)
        slug = term["id"].replace("trend-", "")
        zh_path = CONTENT_DIR / f"{slug}.md"
        en_path = CONTENT_DIR / f"{slug}-en.md"

        # Absolute minimum quality gate — filter out pure noise
        if score < 10:
            continue

        if score >= full_threshold:
            zh_is_brief = _is_brief(zh_path)
            en_is_brief = _is_brief(en_path)

            need_gen = not zh_path.exists() or zh_is_brief or not en_path.exists() or en_is_brief
            if need_gen:
                # Remove brief files so generate_research_report writes full versions
                if zh_is_brief:
                    zh_path.unlink()
                if en_is_brief:
                    en_path.unlink()
                if zh_is_brief or en_is_brief:
                    upgraded += 1
                    print(f"[trends] ↑ Upgrading brief → full report: {term['canonical']} (score={score})")
                else:
                    missing = []
                    if not zh_path.exists():
                        missing.append("ZH")
                    if not en_path.exists():
                        missing.append("EN")
                    print(f"[trends] Generating research report for {term['canonical']} (score={score}, missing: {', '.join(missing)})...")
                if not args.dry_run:
                    reports_generated += generate_research_report(term)
        elif score >= brief_threshold:
            if not zh_path.exists():
                print(f"[trends] Generating SEO brief for {term['canonical']} (score={score})...")
                if not args.dry_run:
                    briefs_generated += generate_seo_brief(term)
        # else: bottom 20% — score too low, no page generated

    parts = [
        f"{reports_generated} report files",
        f"{briefs_generated} SEO brief files",
    ]
    if upgraded > 0:
        parts.append(f"{upgraded} upgraded from brief")
    print(f"[trends] Generated {' + '.join(parts)} (ZH+EN)")

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
