"""
Action 方案生成器
输入: ./daily/YYYY-MM-DD/signals.json（处理后的信号）
输出: ./daily/YYYY-MM-DD/landing-page.md（Score ≥ 15 + 跨平台 ≥ 3 时触发）
依赖: DeepSeek API
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
TRACKING_DIR = ROOT / "tracking"
METHODOLOGY_PATH = ROOT / "methodology.md"
CONFIG_PATH = ROOT / "config.json"

TZ_SHANGHAI = timezone(timedelta(hours=8))


def load_signals(date_str: str) -> list[dict]:
    path = DAILY_DIR / date_str / "signals.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("signals", [])


def load_methodology() -> str:
    if METHODOLOGY_PATH.exists():
        return METHODOLOGY_PATH.read_text(encoding="utf-8")
    return ""


def check_action_threshold(signals: list[dict]) -> dict | None:
    """检查是否有信号达到 Action 方案生成阈值: Score ≥ 15 且 cross_platform ≥ 3"""
    try:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        config = {"scoring": {"thresholds": {"action_trigger": 15, "cross_platform_min": 3}}}

    threshold = config["scoring"]["thresholds"]["action_trigger"]
    min_platforms = config["scoring"]["thresholds"]["cross_platform_min"]

    for s in signals:
        score = s.get("score", 0)
        platforms = s.get("cross_platform_count", 0)
        if score >= threshold and platforms >= min_platforms:
            return s

    return None


def _build_system_prompt() -> str:
    methodology = load_methodology()

    return f"""你是 KAKAOPC 情报科的 Action 方案规划师。你的任务是为达到阈值的信号生成一份可执行的 2h Build 方案。

## 方法论

{methodology}

## 方案要求

1. **具体可执行**: 每个步骤必须具体到今天就能动手操作的程度。不说"研究竞品"，说"打开 X 的定价页，记录 3 个问题"。
2. **时间约束**: 核心 MVP 必须在 2 小时内完成。超出 2 小时的扩展方案放入"Weekend Expansion"。
3. **定价务实**: 参考 Competitive Intel 中真实讨论的定价锚点，不给拍脑袋的价格。
4. **反方必答**: 每个方案必须有明确的失败条件——什么数据出现说明这个判断是错的。

## 格式要求

输出完整的 Markdown，结构如下:
1. 信号 → 产品映射（表格）
2. 为什么今天这个赢了（排除替代方案 + 赢在哪）
3. MVP 规格（输入/输出/不需要/技术选型/部署时间）
4. 竞争定位（竞品表格 + 差异化）
5. 定价策略（单次/月度/锚点/理由）
6. Landing Page 方案（标题/副标题/卖点/CTA/部署路径）
7. 验证步骤（Day 1-7 具体操作 + 流量策略）
8. Weekend Expansion
9. Counter-view（失败条件 + 市场不存在条件 + 反向信号）

