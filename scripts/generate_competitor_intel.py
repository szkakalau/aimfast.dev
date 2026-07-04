"""
竞品情报生成器 (Phase 1 — 双引擎架构：监控引擎)
输入: ./daily/YYYY-MM-DD/competitor_matches.json + 历史 ~7 天数据
输出: ./daily/YYYY-MM-DD/competitor_intel.json
依赖: DeepSeek API (llm_client)

处理流程（对每个追踪目标）:
  1. 读取当日匹配 + 前 7 天的提及量（用于趋势对比）
  2. LLM 处理: 去噪 → 分类 → 翻译 → 竞品影响 → 对你有什么用
  3. 输出结构化 JSON

最大跟踪目标数: 10（超过时只处理前 10 个）
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.llm_client import chat

ROOT = Path(__file__).resolve().parent.parent
DAILY_DIR = ROOT / "daily"

TZ_SHANGHAI = timezone(timedelta(hours=8))

# 引入竞品情报的 token 预算（一次大约 2-3K tokens per target）
MAX_TARGETS = 10
MAX_MATCHES_PER_TARGET = 30  # 只发给 LLM 前 30 个匹配，太多浪费 token


def _load_weekly_stats(target: dict, current_date: str) -> dict:
    """加载最近 7 天的提及量统计，用于趋势对比。"""
    tid = target.get("target_id", "")
    weekly_counts = []
    for i in range(7):
        d = (datetime.strptime(current_date, "%Y-%m-%d") - timedelta(days=i)).strftime("%Y-%m-%d")
        matches_path = DAILY_DIR / d / "competitor_matches.json"
        if matches_path.exists():
            try:
                data = json.loads(matches_path.read_text(encoding="utf-8"))
                for t in data.get("targets", []):
                    if t.get("target_id") == tid:
                        weekly_counts.append({"date": d, "count": t.get("match_count", 0)})
                        break
                else:
                    weekly_counts.append({"date": d, "count": 0})
            except Exception:
                weekly_counts.append({"date": d, "count": 0})
        else:
            weekly_counts.append({"date": d, "count": 0})

    this_week = sum(d["count"] for d in weekly_counts[:3]) if len(weekly_counts) >= 3 else weekly_counts[0]["count"] if weekly_counts else 0
    last_week = sum(d["count"] for d in weekly_counts[3:6]) if len(weekly_counts) >= 6 else 0
    trend = "up" if this_week > last_week * 1.2 else "down" if this_week < last_week * 0.8 else "stable"

    return {
        "weekly_mentions": this_week,
        "previous_week_mentions": last_week,
        "trend": trend,
        "daily_breakdown": weekly_counts,
    }


def _build_system_prompt() -> str:
    return """你是一个竞品情报分析师。你的任务是把原始信号转化为可执行的情报。

## 你的处理流程

1. **去噪**：判断每条提及是否有实质内容。
   - 仅提及名称、纯转帖、无上下文 → 标记为 noise
   - 有讨论、有观点、有数据 → 保留

2. **分类**：对有价值的提及：
   - 翻译：把原文核心意思翻译成中文（1-2 句话）
   - 竞品影响：这对竞品意味着什么？（方向变化？用户反馈？增长信号？）
   - 对追踪者的价值：这个情报对追踪者有什么可行动的？（工具机会？切入点？风险？）

3. **聚合**：
   - 本周提及趋势（上升/下降/持平）
   - 情感倾向（正面/负面/中性）
   - 核心叙事变化（如有）

## 输出格式

你必须严格返回以下 JSON 格式（不要额外文字，只返回 JSON）：

```json
{
  "target_name": "目标名称",
  "stats": {
    "weekly_mentions": 12,
    "trend": "up",
    "sentiment": "neutral",
    "noise_count": 5,
    "signal_count": 7,
    "core_narrative": "一句话描述本周讨论的核心主题变化"
  },
  "highlights": [
    {
      "source": "HN",
      "source_url": "https://...",
      "original_text": "原文关键句（英文）",
      "translation": "中文翻译",
      "competitor_impact": "对竞品的影响",
      "your_action": "对追踪者的可行动建议",
      "relevance": "high"
    }
  ],
  "suggested_actions": [
    {"action": "deep_dive", "label": "深入了解 XXX"},
    {"action": "build", "label": "考虑做 XXX 工具"},
    {"action": "ignore", "label": "忽略（现阶段不相关）"}
  ],
  "noise_summary": "已过滤 5 条无关提及（纯转帖/无实质内容）"
}
```

