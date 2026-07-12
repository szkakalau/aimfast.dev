"""
第六层：Term 研究报告生成器
────────────────────────────
从 Layers 1-5 的 term 数据库中读取高评分 term，
生成包含 12 个板块的深度研究报告。

各 term 的数据来自:
  - canonical_terms.json → stage, age, aliases, sources, score
  - term_index.json     → 完整 mention 历史（source, date, title）
  - term_scores.json    → 五因子评分 breakdown

触发阈值:
  score ≥ 60 → 完整研究报告（12 板块，LLM 生成）
  score 30-59 → 快速简报（模板生成，提示需要更多信号）
  score < 30 → 跳过

输出:
  - content/terms/{slug}.md (中文) + {slug}-en.md (英文)
  - 更新 canonical_terms.json 的 research 字段
"""
import json
import re
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACKING_DIR = ROOT / "tracking"
CONTENT_DIR = ROOT / "content" / "terms"

TZ_SHANGHAI = timezone(timedelta(hours=8))
CANONICAL_PATH = TRACKING_DIR / "canonical_terms.json"
TERM_INDEX_PATH = TRACKING_DIR / "term_index.json"
SCORES_PATH = TRACKING_DIR / "term_scores.json"
STAGES_PATH = TRACKING_DIR / "term_stages.json"

# ── 阈值 ────────────────────────────────────────────
# 百分位阈值: 基于当日实际分数分布动态计算，而非固定数字
#   top 25% → 完整研究报告
#   25-80%  → 快速追踪简报
#   80-100% → 跳过
FULL_RESEARCH_PCT = 0.25       # top 25% → 完整报告
QUICK_BRIEF_PCT = 0.80         # top 80% → 简报（底部 20% 跳过）
MAX_FULL_REPORTS_PER_DAY = 5   # 每日最多生成 5 篇完整报告（控制 LLM 成本）
ABSOLUTE_MIN_SCORE = 10        # 绝对最低分: 低于此分的 term 在任何情况下都跳过

# ── 报告 Prompt ────────────────────────────────────────

RESEARCH_SYSTEM_PROMPT = """你是一位技术趋势分析师，为独立开发者撰写深度机会研究报告。

## 写作原则
1. **证据驱动**: 每条判断必须引用具体数据（"在 3 个信源被提及 12 次"而不是"很多人讨论"）
2. **行动导向**: 不只要告诉读者"这是什么"，更要告诉"今天能做什么"
3. **反方制度化**: 每个推荐必须附带失败条件
4. **翻译优先**: 技术术语必须翻译成普通开发者能理解的商业含义
5. **具体胜于抽象**: 说"$9.99/月订阅制"而不是"可以考虑订阅模式"

## 输出格式
严格的 12 个板块，每个板块以 `## 板块名` 开头。"""


