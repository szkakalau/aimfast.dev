"""
周报生成器
输入: daily/ 最近 7 天数据 + tracking/ 历史机会
输出: weekly/YYYY-WW.md
依赖: DeepSeek API
触发: 每周日 20:00
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from scripts.llm_client import chat

ROOT = Path(__file__).resolve().parent.parent
DAILY_DIR = ROOT / "daily"
TRACKING_DIR = ROOT / "tracking"
WEEKLY_DIR = ROOT / "weekly"
METHODOLOGY_PATH = ROOT / "methodology.md"

TZ_SHANGHAI = timezone(timedelta(hours=8))


def load_methodology() -> str:
    if METHODOLOGY_PATH.exists():
        return METHODOLOGY_PATH.read_text(encoding="utf-8")
    return ""


def collect_weekly_data(date_str: str) -> dict:
    """收集本周（过去 7 天）的全部数据。"""
    today = datetime.strptime(date_str, "%Y-%m-%d")
    week_data = {
        "days": [],
        "top_signals": [],       # 去重的本周 Top 信号
        "verified_opportunities": [],  # 本周验证到期或更新的机会
        "new_lessons": [],        # 本周新增经验
        "week_label": "",
    }

    seen_titles: set[str] = set()
    all_signals: list[dict] = []

    for i in range(7):
        d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        signals_path = DAILY_DIR / d / "signals.json"
        report_path = DAILY_DIR / d / "report.md"
        article_path = DAILY_DIR / d / "article.md"

        day_info = {"date": d, "signal_count": 0, "top_score": 0, "has_report": False, "has_article": False}

        if signals_path.exists():
            data = json.loads(signals_path.read_text(encoding="utf-8"))
            day_signals = data.get("signals", [])
            day_info["signal_count"] = data.get("total_raw", len(day_signals))
            day_info["top_score"] = max((s.get("score", 0) for s in day_signals), default=0)
            day_info["action_qualified"] = data.get("summary", {}).get("action_qualified", 0)

            # 收集 Top 信号（去重）
            for s in day_signals[:5]:
                title = s.get("title", "")
                if title not in seen_titles and s.get("score", 0) >= 15:
                    seen_titles.add(title)
                    s["_day"] = d
                    week_data["top_signals"].append(s)
                all_signals.append(s)

        day_info["has_report"] = report_path.exists()
        day_info["has_article"] = article_path.exists()
        week_data["days"].append(day_info)

    # 反转天数顺序（周一 → 周日）
    week_data["days"].reverse()

    # 本周验证结果
    opp_path = TRACKING_DIR / "opportunities.json"
    if opp_path.exists():
        opps = json.loads(opp_path.read_text(encoding="utf-8")).get("opportunities", [])
        week_start = (today - timedelta(days=6)).strftime("%Y-%m-%d")
        for op in opps:
            op_date = op.get("date", "")
            if op_date >= week_start or op.get("verification_result") != "pending":
                week_data["verified_opportunities"].append(op)

    # 本周新增经验
    lessons_path = TRACKING_DIR / "lessons.json"
    if lessons_path.exists():
        lessons = json.loads(lessons_path.read_text(encoding="utf-8")).get("lessons", [])
        week_start = (today - timedelta(days=6)).strftime("%Y-%m-%d")
        for ln in lessons:
            if ln.get("date", "") >= week_start:
                week_data["new_lessons"].append(ln)

    # 周标签
    iso = today.isocalendar()
    week_data["week_label"] = f"{today.year}-W{iso.week:02d}"

    return week_data


def _build_system_prompt() -> str:
    methodology = load_methodology()
    return f"""你是 KAKAOPC 情报科的周报主编。你的任务是基于本周 7 天的信号数据，生成一份独立开发者情报周报。

## 方法论

{methodology}

## 周报写作规范

1. **本周一句话**: 用一句话概括这周最重要的发现
2. **Top 5 信号（去重）**: 本周最高质量的信号，每条的商业含义
3. **信号趋势**: 什么在上升、什么在降温、什么新出现
4. **验证结果**: 本周到期的机会验证结果（通过/失败/调整），诚实地写
5. **经验积累**: 本周从失败中学到了什么
6. **下周关注**: 基于本周格局，下周最值得关注的方向
7. **数据附录**: 本周每日信号量、最高分、Action 触发数

