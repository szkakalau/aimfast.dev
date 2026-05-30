"""
星球文章生成器
输入: ./daily/YYYY-MM-DD/signals.json（处理后的信号）
输出: ./daily/YYYY-MM-DD/article.md（智识星球公开文章）
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
CONFIG_PATH = ROOT / "config.json"

TZ_SHANGHAI = timezone(timedelta(hours=8))

# 文章类型定义
ARTICLE_TYPES = {
    "opportunity_deep_dive": {"label": "机会深挖", "ratio": 0.40},
    "counter_intuitive": {"label": "反直觉洞察", "ratio": 0.25},
    "methodology": {"label": "方法论教学", "ratio": 0.20},
    "trend_alert": {"label": "趋势预警", "ratio": 0.10},
    "failure_postmortem": {"label": "失败复盘", "ratio": 0.05},
}


def load_signals(date_str: str) -> list[dict]:
    path = DAILY_DIR / date_str / "signals.json"
    if not path.exists():
        print(f"[文章] {path} 不存在，无法生成文章")
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("signals", [])


def load_methodology() -> str:
    if METHODOLOGY_PATH.exists():
        return METHODOLOGY_PATH.read_text(encoding="utf-8")
    return ""


def _get_recent_article_types(date_str: str, lookback: int = 3) -> list[str]:
    """获取最近 N 天的文章类型，用于轮换判断。"""
    types: list[str] = []
    today = datetime.strptime(date_str, "%Y-%m-%d")
    for i in range(1, lookback + 1):
        prev = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        prev_path = DAILY_DIR / prev / "article.json"
        if prev_path.exists():
            try:
                meta = json.loads(prev_path.read_text(encoding="utf-8"))
                types.append(meta.get("type", ""))
            except Exception:
                pass
    return types


def select_topic(signals: list[dict], date_str: str) -> dict:
    """
    从当日信号中选题。
    按类型占比 + 轮换规则选择今天要写的角度。

    返回 {type, signal, angle, reason}
    """
    config = {}
    try:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass

    max_consecutive = config.get("content", {}).get("planet_article", {}).get("max_consecutive_same_type", 2)
    recent_types = _get_recent_article_types(date_str)

    # 如果最近 2 天连续同一类型，排除该类型
    excluded_types: set[str] = set()
    if len(recent_types) >= max_consecutive and len(set(recent_types[:max_consecutive])) == 1:
        excluded_types.add(recent_types[0])
        print(f"[文章] 连续 {max_consecutive} 天「{recent_types[0]}」，本轮排除")

    # 按信号特征匹配文章类型
    candidates: dict[str, list[dict]] = {t: [] for t in ARTICLE_TYPES}

    for s in signals:
        score = s.get("score", 0)
        cross = s.get("cross_platform_count", 0)
        tags = [t for t in s.get("tags", []) if isinstance(t, str)]
        text = f"{s.get('title', '')} {s.get('summary', '')} {' '.join(tags)}".lower()

        # 机会深挖: 高分 + 跨平台 + 可行动
        if score >= 12 and cross >= 2:
            candidates["opportunity_deep_dive"].append(s)

        # 反直觉洞察: 与主流叙事矛盾或 cooling 标签
        if s.get("cooling") or any(kw in text for kw in ["counter", "反直觉", "surprising", "unexpected"]):
            candidates["counter_intuitive"].append(s)

        # 方法论教学: show_hn 或 product-launch 类型（适合展示"如何发现"）
        if s.get("signal_type") in ("show_hn", "product-launch") or any(
            kw in text for kw in ["build", "how to", "方法论", "教程", "经验"]
        ):
            candidates["methodology"].append(s)

        # 趋势预警: cooling 标签或降温关键词
        if s.get("cooling") or any(kw in text for kw in ["降温", "declining", "cooling", "fading"]):
            candidates["trend_alert"].append(s)

        # 失败复盘: 从 tracking/lessons.json 匹配（此处用低分跨平台信号作为候补）
        if score < 5 and cross >= 2:
            candidates["failure_postmortem"].append(s)

    # 按优先级选择类型
    type_order = ["opportunity_deep_dive", "counter_intuitive", "methodology", "trend_alert", "failure_postmortem"]

    for atype in type_order:
        if atype in excluded_types:
            continue
        if candidates[atype]:
            best_signal = max(candidates[atype], key=lambda s: s.get("score", 0))
            return {
                "type": atype,
                "type_label": ARTICLE_TYPES[atype]["label"],
                "signal": best_signal,
                "angle": _generate_angle(best_signal, atype),
                "reason": f"类型: {ARTICLE_TYPES[atype]['label']} | 信号: {best_signal.get('title', '')[:60]} | 分数: {best_signal.get('score', 0)}",
            }

    # fallback: 取最高分信号做机会深挖
    if signals:
        best = signals[0]
        return {
            "type": "opportunity_deep_dive",
            "type_label": "机会深挖",
            "signal": best,
            "angle": _generate_angle(best, "opportunity_deep_dive"),
            "reason": f"Fallback | 信号: {best.get('title', '')[:60]} | 分数: {best.get('score', 0)}",
        }

    return {"type": "opportunity_deep_dive", "type_label": "机会深挖", "signal": {}, "angle": "今日无合适选题", "reason": "无信号"}


def _generate_angle(signal: dict, atype: str) -> str:
    """根据信号和类型生成选题角度描述。"""
    title = signal.get("title", "未知")
    score = signal.get("score", 0)
    cross = signal.get("cross_platform_count", 0)

    angles = {
        "opportunity_deep_dive": f"从 {cross} 个平台的讨论中，我发现了一个被忽视的产品机会",
        "counter_intuitive": f"大家都在关注 X，但真正的机会可能在相反的方向",
        "methodology": f"我是怎么从 {score} 分的信号中发现这个方向的——完整拆解",
        "trend_alert": f"这个方向正在降温，追高需谨慎",
        "failure_postmortem": f"这个信号看起来很强，但验证后发现了一个关键问题",
    }
    return angles.get(atype, f"关于「{title[:40]}」的深度分析")


def _build_system_prompt() -> str:
    """构建系统提示：写作规范 + BuilderPulse 蒸馏风格 + 文章模板。"""
    methodology = load_methodology()

    return f"""你是 KAKAOPC 情报科的专栏作者，为「智识星球」撰写独立开发者情报分析文章。你的文章风格不是一个分析师在写报告，而是一个有经验的 Builder 在和朋友聊天。

