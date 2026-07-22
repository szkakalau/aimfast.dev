"""
竞品情报生成器
读取全量信号 + 用户追踪目标，使用 LLM 生成每个目标的每日情报。

流程：
  1. 加载全量信号 (daily/{date}/signals.json)
  2. 加载追踪目标 (tracking/tracking_targets.json)
  3. 对每个目标，在信号中做关键词+语义匹配
  4. 对匹配到的提及用 LLM 做三层处理：
     a. 去噪（过滤纯转帖、无实质内容）
     b. 翻译 + 提炼（原文 → 中文翻译 → 对竞品影响 → 对追踪者的价值）
     c. 聚合趋势（本周提及量 vs 上周、情感倾向）
  5. 输出 competitor_intel.json 到 daily/{date}/

用法：
  python scripts/generate_competitor_intel.py [date]
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 确保可以导入项目根目录的模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.llm_client import chat as llm_chat
from scripts.defaults import sanitize_for_llm

ROOT = Path(__file__).resolve().parent.parent
DAILY_DIR = ROOT / "daily"
TRACKING_DIR = ROOT / "tracking"
TZ_SHANGHAI = timezone(timedelta(hours=8))

# ── 每个目标最多处理几条提及 ──
MAX_MENTIONS_PER_TARGET = 10
# ── 每次 LLM 调用最多输出几个 highlights ──
MAX_HIGHLIGHTS_PER_TARGET = 3


def _load_signals(date_str: str) -> list[dict]:
    """加载指定日期的全量信号。"""
    path = DAILY_DIR / date_str / "signals.json"
    if not path.exists():
        print(f"[CompetitorIntel] signals.json 不存在: {path}")
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("signals", [])


def _load_targets() -> list[dict]:
    """加载活跃追踪目标。"""
    path = TRACKING_DIR / "tracking_targets.json"
    if not path.exists():
        print("[CompetitorIntel] 无追踪目标文件，跳过")
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("targets", [])
    except Exception as e:
        print(f"[CompetitorIntel] 读取追踪目标失败: {e}")
        return []


def _match_target_to_signals(target: dict, signals: list[dict]) -> list[dict]:
    """关键词 + 别名匹配：找出与追踪目标相关的所有信号。"""
    name = target.get("name", "").lower()
    if not name:
        return []

    # 解析别名和关键词
    aliases = []
    keywords = []
    try:
        aliases = json.loads(target.get("aliases", "[]"))
    except (json.JSONDecodeError, TypeError):
        pass
    try:
        keywords = json.loads(target.get("keywords", "[]"))
    except (json.JSONDecodeError, TypeError):
        pass

    search_terms = [name] + [a.lower() for a in aliases] + [k.lower() for k in keywords]

    matched = []
    for sig in signals:
        title = (sig.get("title", "") or "").lower()
        summary = (sig.get("summary", "") or "").lower()
        text = f"{title} {summary}"

        # 检查是否有任何搜索词匹配
        for term in search_terms:
            if not term:
                continue
            if term in text:
                matched.append(sig)
                break

    return matched


def _build_intel_prompt(name: str, target_type: str, notes: str, mentions: list[dict]) -> tuple[str, str]:
    """构建竞品情报的 system + user prompt。

    三层处理：
      1. 去噪（过滤无实质内容的提及）
      2. 翻译 + 提炼（原文 → 中文翻译 → 竞品影响 → 追踪者价值）
      3. 聚合趋势（提及量、情感、新变化）
    """
    if not mentions:
        return "", ""

    # ── 构建提及文本 ──
    mentions_text = ""
    for i, m in enumerate(mentions[:MAX_MENTIONS_PER_TARGET]):
        title = sanitize_for_llm(m.get("title", ""))
        summary = sanitize_for_llm(m.get("summary", ""))
        source = m.get("source", "unknown")
        url = m.get("url", "")
        score = m.get("score", 0)
        source_key = m.get("source_key", source)
        mentions_text += (
            f"### 提及 #{i+1}\n"
            f"来源: {source} ({source_key}) | 评分: {score}\n"
            f"标题: {title}\n"
            f"摘要: {summary}\n"
            f"链接: {url}\n\n"
        )

    type_labels = {
        "competitor": "竞品公司/产品",
        "person": "行业人物",
        "topic": "话题/赛道",
        "tech": "技术栈",
        "platform": "平台/渠道",
    }
    type_label = type_labels.get(target_type, "追踪目标")

    system_prompt = """你是一个竞品情报分析师。你的任务是对用户的追踪目标生成每日情报简报。

对于每条提及，你需要做三层处理：

1. **去噪判断**：
   - 纯转帖/无评论/无上下文 → 标记为噪音，不计入 highlights
   - 仅提及名称但无实质内容 → 同上
   - 有实质性讨论、新观点、或策略价值 → 保留

2. **翻译 + 提炼**（仅对有价值的内容）：
   对于每条保留的提及，输出：
   - original_text: 原文关键句（1-2 句英文）
   - translation: 一句话中文翻译
   - competitor_impact: 这对追踪目标本身意味着什么（方向变化？市场反应？新竞争者？）
   - your_action: 这对追踪者意味着什么可行动的机会或风险

3. **聚合趋势**：
   - weekly_mentions: 本次匹配到的提及总数（包含噪音）
   - noise_count: 被判定为噪音的数量
   - trend: "up"（关注度上升）, "down"（关注度下降）, "stable"（持平）
   - sentiment: "positive"（积极）, "negative"（消极）, "neutral"（中性）
   - notable_change: 是否有值得注意的变化（如讨论角度变化、新进入者），一句话描述

输出必须是严格 JSON 格式，不要包含 markdown 代码块标记。"""

    user_prompt = f"""追踪目标: {name}