## ⚠️ 视角规则（极其重要）

**"你"始终是追踪者（使用 AimFast.Dev 的人），不是被追踪的目标！**

- `competitor_impact`：这个事件对**被追踪的目标**意味着什么？
- `your_action`：追踪者（你）可以据此**做什么**？（永远不要写目标应该做什么）

错误示例（视角混淆 — 严禁）：
  - ❌ `your_action`: "Cursor 应立即修复 iOS 隐私问题"
  - ❌ `your_action`: "Vercel 应该降价以保持竞争力"
  - ❌ `your_action`: "评估 Cursor 是否应内置此功能"

正确示例（追踪者视角）：
  - ✅ `your_action`: "Cursor 的隐私问题可能导致用户流失——如果你在做 AI 编程工具，这是一个差异化切入点"
  - ✅ `your_action`: "关注 Vercel 定价变化，如果你的产品依赖 Vercel，评估迁移成本"
  - ✅ `your_action`: "这些第三方工具在增强 Cursor 能力——考虑做一个 Cursor 互补插件来获取用户"

**对于 competitor / platform 类型的追踪目标**，追踪者在问的是："这个竞品的动态对我有什么影响？我能利用什么？我应该担心什么？" 不要替竞品做决策。

## 规则

- 每个目标最多输出 5 条 highlights（精选最有价值的）
- relevance 标记: high（直接竞品/关键变化）/ medium（间接相关）/ low（背景信息）
- suggested_actions 必须有 2-4 个选项，从追踪者角度出发
- 如果所有提及都是噪音，highlights 为空数组，noise_summary 说明原因
- 只返回 JSON，不要有任何 markdown 包裹或额外文字"""


def _build_user_prompt(target: dict, stats: dict) -> str:
    """构建单目标的用户 prompt。"""
    tname = target.get("target_name", "")
    ttype = target.get("target_type", "competitor")
    aliases = target.get("aliases", [])
    keywords = target.get("keywords", [])
    matches = target.get("matches", [])[:MAX_MATCHES_PER_TARGET]
    notes = target.get("_notes", "")

    # 构建匹配列表（紧凑格式）
    matches_text = ""
    for i, m in enumerate(matches):
        matches_text += (
            f"[{i+1}] [{m['source']}] {m['title']}\n"
            f"    匹配: {m['match_method']} (score={m['match_score']})\n"
            f"    摘要: {m['summary'][:300]}\n"
            f"    URL: {m['url']}\n\n"
        )

    return f"""## 追踪目标

- 名称: {tname}
- 类型: {ttype}
- 别名: {', '.join(aliases)}
- 关键词: {', '.join(keywords)}
{f"- 备注: {notes}" if notes else ""}

## 本周趋势

- 本周提及: {stats['weekly_mentions']} 次（上周: {stats['previous_week_mentions']} 次）
- 趋势方向: {stats['trend']}

## 今日匹配到的提及（共 {len(matches)} 条，展示前 {min(len(matches), MAX_MATCHES_PER_TARGET)} 条）

{matches_text if matches_text else '今日无匹配到的提及。'}

## 指令