## 写作方法论

{methodology}

## 文章写作铁律

### 标题铁律
- ≤ 30 字
- 必须有具体数字或对比（"3 个信号""从 0 到 $500""为什么不是 X 而是 Y"）
- 制造好奇心缺口——但不能是标题党
- 禁止: "深度分析""浅谈""浅析""思考""探索"等空洞词

### 开头铁律（最重要）
- **第一句必须是一个具体场景、具体人物、或具体数据点**
- 禁止: "随着 AI 技术的发展…""在当今数字化时代…""近年来…""最近…"
- 正确示例:
  - "周二下午，Reddit r/SaaS 上一个帖子收到了 847 条评论。"
  - "一位土耳其创始人的焦虑应用，收到了第一笔 $3 付款。"
  - "Hacker News 上 417 个开发者在争论同一件事：AI 写的代码，谁负责评审？"

### 正文铁律
- **每 300 字至少一个具体数字或直接引用**
- 观点 → 证据 → 白话翻译 → 行动启示（四段式，不是两段式）
- 引用格式: "(来源: HN, 417 评论)" 或 "(Reddit, $3 出价)"
- 引入技术术语时必须在同一句中用白话解释

### 白话翻译原则
- 不假设读者懂任何缩写
- "AI agent" → "能代表用户调用工具和采取步骤的软件"
- "self-hosted" → "软件跑在你自己的服务器上，而不是供应商那里"
- "local-first" → "文件先在自己的机器上可用，云端分享是可选的"

### 买家命名
- 每当你描述一个产品机会时，必须回答:
  - **谁会最先付钱？**（具体到角色）
  - **为什么是现在？**（什么变了）
  - **定价锚点**: $19 一次性 / $9-29/月监控？

### 结尾铁律
- 必须以"如果是我"的具体行动收尾——不是泛泛的"值得关注"
- 必须有失败条件——**什么情况下这个判断是错的**
- 承认不确定性——"我可能错了，但数据指向…"

