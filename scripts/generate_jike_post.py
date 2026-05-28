"""
即刻帖子生成器
输入: 今日日报 (daily/YYYY-MM-DD/report.md) + 信号数据 (signals.json)
输出: daily/YYYY-MM-DD/jike-post.md — 可直接复制粘贴到即刻的帖子
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

TZ_SHANGHAI = timezone(timedelta(hours=8))


def _load_inputs(date_str: str) -> tuple[str, list[dict], str]:
    """加载日报 + 信号 + 追踪数据。"""
    report_path = DAILY_DIR / date_str / "report.md"
    signals_path = DAILY_DIR / date_str / "signals.json"

    report_md = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
    signals = []
    if signals_path.exists():
        data = json.loads(signals_path.read_text(encoding="utf-8"))
        signals = data.get("signals", [])[:10]

    # 检查是否有可关联的 landing page
    tracking_path = ROOT / "tracking" / "opportunities.json"
    lp_url = ""
    if tracking_path.exists():
        tracking = json.loads(tracking_path.read_text(encoding="utf-8"))
        for opp in tracking.get("opportunities", []):
            if opp.get("lp_status") == "live":
                lp_url = opp.get("landing_page_url", "")
                break

    return report_md, signals, lp_url


def _build_system_prompt() -> str:
    return """你是 KAKAOPC 情报科的社交媒体编辑。你的任务是把日报里的最强信号改写成一篇即刻帖子。

## 核心规则

### E-P-A 框架（必须遵守）
每个帖子必须包含三段：
- **证据锚定**: 具体数字 + 来源。禁用"很多人""最近很火"。用"HN 417条评论 + Reddit 200赞"
- **白话翻译**: 这个信号意味着什么产品机会？谁会付钱？用"你"而不是"开发者们"
- **行动建议**: 今天 2 小时能做什么来验证？附 landing page 链接

### 格式约束
- 500-800 字（即刻最佳阅读长度）
- 用短句，一段不超过 3 行
- 像有经验的 builder 在和朋友聊天，不是分析师报告
- 开头第一句必须有钩子——一个反直觉的事实或一个具体的数字
- 结尾必须有 CTA：引导读者点击 landing page 链接或发表看法

### 语气
- 不装、不吹、不贩卖焦虑
- 承认不确定性——"我可能错了，但数据指向…"
- 如果信号未达 action 阈值（<15 分），诚实地说"今天没有高确定性的方向，但有一个值得关注的变化"
- 帖子末尾加 2-3 个相关标签（#独立开发者 #机会发现 等）

### 禁止
- emoji（即刻用户偏好纯文字）
- "广受好评""大家都在讨论""最近很火"——全部换成具体数字
- AI 写作味（"值得注意的是""综上所述""此外"）
- 超过 2 个话题标签"""


def _build_user_prompt(report_md: str, signals: list[dict], lp_url: str, date_str: str) -> str:
    top_signal = signals[0] if signals else None
    top3 = signals[:3]

    top3_lines = []
    for i, s in enumerate(top3, 1):
        bd = s.get("score_breakdown", {})
        top3_lines.append(
            f"### 信号 {i}: [{s.get('score', 0)}分] {s.get('title', '')}\n"
            f"- 来源: {s.get('source', '')} | 跨平台: {s.get('cross_platform_count', 0)} 个\n"
            f"- 互动量: {s.get('discussion_count', 0)} 讨论\n"
            f"- 摘要: {s.get('summary', '')}\n"
            f"- 打分明细: {json.dumps(bd, ensure_ascii=False)}\n"
        )

    lp_note = f"\n可关联的 Landing Page: {lp_url}" if lp_url else "\n今日无活跃 Landing Page。"

    return f"""## 日期: {date_str}

## 日报原文

{report_md[:3000] if report_md else '今日无日报'}

## Top 3 信号

{chr(10).join(top3_lines)}

{lp_note}

---
请基于以上数据生成即刻帖子。要求：
1. 聚焦 Top 1 信号（如果 ≥15 分 + 跨平台 ≥3），否则聚焦最有意思的变化
2. 严格 E-P-A 三段式
3. 500-800 字
4. 末尾附上 landing page 链接（如果有）
5. 加 2-3 个标签
6. 纯文本，无 emoji，无异味"""


def generate(date_str: str) -> str:
    report_md, signals, lp_url = _load_inputs(date_str)

    if not report_md and not signals:
        return ""

    system = _build_system_prompt()
    user = _build_user_prompt(report_md, signals, lp_url, date_str)

    print(f"[即刻帖子] 上下文: {len(system)} + {len(user)} = {len(system) + len(user)} 字符")
    print(f"[即刻帖子] 信号数: {len(signals)} | LP: {lp_url or '无'}")

    post = chat(
        system_prompt=system,
        user_prompt=user,
        temperature=0.8,
        max_tokens=2048,
    )

    return post


def run(date_str: str | None = None) -> str:
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    print(f"\n{'='*50}")
    print(f"[即刻帖子] 生成 — {date}")
    print(f"{'='*50}")

    post = generate(date)
    if not post:
        print("[即刻帖子] 无数据，跳过")
        write_pipeline_status(date, "jike_post", "skipped",
            reason="no_data", message="No report or signals to generate post from.")
        return ""

    output_dir = DAILY_DIR / date
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "jike-post.md"
    output_path.write_text(post, encoding="utf-8")
    print(f"[即刻帖子] 已保存 → {output_path}")
    print(f"[即刻帖子] 字数: {len(post)} 字符")

    write_pipeline_status(date, "jike_post", "generated",
        message=f"Jike post saved ({len(post):,} chars)")

    return post


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    result = run(today)
    if result:
        print("\n" + result)