def _build_research_prompt(term: dict, mentions: list[dict], score_detail: dict | None) -> str:
    """为单个 term 构建研究提示。"""
    from scripts.defaults import sanitize_for_llm
    name = sanitize_for_llm(term.get("term", term.get("canonical", "")), strip_markdown=False)
    term_type = term.get("term_type", "unknown")
    stage = term.get("stage", "nascent")
    age = term.get("age_days", 0)
    score = term.get("score", 0)
    sources = term.get("sources", {})
    distinct_sources = term.get("distinct_sources", 1)
    appearances = term.get("appearances", 0)
    first_seen = term.get("first_seen", "")
    last_seen = term.get("last_seen", "")
    aliases = term.get("aliases", [])

    # 构建提及时间线
    mention_dates = defaultdict(int)
    mention_sources = defaultdict(list)
    for m in mentions:
        d = m.get("date", "")
        src = m.get("source", "")
        if d:
            mention_dates[d] += 1
            if src not in mention_sources[d]:
                mention_sources[d].append(src)

    timeline = []
    for d in sorted(mention_dates.keys())[-10:]:
        timeline.append(f"  {d}: {mention_dates[d]} 次提及 ({', '.join(mention_sources[d][:3])})")
    timeline_str = "\n".join(timeline) if timeline else "无历史数据"

    # 来源分解
    source_breakdown = "\n".join(
        f"  {src}: {count} 次" for src, count in sorted(sources.items(), key=lambda x: -x[1])
    )

    # 评分分解
    score_breakdown = ""
    if score_detail:
        bd = score_detail.get("breakdown", {})
        score_breakdown = "\n".join(
            f"  {k}: 原始值={v.get('raw','?')}, 得分={v.get('score','?')}/10"
            for k, v in bd.items()
        )

    stage_label = {
        "nascent": "Nascent (0-7天, 最早发现阶段)",
        "emergent": "Emergent (8-30天, 正在扩散)",
        "validating": "Validating (31-90天, 需要验证真伪)",
        "rising": "Rising (91+天, 已被市场确认)",
    }.get(stage, stage)

    return f"""请为术语 **{name}** 撰写一份深度机会研究报告。

## 已知数据

| 维度 | 数据 |
|------|------|
| 术语名称 | {name} |
| 别名/变体 | {', '.join(aliases) if aliases else '无'} |
| 类型 | {term_type} |
| 首次发现 | {first_seen} |
| 最近出现 | {last_seen} |
| 年龄 | {age} 天 |
| 当前阶段 | {stage_label} |
| 趋势评分 | {score}/100 |
| 独立信源数 | {distinct_sources} |
| 总提及次数 | {appearances} |

### 来源分布
{source_breakdown}

### 近期提及时间线
{timeline_str}

### 评分分解
{score_breakdown}

## 报告要求

严格按以下 12 个板块撰写，每个板块用 `## 板块名`：

### ## 1. What is it（这是什么）
80-120 字。用通俗中文解释 {name} 是什么。一个独立开发者能 30 秒看懂。

### ## 2. Why now（为什么现在）
100-150 字。为什么这个时间点出现？市场变化、技术突破、用户需求？

### ## 3. Market Evidence（市场证据）
80-120 字。跨平台验证情况：{distinct_sources} 个独立信源、{appearances} 次提及。引用具体来源和时间线。

### ## 4. Who's Behind It（谁在推动）
80-120 字。关键公司、组织、个人或社区。

### ## 5. Growth Trajectory（增长轨迹）
80-100 字。基于提及时间线判断趋势：加速增长 / 稳定 / 衰减。预测 30 天和 90 天后的状态。

### ## 6. Commercial Opportunities（商业化机会）
100-150 字。2-3 个具体方向，每个含目标用户和定价建议。

### ## 7. SEO Opportunity（SEO 机会）
80-100 字。3 个长尾关键词，搜索量趋势，竞争程度评估。

### ## 8. Domain Opportunity（域名机会）
60-80 字。3 个可用域名创意（.com / .dev / .ai），含品牌化建议。

### ## 9. Product Ideas（产品创意）
120-180 字。2-3 个具体产品创意，每个含名称、一句话描述、为什么现在做。

### ## 10. Related Companies（相关公司）
60-80 字。值得关注的竞品或生态公司。

### ## 11. Risk Factors（风险因素）
60-80 字。什么时候这个判断会错？什么情况下产品会失败？

### ## 12. Action Plan（行动建议）
80-120 字。独立开发者今天可以采取的具体行动。第一步行什么？如何低成本验证？

## 格式要求
- 全文中文
- 数据直接引用提供的数字
- 保持客观分析语气
- 每个板块之间空行分隔"""


