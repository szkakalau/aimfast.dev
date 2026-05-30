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


def _load_inputs(date_str: str) -> tuple[str, list[dict], str, str]:
    """加载日报 + 信号 + 追踪数据。
    返回 (report_md, signals, lp_url, lp_opportunity)
    """
    report_path = DAILY_DIR / date_str / "report.md"
    signals_path = DAILY_DIR / date_str / "signals.json"

    report_md = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
    all_signals = []
    if signals_path.exists():
        data = json.loads(signals_path.read_text(encoding="utf-8"))
        all_signals = data.get("signals", [])

    # 检查是否有可关联的 landing page
    # 优先级: 今天生成的 LP > 最近的 live LP
    tracking_path = ROOT / "tracking" / "opportunities.json"
    lp_url = ""
    lp_opportunity = ""
    lp_signal = None
    if tracking_path.exists():
        tracking = json.loads(tracking_path.read_text(encoding="utf-8"))
        live_opps = [o for o in tracking.get("opportunities", []) if o.get("lp_status") == "live"]
        if live_opps:
            # 优先匹配今天的 LP
            today_opp = next((o for o in live_opps if o.get("date") == date_str), None)
            matched = today_opp if today_opp else live_opps[-1]  # 回退到最新的
            lp_url = matched.get("landing_page_url", "")
            lp_opportunity = matched.get("opportunity", "")
            if today_opp:
                print(f"[即刻帖子] LP 匹配: 今日 LP ({lp_opportunity}) → {lp_url}")
            else:
                print(f"[即刻帖子] LP 匹配: 回退到最近 LP ({lp_opportunity}, {matched.get('date')}) → {lp_url}")

            # 在所有信号中搜索 LP 关联的信号（按 opportunity 名称匹配）
            if lp_opportunity and all_signals:
                opp_lower = lp_opportunity.lower()
                for s in all_signals:
                    title = s.get("title", "").lower()
                    if opp_lower and any(word in title for word in opp_lower.split() if len(word) > 2):
                        lp_signal = s
                        break

    # 构建 top 10 信号列表；如有 LP 关联信号且不在 top 5，注入到 top 3
    top_signals = all_signals[:10]
    if lp_signal and all(s.get("id") != lp_signal.get("id") for s in top_signals[:5]):
        top_signals = [s for s in top_signals if s.get("id") != lp_signal["id"]]
        top_signals.insert(2, lp_signal)
        print(f"[即刻帖子] LP 关联信号 ({lp_signal.get('title')}, {lp_signal.get('score')}分) 不在 top 5，已提升至 top 3")

    return report_md, top_signals, lp_url, lp_opportunity


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


def _build_user_prompt(report_md: str, signals: list[dict], lp_url: str, lp_opportunity: str, date_str: str) -> str:
    top_signal = signals[0] if signals else None
    top3 = signals[:3]

    top3_lines = []
    for i, s in enumerate(top3, 1):
        bd = s.get("score_breakdown", {})
        tags = []
        # 标记 LP 关联信号
        if lp_url and lp_opportunity:
            s_title = s.get("title", "").lower()
            opp_lower = lp_opportunity.lower()
            if any(word in s_title for word in opp_lower.split() if len(word) > 2):
                tags.append("LP 关联 — 这是帖子的必写主题")
        tag_str = f" 【{' | '.join(tags)}】" if tags else ""
        top3_lines.append(
            f"### 信号 {i}: [{s.get('score', 0)}分] {s.get('title', '')}{tag_str}\n"
            f"- 来源: {s.get('source', '')} | 跨平台: {s.get('cross_platform_count', 0)} 个\n"
            f"- 互动量: {s.get('discussion_count', 0)} 讨论\n"
            f"- 摘要: {s.get('summary', '')}\n"
            f"- 打分明细: {json.dumps(bd, ensure_ascii=False)}\n"
        )

    if lp_url and lp_opportunity:
        lp_note = f"""可关联的 Landing Page（已上线，必须作为帖子主题）:
- URL: {lp_url}
- 对应机会: {lp_opportunity}
- 硬性要求: 这篇帖子的主题必须是「{lp_opportunity}」。用 E-P-A 框架分析这个具体机会，而不是写其他信号。Top 3 中已有此信号（已标注"LP 关联"），聚焦它。"""
    elif lp_url:
        lp_note = f"\n可关联的 Landing Page: {lp_url}"
    else:
        lp_note = "\n今日无活跃 Landing Page。"

    return f"""## 日期: {date_str}

## 日报原文

{report_md[:3000] if report_md else '今日无日报'}

## Top 3 信号

{chr(10).join(top3_lines)}

{lp_note}

---
请基于以上数据生成即刻帖子。要求：
1. 如果提供了 Landing Page，帖子主题必须是对应机会，不能写其他话题。聚焦标注了"LP 关联"的信号
2. 严格 E-P-A 三段式: 证据、白话、行动。行动建议必须引导读者点击 Landing Page 链接
3. 500-800 字
4. 末尾单独一行: "Landing Page: <完整URL>"
5. 加 2-3 个标签
6. 纯文本，无 emoji，无异味"""


def generate(date_str: str) -> str:
    report_md, signals, lp_url, lp_opportunity = _load_inputs(date_str)

    if not report_md and not signals:
        return ""

    system = _build_system_prompt()
    user = _build_user_prompt(report_md, signals, lp_url, lp_opportunity, date_str)

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