格式: Markdown，不要用代码块包裹。篇幅: 1500-2500 字。语言: 中文。"""


def _build_user_prompt(data: dict, date_str: str) -> str:
    lines = [
        f"## 周报周期: {data['week_label']}（截止 {date_str}）",
        "",
        "## 本周每日概况",
    ]

    for day in data["days"]:
        d = day["date"]
        lines.append(
            f"- {d}: {day['signal_count']} 信号 | 最高 {day['top_score']} 分 | "
            f"Action {day.get('action_qualified', 0)} 个 | "
            f"{'有日报' if day['has_report'] else '无日报'} | "
            f"{'有文章' if day['has_article'] else '无文章'}"
        )

    lines.extend(["", "## 本周 Top 信号（去重，Score ≥ 15）"])
    if data["top_signals"]:
        for s in data["top_signals"][:10]:
            lines.append(
                f"- [{s.get('score', 0)}分 | {s.get('_day', '?')} | {s.get('source', '?')}] "
                f"{s.get('title', '')[:100]}"
            )
    else:
        lines.append("*本周无触发 Action 阈值的高分信号*")

    lines.extend(["", "## 机会验证状态"])
    if data["verified_opportunities"]:
        for op in data["verified_opportunities"]:
            status = op.get("verification_result", "pending")
            emoji = {"passed": "✅", "failed": "❌", "adjust": "⚠️", "pending": "⏳"}.get(status, "❓")
            lines.append(
                f"- {emoji} [{op.get('id', '?')}] {op.get('opportunity', '')[:60]} "
                f"({op.get('score', 0)}分 | {op.get('day7_uv', 0)} UV | {op.get('day7_signups', 0)} 注册 | "
                f"判决: {op.get('day7_decision', 'pending')})"
            )
    else:
        lines.append("*本周无验证到期或更新的机会*")

    lines.extend(["", "## 本周经验教训"])
    if data["new_lessons"]:
        for ln in data["new_lessons"]:
            lines.append(
                f"- [{ln.get('id', '?')}] {ln.get('opportunity', '')[:60]}\n"
                f"  失败类型: {ln.get('failure_type', '?')} | "
                f"原因: {ln.get('cause', '?')} | "
                f"教训: {ln.get('lesson', '?')}"
            )
    else:
        lines.append("*本周无新增经验*")

    lines.extend([
        "",
        "---",
        "",
        "请基于以上数据生成本周情报周报。",
        "重点分析: 本周信号格局的整体变化、最有价值的单一发现、验证管线的最新结果。",
    ])

    return "\n".join(lines)


def generate_weekly(data: dict, date_str: str) -> str:
    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(data, date_str)

    print(f"[周报] 上下文: {len(system_prompt)} + {len(user_prompt)} = {len(system_prompt) + len(user_prompt)} 字符")

    report = chat(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.5,
        max_tokens=4096,
    )

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
    print(f"[周报] 周报生成 — {date}")
    print(f"{'='*50}")

    data = collect_weekly_data(date)
    print(f"[周报] 周标签: {data['week_label']}")
    print(f"[周报] 有效天数: {sum(1 for d in data['days'] if d['signal_count'] > 0)}/7")
    print(f"[周报] Top 信号: {len(data['top_signals'])} 个（去重）")
    print(f"[周报] 验证机会: {len(data['verified_opportunities'])} 个")
    print(f"[周报] 新增经验: {len(data['new_lessons'])} 条")

    if sum(1 for d in data["days"] if d["signal_count"] > 0) == 0:
        print("[周报] 本周无数据，跳过生成")
        return ""

    report = generate_weekly(data, date)

    WEEKLY_DIR.mkdir(parents=True, exist_ok=True)
    output_path = WEEKLY_DIR / f"{data['week_label']}.md"
    output_path.write_text(report, encoding="utf-8")
    print(f"[周报] 周报已保存 → {output_path}")
    print(f"[周报] 字数: {len(report)} 字符")

    return report


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    result = run(today)
    if result:
        try:
            print("\n" + result[:500] + "...")
        except UnicodeEncodeError:
            print(f"\n[Weekly report: {len(result)} chars, see weekly/]")