def _call_llm_research(prompt: str, language: str = "zh") -> str:
    """调用 LLM 生成研究报告。"""
    try:
        from scripts.llm_client import chat

        if language == "en":
            system = "You write technical trend research reports for indie developers and SaaS founders. Write in idiomatic, natural English."
        else:
            system = RESEARCH_SYSTEM_PROMPT

        raw = chat(
            system_prompt=system,
            user_prompt=prompt,
            temperature=0.6,
            max_tokens=4096,
        )
        return raw.strip()
    except Exception as e:
        print(f"  [Research] LLM 调用失败: {e}")
        return ""


# Windows 保留文件名（大小写不敏感）
_WINDOWS_RESERVED = {
    "con", "prn", "aux", "nul",
    "com1", "com2", "com3", "com4", "com5", "com6", "com7", "com8", "com9",
    "lpt1", "lpt2", "lpt3", "lpt4", "lpt5", "lpt6", "lpt7", "lpt8", "lpt9",
}


def _make_slug(name: str) -> str:
    """从 term 名生成 URL-safe slug。"""
    # 保留英文/数字/连字符/点
    slug = re.sub(r"[^\w\s\-.]", "", name.lower()).strip()
    # 折叠连续点为单点（防止 "...." → 路径遍历）
    slug = re.sub(r"\.{2,}", ".", slug)
    # 去掉首尾点
    slug = slug.strip(".")
    # 空格/连字符归一化
    slug = re.sub(r"[-\s]+", "-", slug)[:60]
    # 检测 Windows 保留文件名 → 追加后缀避免文件创建失败
    if slug in _WINDOWS_RESERVED:
        slug = f"{slug}-term"
    return slug or "term"


def _generate_full_report(
    term: dict, mentions: list[dict], score_detail: dict | None, date_str: str
) -> int:
    """生成完整研究报告（中英文）。返回写入的文件数。"""
    name = term.get("term", "")
    slug = _make_slug(name)
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)

    prompt_zh = _build_research_prompt(term, mentions, score_detail)
    written = 0

    # 中文报告
    zh_path = CONTENT_DIR / f"{slug}.md"
    if not zh_path.exists():
        report_zh = _call_llm_research(prompt_zh, "zh")
        if report_zh:
            # 添加 frontmatter
            header = f"""---
term: "{name}"
type: {term.get('term_type', 'unknown')}
stage: {term.get('stage', 'nascent')}
score: {term.get('score', 0)}
first_seen: {term.get('first_seen', '')}
generated_at: {datetime.now(TZ_SHANGHAI).isoformat()}
language: zh
---

"""
            zh_path.write_text(header + report_zh, encoding="utf-8")
            written += 1
            print(f"  [Research] 生成中文报告: {slug}.md")

    # 英文报告 — 用英文 prompt
    en_prompt = prompt_zh.replace(
        "请为术语 **", "Write a deep-dive opportunity research report for **"
    ).replace("撰写一份深度机会研究报告", "in English")
    # 替换中文指令为英文
    en_prompt = re.sub(r"## 报告要求.*", "## Requirements\nWrite the entire report in English.", en_prompt, flags=re.DOTALL)
    en_prompt = re.sub(r"### ## \d+\..*?(?=###|\Z)", "", en_prompt, flags=re.DOTALL)

    en_path = CONTENT_DIR / f"{slug}-en.md"
    if not en_path.exists():
        # 直接用中文 prompt + 英文 system 指令
        report_en = _call_llm_research(prompt_zh, "en")
        if report_en:
            header = f"""---
term: "{name}"
type: {term.get('term_type', 'unknown')}
stage: {term.get('stage', 'nascent')}
score: {term.get('score', 0)}
first_seen: {term.get('first_seen', '')}
generated_at: {datetime.now(TZ_SHANGHAI).isoformat()}
language: en
---

"""
            en_path.write_text(header + report_en, encoding="utf-8")
            written += 1
            print(f"  [Research] 生成英文报告: {slug}-en.md")

    return written