不要用代码块包裹。"""


def _build_user_prompt(top_signal: dict, all_signals: list[dict], date_str: str) -> str:
    """构建用户提示：触发信号 + 相关上下文。"""
    bd = top_signal.get("score_breakdown", {})

    lines = [
        f"## 日期: {date_str}",
        "",
        "## 触发信号",
        f"- 标题: {top_signal.get('title', 'N/A')}",
        f"- 分数: {top_signal.get('score', 0)} 分",
        f"- 跨平台数: {top_signal.get('cross_platform_count', 0)}",
        f"- 来源: {top_signal.get('source', '?')}",
        f"- 链接: {top_signal.get('url', 'N/A')}",
        f"- 讨论量: {top_signal.get('discussion_count', 0)}",
        f"- 参与度: {json.dumps(top_signal.get('engagement', {}), ensure_ascii=False)}",
        f"- 摘要: {top_signal.get('summary', 'N/A')}",
        f"- 标签: {', '.join(top_signal.get('tags', []))}",
        f"- 打分明细: {json.dumps(bd, ensure_ascii=False)}",
        "",
        "## 相关信号上下文（辅助判断竞品和市场规模）",
    ]

    # 找与主信号关键词重叠的信号作为上下文
    main_kw = set(
        w.lower()
        for w in (top_signal.get("title", "") + " " + top_signal.get("summary", "")).split()
        if len(w) > 3
    )
    related = []
    for s in all_signals:
        if s.get("id") == top_signal.get("id"):
            continue
        s_text = (s.get("title", "") + " " + s.get("summary", "")).lower()
        overlap = sum(1 for kw in main_kw if kw in s_text)
        if overlap >= 3:
            related.append(s)

    if related:
        for s in related[:10]:
            lines.append(
                f"- [{s.get('score', 0)}分 | {s.get('source', '?')}] {s.get('title', '')[:100]}"
            )
    else:
        lines.append("*无高度相关信号*")

    lines.extend([
        "",
        "## 同平台高分信号（竞争信号）",
    ])
    same_source = [
        s for s in all_signals
        if s.get("source_key") == top_signal.get("source_key")
        and s.get("id") != top_signal.get("id")
    ]
    for s in same_source[:5]:
        lines.append(f"- [{s.get('score', 0)}分] {s.get('title', '')[:100]}")

    lines.extend([
        "",
        "---",
        "",
        "请基于以上数据生成完整的 Action 方案。",
        "",
        "关键提醒:",
        "- 信号已满足阈值（Score ≥ 15 + 跨平台 ≥ 3），值得认真对待",
        "- 2h Build 必须是具体可执行的——读者能照着操作",
        "- 定价必须基于真实讨论中的锚点，不要拍脑袋",
        "- Counter-view 必须包含具体的反向信号——什么数据出现说明判断错了",
    ])

    return "\n".join(lines)


def generate_action_plan(top_signal: dict, all_signals: list[dict], date_str: str) -> str:
    """调用 LLM 生成完整 2h Build 方案 + Landing Page 方案。"""
    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(top_signal, all_signals, date_str)

    print(f"[Action] 上下文: {len(system_prompt)} + {len(user_prompt)} = {len(system_prompt) + len(user_prompt)} 字符")

    plan = chat(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.6,
        max_tokens=4096,
    )

    if plan.startswith("```"):
        lines = plan.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        plan = "\n".join(lines)

    return plan


def register_opportunity(top_signal: dict, date_str: str) -> str:
    """在追踪表中注册新机会。若当日已有相同信号则跳过。返回 tracking_id。"""
    path = TRACKING_DIR / "opportunities.json"
    if not path.exists():
        print(f"[Action] {path} 不存在，跳过注册")
        return ""

    data = json.loads(path.read_text(encoding="utf-8"))

    # 去重：检查当日是否已有相同标题的机会
    for op in data.get("opportunities", []):
        if op.get("date") == date_str and op.get("opportunity") == top_signal.get("title", ""):
            print(f"[Action] 机会已存在: {op['id']}，跳过注册")
            return op["id"]

    tid = f"OP-{date_str.replace('-', '')}-{len(data['opportunities']) + 1:03d}"

    opportunity = {
        "id": tid,
        "date": date_str,
        "opportunity": top_signal.get("title", "Unknown"),
        "signals": [top_signal.get("source", "")],
        "score": top_signal.get("score", 0),
        "cross_platform_count": top_signal.get("cross_platform_count", 0),
        "buyer": "to-be-determined",
        "landing_page_url": "",
        "lp_status": "not_built",
        "verification_result": "pending",
        "day7_uv": 0,
        "day7_signups": 0,
        "day7_decision": "",
        "current_status": "monitoring",
        "notes": "",
    }
    data["opportunities"].append(opportunity)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[Action] 已注册机会: {tid}")
    return tid


def run(date_str: str | None = None) -> str:
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    print(f"\n{'='*50}")
    print(f"[Action] Action 方案生成 — {date}")
    print(f"{'='*50}")

    signals = load_signals(date)
    if not signals:
        print("[Action] 无处理后信号，跳过")
        write_pipeline_status(date, "action", "skipped",
            reason="no_signals_data",
            message="No processed signals found for today.")
        return ""

    signals.sort(key=lambda s: s.get("score", 0), reverse=True)

    top = check_action_threshold(signals)
    if not top:
        top_score = signals[0].get("score", 0)
        top_cp = max((s.get("cross_platform_count", 0) for s in signals), default=0)
        # Re-read config to get threshold values for the message
        cfg_path = Path(__file__).resolve().parent.parent / "config.json"
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        min_cp = cfg["scoring"]["thresholds"]["cross_platform_min"]
        min_score = cfg["scoring"]["thresholds"]["action_trigger"]
        msg = (
            f"No signals met action threshold (Score >= {min_score}, cross-platform >= {min_cp}). "
            f"Top signal: {top_score} pts / {top_cp} platforms."
        )
        print(f"[Action] {msg}")
        write_pipeline_status(date, "action", "skipped",
            reason="threshold_not_met",
            message=msg)
        return ""

    print(f"[Action] 触发信号: [{top.get('score', 0)}分 | {top.get('cross_platform_count', 0)}平台] {top.get('title', 'N/A')[:60]}")

    tracking_id = register_opportunity(top, date)
    action_plan = generate_action_plan(top, signals, date)

    output_dir = DAILY_DIR / date
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "landing-page.md"
    output_path.write_text(action_plan, encoding="utf-8")
    print(f"[Action] 方案已保存 → {output_path}")
    if tracking_id:
        print(f"[Action] 追踪 ID: {tracking_id}")

    write_pipeline_status(date, "action", "generated",
        message=f"Action plan generated for: {top.get('title', 'N/A')[:80]} (tracking: {tracking_id})")

    return action_plan


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    result = run(today)
    if result:
        try:
            print("\n" + result[:500] + "...")
        except UnicodeEncodeError:
            print(f"\n[Action plan preview: {len(result)} chars, see daily/{today}/landing-page.md]")
