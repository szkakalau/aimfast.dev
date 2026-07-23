"""
周报生成器
输入: daily/ 最近 7 天数据 + tracking/ 历史机会
输出: weekly/YYYY-WW.md + Buttondown 草稿
依赖: DeepSeek API + Buttondown API
触发: 每周日 20:00
"""
import json
import os
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

from scripts.llm_client import chat

ROOT = Path(__file__).resolve().parent.parent
DAILY_DIR = ROOT / "daily"
TRACKING_DIR = ROOT / "tracking"
WEEKLY_DIR = ROOT / "weekly"
METHODOLOGY_PATH = ROOT / "methodology.md"

TZ_SHANGHAI = timezone(timedelta(hours=8))

BUTTONDOWN_API_URL = "https://api.buttondown.com/v1/emails"
BUTTONDOWN_TIMEOUT = 30  # seconds


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
    return f"""你是 AimFast.Dev 的创始人，正在写一封给独立开发者同行的私人周信。

你不是在写报告。你是一个每天盯着 30+ 个信源、自己也在做产品验证的人。你的读者和你一样——他们在用业余时间做副业、在犹豫要不要 all in 某个方向、在被各种"风口"信息轰炸。

## 你的写作风格

- 用"我"的视角，不是"我们"或"AimFast.Dev"。这是你个人的观察和反思。
- 每一期只讲一件事。不是"本周 Top 5"，而是"这周只有一个东西让我真正停下来想了想"。
- 可以展示犹豫、困惑、推翻自己的过程。读者需要的不是权威判断，是真实思考过程。
- 数据是背景，不是主角。数字只是帮你说明"我为什么注意到这个"，不是结论本身。
- 避免任何格式化结构——不要用"本周一句话""信号趋势""数据附录"这些标签。让文字自然流动。

## 方法论（你思考的底层框架）

{methodology}

## 你每期思考的线索（不是结构模板，是你大脑里的 checklist）

- **开场钩子**: 这周发生了什么让我意外的事？一个具体数字、一次失败、一个反直觉的发现。先讲故事，不要先讲结论。
- **为什么这件事重要**: 它打破了我之前的什么假设？它揭示了什么我忽略的信号？
- **深入一个信号**: 不要扫射 5 个方向。挑一个，把它讲透——这个信号从哪里来？谁在讨论？如果做产品，第一个付钱的人长什么样？
- **我做了什么（或打算做什么）**: 具体行动——做了 Landing Page？手动 DM 了 50 个人？放弃了某个方向？诚实地写，包括犹豫和失败。
- **对你有什么用**: 从这件事中提炼 2-3 个可迁移的经验。不是"建议"，而是"如果你也在做类似的事，也许可以参考这个思路"。
- **收尾**: 简短的一句话，呼应开头或留下一个问题。让读者觉得这是一个真实的人在和他们聊天，不是在推送内容。

## 绝对不要做的事

- 不要写"本周信号概览""本周共扫描 X 条信号"这种开场——这是机器人写的
- 不要给每个信号打分并列出来——那是仪表盘，不是周信
- 不要用"我们建议""值得关注""具有潜力"——这些词汇没有信息量
- 不要凑字数。如果只有一件事值得说，就说那一件事。800 字比 2000 字废话好。
- 不要假装确定。如果你不确定某个方向，就说你不确定。

## 格式

纯粹的 Markdown 正文，不要代码块包裹。用 `---` 做自然分段。篇幅不限——说出该说的就停。

信末附上一句简短的个人化署名和 AimFast.Dev 链接（参考你过去的写法）。"""