def _generate_quick_brief(term: dict, date_str: str) -> int:
    """生成快速追踪简报（模板，无 LLM 开销）。"""
    name = term.get("term", "")
    slug = _make_slug(name)
    term_type = term.get("term_type", "unknown")
    score = term.get("score", 0)
    stage = term.get("stage", "nascent")
    sources = term.get("sources", {})
    sources_str = ", ".join(f"{s}({c})" for s, c in sorted(sources.items(), key=lambda x: -x[1]))
    first_seen = term.get("first_seen", "")
    appearances = term.get("appearances", 0)

    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    written = 0

    # 中文简报
    zh_path = CONTENT_DIR / f"{slug}.md"
    if not zh_path.exists():
        brief = f"""---
term: "{name}"
type: {term_type}
stage: {stage}
score: {score}
status: tracking
generated_at: {datetime.now(TZ_SHANGHAI).isoformat()}
---

## {name}

**类型**: {term_type}
**首次发现**: {first_seen}
**信号数**: {appearances}
**来源**: {sources_str}
**评分**: {score}/100

### 追踪状态

> ⚠️ **追踪阶段** — 当前跨源信号量尚不足以触发完整研究报告（需进入 top {FULL_RESEARCH_PCT*100:.0f}% 分数区间）。
> 该术语持续在每日 Pipeline 中接收新信号。当跨平台讨论热度积累到阈值后自动升级为完整机会分析报告。

### 已知信号

该术语从 {len(sources)} 个信源获得 {appearances} 次提及。AimFast.Dev 将持续追踪其发展：
- 每日 18 个信源全覆盖（HN / GitHub / Reddit / V2EX / 官方 Blog / Google News 等）
- 术语评分随跨平台讨论自动增长
- 进入 top {FULL_RESEARCH_PCT*100:.0f}% 分数区间后 → 自动升级为完整机会分析报告

---

*此简报由 AimFast.Dev Term Pipeline 自动生成。最后更新: {datetime.now(TZ_SHANGHAI).strftime('%Y-%m-%d %H:%M')} CST*
"""
        zh_path.write_text(brief, encoding="utf-8")
        written += 1

    # 英文简报
    en_path = CONTENT_DIR / f"{slug}-en.md"
    if not en_path.exists():
        brief_en = f"""---
term: "{name}"
type: {term_type}
stage: {stage}
score: {score}
status: tracking
generated_at: {datetime.now(TZ_SHANGHAI).isoformat()}
---

## {name}

**Type**: {term_type}
**First Seen**: {first_seen}
**Signal Count**: {appearances}
**Sources**: {sources_str}
**Score**: {score}/100

### Tracking Status

> ⚠️ **Tracking Stage** — Current cross-platform signal volume hasn't reached the top {FULL_RESEARCH_PCT*100:.0f}% percentile for a full research report.
> This term continues receiving new signals in the daily pipeline. Full opportunity analysis auto-triggers when discussion reaches threshold.

### Known Signals

{appearances} mentions from {len(sources)} sources. AimFast.Dev continues tracking across 18+ sources daily.
At top {FULL_RESEARCH_PCT*100:.0f}% percentile → auto-generates a full 12-section opportunity report.

---

*Auto-generated by AimFast.Dev Term Pipeline. Last updated: {datetime.now(TZ_SHANGHAI).strftime('%Y-%m-%d %H:%M')} CST*
"""
        en_path.write_text(brief_en, encoding="utf-8")
        written += 1

    return written