### 语气铁律
- 像一个有经验的 Builder 在和你聊天，不是分析师报告
- 不装、不吹、不贩卖焦虑
- 用"你"和"我"，不用"开发者们"和"我们认为"
- 短句为主，一段不超过 4 句

### SEO 铁律（搜索引擎优化）
- **标题**: 25-35 字，包含核心关键词和具体数字，有搜索吸引力。生成后额外给出一个 30-60 字符的英文 slug（如 "vercel-zerolang-opportunity"）
- **元描述**: 文章的第一段（150-160 字符）必须能独立作为 Google 搜索摘要，包含核心关键词并清晰传达文章价值
- **标题层级**: 严格 H1 → H2 → H3，不跳级。每个 H2 下至少 150 字
- **关键词自然出现**: 核心关键词在前 200 字内至少出现一次
- **内链建议**: 在正文末尾加一段"相关阅读"，列出 2-3 条可以内链到其他日报/文章的主题（格式：`- 相关阅读：[标题描述]`）
- **结构化内容**: 使用列表、引用块、表格等提升内容可读性，帮助 Google 生成 featured snippet
- **链接文字**: 所有链接使用描述性锚文字，禁止"点击这里"

## 文章结构

1. **我看到一个信号** — 具体场景/数据点引入（必须是一个故事或具体数字）
2. **翻译成人话** — 白话解释 + 谁在疼 + 为什么是现在（含定价锚点）
3. **这背后藏着一个机会** — 产品描述 + 谁会付钱 + 多少钱 + 为什么大多数人会错过
4. **为什么大多数人会错过它** — 主流观点 + 为什么错了 + 数据支撑
5. **如果是我，我会怎么做** — 第一步 + 7 天验证计划 + MVP 方案（Google Form + Markdown 即可）+ 失败条件
6. **本周其他值得关注的信号** — 3-5 条简报（每条 ≤ 80 字）
7. **关于 KAKAOPC 情报科** — 固定结尾

## 字数与格式
- 正文: 2500-5000 字
- 输出完整 Markdown，不要用代码块包裹
- 使用 `##` 和 `###` 做标题层级
- 重要数据用 `**粗体**` 强调"""


def _build_user_prompt(topic: dict, signals: list[dict], date_str: str) -> str:
    """构建用户提示：选题 + 相关信号数据。"""
    atype = topic.get("type", "opportunity_deep_dive")
    type_label = topic.get("type_label", "机会深挖")
    main_signal = topic.get("signal", {})
    angle = topic.get("angle", "")

    # 主信号详情
    main_lines = []
    if main_signal:
        bd = main_signal.get("score_breakdown", {})
        main_lines = [
            f"### 主信号: {main_signal.get('title', 'N/A')}",
            f"- 分数: {main_signal.get('score', 0)} 分 | 跨平台: {main_signal.get('cross_platform_count', 0)}",
            f"- 来源: {main_signal.get('source', '?')}",
            f"- 链接: {main_signal.get('url', 'N/A')}",
            f"- 互动: {main_signal.get('discussion_count', 0)} 讨论 | 参与度: {main_signal.get('engagement', {}).get('total', 0)}",
            f"- 摘要: {main_signal.get('summary', 'N/A')}",
            f"- 标签: {', '.join(main_signal.get('tags', []))}",
            f"- 打分明细: {json.dumps(bd, ensure_ascii=False)}",
        ]

    # 辅助信号（Top 10 中与主信号不同源的）
    related = []
    main_source = main_signal.get("source_key", "") if main_signal else ""
    for s in signals[:15]:
        if s.get("id") != main_signal.get("id"):
            related.append(
                f"- [{s.get('score', 0)}分 | {s.get('source', '?')}] {s.get('title', '')[:100]}\n"
                f"  摘要: {s.get('summary', '')[:120]}"
            )

    return f"""## 日期: {date_str}
## 文章类型: {type_label}
## 选题角度: {angle}

{chr(10).join(main_lines) if main_lines else '无主信号'}

## 辅助信号（Top 15）

{chr(10).join(related) if related else '无辅助信号'}

---

请基于以上选题和数据，生成一篇完整的智识星球文章。