def _build_user_prompt(data: dict, date_str: str) -> str:
    lines = [
        f"这周是 {data['week_label']}（截止 {date_str}），你的 AI 扫描了本周 7 天的信号。以下是原始数据，供你写周信时参考：",
        "",
        "## 本周每天发生了什么",
    ]

    for day in data["days"]:
        d = day["date"]
        lines.append(
            f"- {d}: {day['signal_count']} 条信号，最高 {day['top_score']} 分，"
            f"触发 Action 的有 {day.get('action_qualified', 0)} 个"
        )

    lines.extend(["", "## 本周值得注意的信号（Score ≥ 15）"])
    if data["top_signals"]:
        for i, s in enumerate(data["top_signals"][:10]):
            lines.append(
                f"{i+1}. [{s.get('score', 0)}分 | {s.get('_day', '?')} | "
                f"来源: {s.get('source', '?')}] {s.get('title', '')[:120]}"
            )
    else:
        lines.append("*这周没有触发阈值的高分信号——这本身就是一个值得写的信号*")

    lines.extend(["", "## 验证管线状态"])
    if data["verified_opportunities"]:
        for op in data["verified_opportunities"]:
            status = op.get("verification_result", "pending")
            emoji = {"passed": "✅", "failed": "❌", "adjust": "⚠️", "pending": "⏳"}.get(status, "❓")
            lines.append(
                f"- {emoji} {op.get('opportunity', '')[:80]}\n"
                f"  {op.get('score', 0)}分 → {op.get('day7_uv', 0)} UV, {op.get('day7_signups', 0)} 注册 → "
                f"判决: {op.get('day7_decision', 'pending')}"
            )
    else:
        lines.append("*本周无验证到期——如果你有在跑验证的实验，这是正常节奏*")

    lines.extend(["", "## 从失败中学到的"])
    if data["new_lessons"]:
        for ln in data["new_lessons"]:
            lines.append(
                f"- {ln.get('opportunity', '')[:80]}\n"
                f"  失败原因: {ln.get('cause', '?')}\n"
                f"  教训: {ln.get('lesson', '?')}"
            )
    else:
        lines.append("*本周无新增经验——要么一切顺利，要么还没开始复盘*")

    lines.extend([
        "",
        "---",
        "",
        "上面是数据。现在写你的周信——不要总结数据，用它来讲一个故事。",
        "挑一个让你真正停下思考的信号或失败，把它讲透。如果这周很平静（没有高分信号、没有验证结果），那就诚实地写'这周很平静'，然后反思平静本身意味着什么。",
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


def push_to_buttondown(report: str, week_label: str) -> bool:
    """将周报推送到 Buttondown 草稿箱。订阅者（含 liuguocong@gmail.com）发布后自动收到。"""
    api_key = os.environ.get("BUTTONDOWN_API_KEY", "")
    if not api_key:
        print("[Buttondown] WARNING — BUTTONDOWN_API_KEY 未设置，跳过推送（周报仅保存本地）")
        return False

    lines = report.split("\n")

    # Subject: 尝试从第一行提取 H1 标题，fallback 到 week_label
    subject = f"AimFast Weekly {week_label}"
    if lines:
        h1_match = re.match(r"^#\s+(.+)", lines[0])
        if h1_match:
            subject = h1_match.group(1).strip()
        elif lines[0].strip():
            subject = lines[0].strip()

    # Body = 第一个 --- 之后的所有内容。如果找不到 ---，取全文（除标题）
    separator_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            separator_idx = i
            break

    if separator_idx is not None:
        body = "\n".join(lines[separator_idx + 1:]).strip()
    else:
        # Fallback: 去掉第一行标题，取剩余全文
        body = "\n".join(lines[1:]).strip()
        print("[Buttondown] 警告: 未找到 '---' 分隔符，使用全文作为 body")

    payload = json.dumps({
        "subject": subject,
        "body": body,
        "status": "draft",
    }).encode("utf-8")

    # Buttondown 对 email body 大小有限制，超长时发出警告
    body_kb = len(body.encode("utf-8")) / 1024
    if body_kb > 500:
        print(f"[Buttondown] 警告: body 大小 {body_kb:.0f} KB，可能超出 API 限制")

    req = urllib.request.Request(
        BUTTONDOWN_API_URL,
        data=payload,
        headers={
            "Authorization": f"Token {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=BUTTONDOWN_TIMEOUT) as resp:
            result = json.loads(resp.read())
            draft_id = result.get("id", "?")
            print(f"[Buttondown] 草稿已创建 → {draft_id}")
            print(f"[Buttondown] 打开 Buttondown → Publish → Finalize 即可发送给所有订阅者")
            return True
    except urllib.error.HTTPError as e:
        print(f"[Buttondown] 创建草稿失败 HTTP {e.code}")
        return False
    except urllib.error.URLError as e:
        print(f"[Buttondown] 网络错误: {e.reason}")
        return False


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

    # 推送到 Buttondown → 所有订阅者（含 liuguocong@gmail.com）发布后收到
    pushed = push_to_buttondown(report, data["week_label"])
    if not pushed:
        print("[周报] ⚠️ Buttondown 推送失败，周报仅保存到本地文件")

    return report


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    result = run(today)
    if result:
        try:
            print("\n" + result[:500] + "...")
        except UnicodeEncodeError:
            print(f"\n[Weekly report: {len(result)} chars, see weekly/]")