def run(date_str: str | None = None):
    """执行研究报告生成。"""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")

    print(f"\n{'='*50}")
    print(f"[Research] 第六层：Term 研究报告生成 — {date}")
    print(f"{'='*50}")

    # Step 1: 加载数据
    if not SCORES_PATH.exists():
        print("[Research] term_scores.json 不存在，跳过")
        return

    scores_data = json.loads(SCORES_PATH.read_text(encoding="utf-8"))
    scored_terms = scores_data.get("scores", [])

    # 加载 term_index 获取 mention 详情
    term_mentions: dict[str, list[dict]] = defaultdict(list)
    if TERM_INDEX_PATH.exists():
        ti = json.loads(TERM_INDEX_PATH.read_text(encoding="utf-8"))
        for term_name, entry in ti.get("terms", {}).items():
            canonical = entry.get("canonical_name", term_name)
            for ref in entry.get("signals", []):
                term_mentions[canonical].append(ref)

    # 构建 score_detail map
    score_map: dict[str, dict] = {s["term"]: s for s in scored_terms}

    # Step 2: 基于百分位计算阈值
    all_scores = sorted([s["score"] for s in scored_terms], reverse=True)
    n = len(all_scores)
    full_threshold = all_scores[max(0, min(n - 1, int(n * FULL_RESEARCH_PCT)))] if n > 0 else 100
    brief_threshold = all_scores[max(0, min(n - 1, int(n * QUICK_BRIEF_PCT)))] if n > 0 else 50
    print(f"[Research] 动态阈值: 完整报告≥{full_threshold:.0f}分 (top {FULL_RESEARCH_PCT*100:.0f}%), 简报≥{brief_threshold:.0f}分")

    # Step 3: 分级处理
    full_reports = 0
    quick_briefs = 0
    skipped = 0

    for s in scored_terms:
        name = s["term"]
        score_val = s["score"]
        mentions = term_mentions.get(name, [])
        score_detail = s

        slug = _make_slug(name)
        zh_exists = (CONTENT_DIR / f"{slug}.md").exists()

        if score_val < ABSOLUTE_MIN_SCORE:
            skipped += 1
            continue

        if score_val >= full_threshold:
            if full_reports >= MAX_FULL_REPORTS_PER_DAY:
                # 今日完整报告配额已满 → 降级为简报
                if not zh_exists:
                    written = _generate_quick_brief(s, date)
                    if written > 0:
                        quick_briefs += 1
                continue

            if not zh_exists:
                written = _generate_full_report(s, mentions, score_detail, date)
                if written > 0:
                    full_reports += 1
            else:
                print(f"  [Research] {name} ({score_val:.0f}分): 报告已存在，跳过")
        elif score_val >= brief_threshold:
            written = _generate_quick_brief(s, date)
            if written > 0:
                quick_briefs += 1
        else:
            skipped += 1

    # Step 3: 更新 canonical_terms.json（标记已研究）
    if CANONICAL_PATH.exists():
        ct = json.loads(CANONICAL_PATH.read_text(encoding="utf-8"))
        for name, entry in ct.get("canonicals", {}).items():
            slug = _make_slug(name)
            zh_path = CONTENT_DIR / f"{slug}.md"
            if zh_path.exists():
                entry["research_md_path"] = f"content/terms/{slug}.md"
                entry["research_generated_at"] = datetime.now(TZ_SHANGHAI).isoformat()
        from scripts.defaults import atomic_write_json
        atomic_write_json(CANONICAL_PATH, ct)

    # Step 4: 输出摘要
    print(f"\n[Research] 生成完成:")
    print(f"  完整研究报告: {full_reports} 篇 (top {FULL_RESEARCH_PCT*100:.0f}%, ≥{full_threshold:.0f}分)")
    print(f"  快速追踪简报: {quick_briefs} 篇 (≥{brief_threshold:.0f}分)")
    print(f"  跳过 (低分): {skipped} 篇 (<{brief_threshold:.0f}分)")

    if full_reports > 0:
        print(f"\n  完整报告列表:")
        for s in scored_terms:
            if s["score"] >= full_threshold and (CONTENT_DIR / f"{_make_slug(s['term'])}.md").exists():
                slug = _make_slug(s["term"])
                if (CONTENT_DIR / f"{slug}.md").exists():
                    print(f"    [{s['score']:.0f}分] {s['term']} → content/terms/{slug}.md")

    print(f"\n[Research] 报告目录: {CONTENT_DIR}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    run(today)
