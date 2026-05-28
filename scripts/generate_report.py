"""
日报生成器
输入: ./daily/YYYY-MM-DD/signals.json（处理后的信号）
输出: ./daily/YYYY-MM-DD/report.md（完整五层日报）
依赖: DeepSeek API（或本地 fallback）
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.llm_client import chat
from scripts.pipeline_status import write as write_pipeline_status

ROOT = Path(__file__).resolve().parent.parent
DAILY_DIR = ROOT / "daily"
TEMPLATES_DIR = ROOT / "templates"
METHODOLOGY_PATH = ROOT / "methodology.md"

TZ_SHANGHAI = timezone(timedelta(hours=8))


def load_signals(date_str: str) -> list[dict]:
    path = DAILY_DIR / date_str / "signals.json"
    if not path.exists():
        print(f"[日报] {path} 不存在，无法生成日报")
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("signals", [])


def load_methodology() -> str:
    if METHODOLOGY_PATH.exists():
        return METHODOLOGY_PATH.read_text(encoding="utf-8")
    return ""


def _categorize_signals(signals: list[dict]) -> dict:
    """将信号按日报板块分类。"""
    categories = {
        "new_products": [],       # 新产品发布
        "search_trends": [],      # 搜索趋势异动
        "github_trending": [],    # GitHub 涨星
        "complaints": [],         # 抱怨热点
        "shutdowns": [],          # 停运/降级
        "growing_tools": [],      # 增长工具
        "model_updates": [],      # 模型动态
        "oss_milestones": [],     # 开源进展
        "pricing": [],            # 定价讨论
        "revival": [],            # 复活信号
        "migration": [],          # 迁移话题
        "trending": [],           # 趋势信号
        "cooling": [],            # 降温信号
    }

    for s in signals:
        stype = s.get("signal_type", "")
        tags = [t for t in s.get("tags", []) if isinstance(t, str)]
        tags_str = " ".join(tags).lower()
        title = s.get("title", "").lower()
        summary = s.get("summary", "").lower()
        text = f"{title} {summary} {tags_str} {stype}"

        if stype in ("product-launch", "show_hn") or any(kw in text for kw in ["launch", "发布", "新产品", "just launched"]):
            categories["new_products"].append(s)
        if stype in ("keyword_trend", "trending_search") or "trends" in s.get("source_key", ""):
            if s.get("cooling"):
                categories["cooling"].append(s)
            elif any(kw in text for kw in ["surging", "rising", "暴涨", "上升"]):
                categories["search_trends"].append(s)
            else:
                categories["trending"].append(s)
        if s.get("source_key") == "github" or "github" in s.get("source", "").lower():
            categories["github_trending"].append(s)
        if stype == "complaint" or any(kw in text for kw in ["抱怨", "太贵", "frustrated", "why is", "too expensive", "problem"]):
            categories["complaints"].append(s)
        if any(kw in text for kw in ["shutdown", "停运", "deprecated", "sunset", "discontinued"]):
            categories["shutdowns"].append(s)
        if any(kw in text for kw in ["growth", "增长", "trending", "star"]):
            categories["growing_tools"].append(s)
        if any(kw in text for kw in ["model", "模型", "llm", "gpt", "claude", "deepseek"]):
            categories["model_updates"].append(s)
        if any(kw in text for kw in ["open source", "开源", "oss", "github"]):
            categories["oss_milestones"].append(s)
        if any(kw in text for kw in ["pricing", "定价", "mrr", "revenue", "收入", "subscription"]):
            categories["pricing"].append(s)
        if any(kw in text for kw in ["revival", "复活", "comeback", "rewrite"]):
            categories["revival"].append(s)
        if any(kw in text for kw in ["migration", "迁移", "switch from", "alternative to", "替代"]):
            categories["migration"].append(s)

    return categories


def _build_system_prompt() -> str:
    """构建系统提示：方法论 + 日报模板 + 写作规范。"""
    methodology = load_methodology()

    return f"""你是 KAKAOPC 情报科的日报主编。你的任务是基于处理后的信号数据，生成一份专业的独立开发者情报日报。

## 方法论

{methodology}

## 写作规范

1. **证据铁律**: 每个判断必须附带具体数字（评论数、star 数、搜索增长率），禁用"很多人""最近很火"等模糊表述。
2. **白话翻译**: 每个技术信号必须翻译成 Builder 能行动的"人话"——这个信号意味着什么产品机会？
3. **反方必答**: 每个推荐必须回答"什么情况下这个判断是错的/这个产品会失败"。
4. **语言**: 全程使用中文，专业术语可保留英文。
5. **篇幅**: 日报正文 1500-3000 字，阅读时间约 5 分钟。

## 日报五层结构

1. **今日核心判断** — 一句话总结今天最重要的发现
2. **🎯 今日一击** — Score ≥ 15 且跨平台验证的最高分信号 → 完整分析（谁会付钱、2h 交付物、定价锚点、counter-view）
3. **📊 Top 3 信号** — 表格：信号名 | 讨论量 | 来源 | 白话翻译
4. **📖 Plain-English Brief** — 每个信号的白话含义 + Builder 视角 + 谨慎视角
5. **🔍 Discovery** — 新产品发布 / 搜索异动 / GitHub 涨星 / 抱怨热点
6. **🛰️ Tech Radar** — 停运降级 / 增长工具 / 模型动态 / 开源进展
7. **🏭 Competitive Intel** — 定价讨论 / 复活信号 / 迁移话题
8. **📈 Trends** — 关键词变迁 / VC 方向 / 降温词 / 新词
9. **🎬 Action** — 2h Build 方案（仅当有 Score ≥ 15 的信号时）
10. **📉 降温提醒** — 连续出现的话题
11. **🔗 来源** — 所有引用的信号链接