## 文章类型要求
- **{type_label}**: {
    '深入分析一个高确定性机会——说明为什么是现在、谁会付钱（具体角色+定价锚点）、怎么做（第一天做什么、第七天验证什么）、什么情况下这个判断是错的'
    if atype == 'opportunity_deep_dive'
    else '挑战主流观点，用数据说明为什么大多数人的判断是错的——必须给出具体数据和反例'
    if atype == 'counter_intuitive'
    else '拆解信号发现过程，教读者如何自己识别类似机会——包括你的搜索流程、判断标准、踩过的坑'
    if atype == 'methodology'
    else '警告某个方向正在降温，分析原因并给出具体避免建议——哪些行为该停止、哪些方向该转移'
    if atype == 'trend_alert'
    else '诚实复盘一个失败案例——重点在"学到了什么"而非"做错了什么"，给读者可迁移的教训'
}

## 生成指令
1. **开头**: 用一个具体的数据点或场景开始，不要用"随着""近年来""最近"
2. **定价**: 必须给出具体的定价锚点（$X 一次性 / $Y/月）
3. **买家**: 必须点名谁会最先付钱（具体角色）
4. **白话**: 所有技术术语首次出现时必须用白话解释
5. **反方**: 必须写清楚什么情况下这个判断是错的
6. **行动**: "如果是我"部分必须包含具体的第一步和 7 天验证计划
7. **篇幅**: 2500-5000 字
8. **语气**: Builder 聊天的语气，不是分析师报告的口气
9. **SEO 标题**: 标题控制在 25-35 字，包含核心关键词和具体数字
10. **SEO 摘要**: 第一段（150-160 字符）能独立作为 Google 搜索摘要
11. **英文 Slug**: 生成一个英文 kebab-case slug（≤60 字符），如 "vercel-zerolang-opportunity"
"""


def generate_article(topic: dict, signals: list[dict], date_str: str) -> str:
    """调用 LLM 根据选题生成星球文章。"""
    if not topic.get("signal"):
        return f"# KAKAOPC 情报科 — {date_str}\n\n> 今日无合适选题。\n"

    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(topic, signals, date_str)

    print(f"[文章] 上下文: {len(system_prompt)} + {len(user_prompt)} = {len(system_prompt) + len(user_prompt)} 字符")

    article = chat(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.8,
        max_tokens=6144,
    )

    if article.startswith("```"):
        lines = article.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        article = "\n".join(lines)

    return article


def run(date_str: str | None = None) -> str:
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    print(f"\n{'='*50}")
    print(f"[文章] 星球文章生成 — {date}")
    print(f"{'='*50}")

    signals = load_signals(date)
    if not signals:
        print("[文章] 无处理后信号，跳过文章生成")
        write_pipeline_status(date, "article", "skipped",
            reason="no_signals_data",
            message="No signals.json found for today — article generation skipped.")
        return ""

    signals.sort(key=lambda s: s.get("score", 0), reverse=True)

    topic = select_topic(signals, date)
    print(f"[文章] 选题: {topic.get('type_label', 'unknown')} — {topic.get('angle', 'N/A')}")
    print(f"[文章] 理由: {topic.get('reason', 'N/A')}")

    article = generate_article(topic, signals, date)

    output_dir = DAILY_DIR / date
    output_dir.mkdir(parents=True, exist_ok=True)

    # 保存文章
    output_path = output_dir / "article.md"
    output_path.write_text(article, encoding="utf-8")
    print(f"[文章] 文章已保存 → {output_path}")
    print(f"[文章] 字数: {len(article)} 字符")

    write_pipeline_status(date, "article", "generated",
        message=f"Planet article generated: {topic.get('type_label', 'N/A')} ({len(article):,} chars)")

    # 保存选题元数据（供后续轮换判断）
    meta = {
        "date": date,
        "type": topic.get("type", ""),
        "type_label": topic.get("type_label", ""),
        "angle": topic.get("angle", ""),
        "signal_id": topic.get("signal", {}).get("id", ""),
        "signal_title": topic.get("signal", {}).get("title", ""),
    }
    meta_path = output_dir / "article.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return article


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    article = run(today)
    if article:
        try:
            print("\n" + article[:500] + "...")
        except UnicodeEncodeError:
            print(f"\n[Article preview: {len(article)} chars, see daily/{today}/article.md]")