对以上提及进行去噪、分类、翻译，输出结构化的竞品情报 JSON。
只保留有实质内容的提及，标记为 noise 的仅在 stats.noise_count 中体现。
"""


def _parse_llm_response(response: str, target_name: str, stats: dict) -> dict:
    """解析 LLM 返回的 JSON，失败时返回降级格式。"""
    try:
        # 尝试提取 JSON（去掉可能的 markdown 包裹）
        text = response.strip()
        if text.startswith("```"):
            # 去掉 ```json ... ``` 包裹
            lines = text.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            text = "\n".join(lines)
        result = json.loads(text)
        result["stats"] = {**stats, **result.get("stats", {})}
        return result
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[竞品情报] JSON 解析失败 ({target_name}): {e}")
        return _fallback_intel(target_name, stats)


def _fallback_intel(target_name: str, stats: dict) -> dict:
    """LLM 不可用时的降级输出。"""
    return {
        "target_name": target_name,
        "stats": {
            "weekly_mentions": stats.get("weekly_mentions", 0),
            "trend": stats.get("trend", "stable"),
            "sentiment": "unknown",
            "noise_count": 0,
            "signal_count": 0,
            "core_narrative": "LLM 不可用，使用降级模式"
        },
        "highlights": [],
        "suggested_actions": [
            {"action": "check_raw", "label": f"查看 {target_name} 原始提及"}
        ],
        "noise_summary": "LLM 不可用，未能进行分析。原始匹配数据保存在 competitor_matches.json",
        "_fallback": True
    }


def run(date_str: str | None = None) -> dict:
    """生成竞品情报。"""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    print(f"\n{'='*50}")
    print(f"[竞品情报] LLM 情报生成 — {date}")
    print(f"{'='*50}")

    # 加载匹配结果
    matches_path = DAILY_DIR / date / "competitor_matches.json"
    if not matches_path.exists():
        print(f"[竞品情报] {matches_path} 不存在，先运行 match_competitors.py")
        return {"date": date, "error": "competitor_matches.json not found"}

    matches_data = json.loads(matches_path.read_text(encoding="utf-8"))
    targets = matches_data.get("targets", [])

    if not targets:
        print("[竞品情报] 无追踪目标，跳过")
        return {"date": date, "targets": []}

    # 限制最大目标数
    if len(targets) > MAX_TARGETS:
        print(f"[竞品情报] 追踪目标 {len(targets)} 个 > {MAX_TARGETS} 上限，仅处理前 {MAX_TARGETS} 个")
        targets = targets[:MAX_TARGETS]

    results = []
    for target in targets:
        tname = target.get("target_name", "")
        match_count = target.get("match_count", 0)
        print(f"\n[竞品情报] 处理: {tname} ({match_count} 个匹配)")

        # 加载周趋势
        stats = _load_weekly_stats(target, date)

        if match_count == 0:
            # 无匹配 → 仍输出占位
            intel = {
                "target_name": tname,
                "stats": {
                    "weekly_mentions": stats["weekly_mentions"],
                    "trend": stats["trend"],
                    "sentiment": "neutral",
                    "noise_count": 0,
                    "signal_count": 0,
                    "core_narrative": "今日未匹配到相关提及"
                },
                "highlights": [],
                "suggested_actions": [],
                "noise_summary": "今日信号源中未找到与此目标的相关内容",
            }
            results.append(intel)
            continue

        # LLM 处理
        system_prompt = _build_system_prompt()
        user_prompt = _build_user_prompt(target, stats)

        # 控制 token 用量：匹配多时用较低的 max_tokens
        estimated_tokens = min(2048 + match_count * 200, 4096)
        try:
            response = chat(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=estimated_tokens,
            )

            intel = _parse_llm_response(response, tname, stats)
            intel["target_id"] = target.get("target_id", "")
            intel["target_type"] = target.get("target_type", "competitor")
            results.append(intel)
            print(f"[竞品情报]   {tname}: {len(intel.get('highlights', []))} highlights, "
                  f"noise={intel.get('stats', {}).get('noise_count', 0)}")
        except Exception as e:
            print(f"[竞品情报]   {tname}: LLM 调用失败 ({e}), 使用降级模式")
            intel = _fallback_intel(tname, stats)
            intel["target_id"] = target.get("target_id", "")
            intel["target_type"] = target.get("target_type", "competitor")
            results.append(intel)

    output = {
        "date": date,
        "generated_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "target_count": len(targets),
        "intel_count": len(results),
        "targets": results,
    }

    # 保存
    out_dir = DAILY_DIR / date
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "competitor_intel.json"
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[竞品情报] 已保存 → {out_path}")
    print(f"[竞品情报] {len(results)} 个目标处理完成")

    return output


if __name__ == "__main__":
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
    else:
        date_str = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    run(date_str)