输出格式为完整的 Markdown，不要用代码块包裹。"""


def _build_user_prompt(signals: list[dict], categories: dict, date_str: str) -> str:
    """构建用户提示：信号数据 + 具体生成指令。"""
    top5 = signals[:5]
    top_signal = top5[0] if top5 else None

    # Top 5 信号详情
    top5_lines = []
    for i, s in enumerate(top5, 1):
        bd = s.get("score_breakdown", {})
        top5_lines.append(
            f"### {i}. [{s.get('score', 0)}分] {s.get('title', 'N/A')}\n"
            f"- 来源: {s.get('source', '?')} | 跨平台数: {s.get('cross_platform_count', 0)}\n"
            f"- 互动: {s.get('discussion_count', 0)} 讨论 | 参与度: {s.get('engagement', {}).get('total', 0)}\n"
            f"- 链接: {s.get('url', 'N/A')}\n"
            f"- 摘要: {s.get('summary', 'N/A')}\n"
            f"- 标签: {', '.join(s.get('tags', []))}\n"
            f"- 打分明细: {json.dumps(bd, ensure_ascii=False)}\n"
        )

    # 各部门信号摘要
    def _section_signals(key: str, label: str, limit: int = 5) -> str:
        items = categories.get(key, [])[:limit]
        if not items:
            return f"**{label}**: 无"
        lines = [f"**{label}** ({len(categories.get(key, []))} 条):"]
        for s in items:
            lines.append(f"- [{s.get('score', 0)}分] {s.get('title', '')[:80]} — {s.get('source', '')} — {s.get('summary', '')[:100]}")
        return "\n".join(lines)

    sections = [
        _section_signals("new_products", "新产品发布"),
        _section_signals("search_trends", "搜索趋势异动"),
        _section_signals("github_trending", "GitHub 涨星项目"),
        _section_signals("complaints", "开发者抱怨热点"),
        _section_signals("shutdowns", "停运与降级"),
        _section_signals("growing_tools", "增长最快的开发者工具"),
        _section_signals("model_updates", "模型动态"),
        _section_signals("oss_milestones", "开源重要进展"),
        _section_signals("pricing", "独立开发者定价与收入讨论"),
        _section_signals("revival", "复活项目信号"),
        _section_signals("migration", "迁移话题"),
        _section_signals("trending", "趋势信号"),
        _section_signals("cooling", "降温信号"),
    ]

    # 信号总览
    all_signals_brief = []
    for s in signals[:30]:
        all_signals_brief.append(
            f"- [{s.get('score', 0)}分 | {s.get('source', '?')}] {s.get('title', '')[:100]}"
        )

    return f"""## 日期: {date_str}

## 信号总览（Top 30 / 共 {len(signals)} 条）

{chr(10).join(all_signals_brief)}

## Top 5 信号详情

{chr(10).join(top5_lines)}

## 分类信号

{chr(10).join(sections)}

---

请基于以上数据生成 {date_str} 的 KAKAOPC 情报科日报。

重点关注：
- 最高分信号{' (' + top_signal.get("title", "")[:60] + ')' if top_signal else ''} 是否达到 Action 阈值（15 分 + 跨平台 ≥ 3），如达到则生成完整"今日一击"和 Action 方案
- 跨平台验证的信号（≥ 2 个独立源）应优先关注——它们代表真实趋势而非单一平台噪音
- 每个板块如果无相关信号，如实写"今日无显著发现"
- 白话翻译要具体——把技术名词翻译成 Builder 能看到的产品机会
- 每个推荐必须包含 counter-view"""


def generate_report(signals: list[dict], date_str: str) -> str:
    """调用 LLM 生成完整五层日报。"""
    if not signals:
        return f"# KAKAOPC 情报科日报 — {date_str}\n\n> 今日无信号数据。\n"

    categories = _categorize_signals(signals)
    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(signals, categories, date_str)

    print(f"[日报] 上下文: {len(system_prompt)} + {len(user_prompt)} = {len(system_prompt) + len(user_prompt)} 字符")

    report = chat(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.5,
        max_tokens=4096,
    )

    # 如果返回内容已包含 markdown 代码块，去掉包裹
    if report.startswith("```"):
        lines = report.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        report = "\n".join(lines)

    return report


def run(date_str: str | None = None) -> str:
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    print(f"\n{'='*50}")
    print(f"[日报] 日报生成 — {date}")
    print(f"{'='*50}")

    signals = load_signals(date)
    if not signals:
        print("[日报] 无处理后信号，跳过日报生成")
        write_pipeline_status(date, "report", "skipped",
            reason="no_signals_data",
            message="No signals.json found for today — report generation skipped.")
        return ""

    # 按 score 降序
    signals.sort(key=lambda s: s.get("score", 0), reverse=True)

    report = generate_report(signals, date)

    output_dir = DAILY_DIR / date
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "report.md"
    output_path.write_text(report, encoding="utf-8")
    print(f"[日报] 日报已保存 → {output_path}")
    print(f"[日报] 字数: {len(report)} 字符")

    write_pipeline_status(date, "report", "generated",
        message=f"Daily report saved ({len(report):,} chars)")

    return report


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    report = run(today)
    if report:
        try:
            print("\n" + report[:500] + "...")
        except UnicodeEncodeError:
            print(f"\n[Report preview: {len(report)} chars, see daily/{today}/report.md]")