追踪类型: {type_label}
备注: {notes or "无"}

今日匹配到的提及（共 {len(mentions)} 条）：

{mentions_text}

请分析以上提及，输出 JSON：

{{
  "target_name": "{name}",
  "stats": {{
    "weekly_mentions": <匹配到的提及总数>,
    "noise_count": <噪音数量>,
    "trend": "<up/down/stable>",
    "sentiment": "<positive/negative/neutral>",
    "notable_change": "<一句话描述值得注意的变化，如无则填 null>"
  }},
  "highlights": [
    {{
      "source": "<来源名>",
      "source_url": "<链接>",
      "original_text": "<原文关键句>",
      "translation": "<中文翻译>",
      "competitor_impact": "<对追踪目标的影响>",
      "your_action": "<追踪者可采取的行动>",
      "relevance": "<high/medium/low>"
    }}
  ],
  "suggested_actions": [
    {{
      "action": "<deep_dive/build/watch/ignore>",
      "label": "<行动标签（中文，10字以内）>"
    }}
  ]
}}

规则：
- highlights 最多 {MAX_HIGHLIGHTS_PER_TARGET} 条，只保留最有价值的
- suggested_actions 提供 2-3 个可行动的建议
- 如果所有提及都是噪音（无保留价值的），highlights 为空数组
- 所有中文文本请使用简体中文"""

    return system_prompt, user_prompt


def _parse_llm_response(response: str) -> dict | None:
    """解析 LLM 返回的 JSON。容错处理常见的格式问题。"""
    if not response:
        return None
    # 去掉可能的 markdown 代码块标记
    text = response.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # 去掉第一行 ```json 或 ```
        text = "\n".join(lines[1:]) if lines[0].startswith("```") else text
        if text.endswith("```"):
            text = text[:-3].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 尝试提取第一个 JSON 对象
        import re
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    print(f"[CompetitorIntel] LLM 响应解析失败，原始响应前 200 字符: {text[:200]}")
    return None


def run(date_str: str | None = None) -> dict:
    """生成竞品情报。

    Returns:
        {"targets": [...], "generated_at": "ISO time"}
        失败时返回 {"targets": [], "error": "..."}
    """
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    print(f"\n[CompetitorIntel] 竞品情报生成 — {date}")

    # 1. 加载数据
    signals = _load_signals(date)
    if not signals:
        print("[CompetitorIntel] 无信号数据")
        return {"targets": [], "error": "no signals"}

    targets = _load_targets()
    if not targets:
        print("[CompetitorIntel] 无追踪目标")
        # 写入空文件以保持 Pipeline 一致性
        intel = {"targets": [], "generated_at": datetime.now(TZ_SHANGHAI).isoformat()}
        output_dir = DAILY_DIR / date
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "competitor_intel.json"
        output_path.write_text(json.dumps(intel, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[CompetitorIntel] 已保存 (空) -> {output_path}")
        return intel

    print(f"[CompetitorIntel] {len(signals)} 条信号 | {len(targets)} 个追踪目标")

    # 2. 对每个目标做匹配 → LLM 处理
    results = []
    for target in targets:
        name = target.get("name", "unknown")
        target_type = target.get("type", "topic")
        notes = target.get("notes", "")

        # 匹配信号
        mentions = _match_target_to_signals(target, signals)
        print(f"  🎯 {name}: {len(mentions)} 条相关提及")

        if not mentions:
            # 无匹配 → 空结果
            results.append({
                "id": target.get("id", ""),
                "name": name,
                "type": target_type,
                "stats": {
                    "weekly_mentions": 0,
                    "noise_count": 0,
                    "trend": "stable",
                    "sentiment": "neutral",
                    "notable_change": None,
                },
                "highlights": [],
                "suggested_actions": [
                    {"action": "watch", "label": "继续观察"}
                ],
            })
            continue

        # 构建 prompt + 调用 LLM
        system_prompt, user_prompt = _build_intel_prompt(name, target_type, notes, mentions)
        response = llm_chat(system_prompt, user_prompt, temperature=0.7, max_tokens=2048)
        parsed = _parse_llm_response(response)

        if parsed:
            parsed["id"] = target.get("id", "")
            parsed["type"] = target_type
            parsed.setdefault("stats", {
                "weekly_mentions": len(mentions),
                "noise_count": 0,
                "trend": "stable",
                "sentiment": "neutral",
                "notable_change": None,
            })
            parsed.setdefault("highlights", [])
            parsed.setdefault("suggested_actions", [])
            results.append(parsed)
        else:
            # LLM 失败 → 基础统计
            results.append({
                "id": target.get("id", ""),
                "name": name,
                "type": target_type,
                "stats": {
                    "weekly_mentions": len(mentions),
                    "noise_count": 0,
                    "trend": "stable",
                    "sentiment": "neutral",
                    "notable_change": None,
                },
                "highlights": [],
                "suggested_actions": [
                    {"action": "watch", "label": "继续观察"}
                ],
            })

    intel = {
        "targets": results,
        "generated_at": datetime.now(TZ_SHANGHAI).isoformat(),
    }

    # 3. 保存输出
    output_dir = DAILY_DIR / date
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "competitor_intel.json"
    output_path.write_text(json.dumps(intel, ensure_ascii=False, indent=2), encoding="utf-8")

    highlight_count = sum(len(t.get("highlights", [])) for t in results)
    print(f"[CompetitorIntel] 已保存 → {output_path}")
    print(f"[CompetitorIntel] {len(results)} 个目标 | {highlight_count} 条 highlight")
    return intel


if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    result = run(date_arg)
    if result.get("error"):
        print(f"[CompetitorIntel] 完成 (空结果: {result['error']})")
    else:
        print(f"[CompetitorIntel] 完成 — {len(result.get('targets', []))} 个目标")
