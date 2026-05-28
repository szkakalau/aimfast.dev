"""
信号处理引擎
负责: 加载 → 去重 → 聚类 → E-P-A 打分 → 衰减 → 排序
输入: ./raw/YYYY-MM-DD/*.json
输出: ./daily/YYYY-MM-DD/signals.json
"""
import json
import re
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"
DAILY_DIR = ROOT / "daily"
CONFIG_PATH = ROOT / "config.json"

TZ_SHANGHAI = timezone(timedelta(hours=8))

# 停用词（聚类时忽略）
STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "in", "on", "at", "to", "for", "of", "with", "by", "from",
    "and", "or", "but", "not", "this", "that", "it", "its",
    "i", "you", "he", "she", "we", "they", "my", "your",
    "has", "have", "had", "do", "does", "did", "will", "would",
    "can", "could", "should", "may", "might", "about", "just",
    "how", "what", "why", "when", "where", "who", "which",
    "v2ex", "reddit", "hacker", "news", "github", "trending",
    "new", "using", "use", "make", "made", "get", "got", "one",
    "like", "now", "also", "still", "need", "way", "really",
}


def load_config() -> dict:
    """加载配置文件。"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_raw_signals(date_str: str) -> list[dict]:
    """加载当日所有原始信号。"""
    raw_path = RAW_DIR / date_str
    if not raw_path.exists():
        print(f"[处理] {raw_path} 不存在，无原始数据")
        return []

    all_signals: list[dict] = []
    for f in sorted(raw_path.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            source_signals = data.get("signals", [])
            all_signals.extend(source_signals)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[处理] 读取 {f.name} 失败: {e}")

    print(f"[处理] 加载 {len(all_signals)} 条原始信号（来自 {raw_path}）")
    return all_signals


# ─── 去重 ───────────────────────────────────────────

def _title_similarity(a: str, b: str) -> float:
    """计算两个标题的相似度（0-1）。"""
    a_clean = re.sub(r"[^\w\s]", "", a.lower()).strip()
    b_clean = re.sub(r"[^\w\s]", "", b.lower()).strip()
    if not a_clean or not b_clean:
        return 0.0
    return SequenceMatcher(None, a_clean, b_clean).ratio()


def _extract_keywords(text: str) -> set[str]:
    """从文本中提取关键词。"""
    words = re.findall(r"[a-zA-Z一-鿿]+", text.lower())
    return {w for w in words if w not in STOP_WORDS and len(w) > 1}


def deduplicate(signals: list[dict]) -> list[dict]:
    """
    去重：
    1. URL 完全相同 → 合并
    2. 标题相似度 > 0.90 → 合并，保留互动量更高的
    3. 同一 URL 出现在多个源 → 合并为一条，标注跨平台验证
    """
    if not signals:
        return []

    config = load_config()
    threshold = config.get("dedup", {}).get("title_similarity", 0.90)

    unique: list[dict] = []
    url_map: dict[str, int] = {}  # url → index in unique

    for signal in signals:
        url = signal.get("url", "")
        title = signal.get("title", "")

        # 第 1 道: URL 精确匹配
        if url and url in url_map:
            idx = url_map[url]
            existing = unique[idx]
            # 合并 sources
            existing_sources = existing.get("_raw_sources", [existing.get("source", "")])
            existing_sources.append(signal.get("source", ""))
            existing["_raw_sources"] = existing_sources
            # 保留互动量更高的
            if signal["engagement"]["total"] > existing["engagement"]["total"]:
                unique[idx] = signal
                unique[idx]["_raw_sources"] = existing_sources
            continue

        # 第 2 道: 标题相似度
        is_dup = False
        for j, existing in enumerate(unique):
            sim = _title_similarity(title, existing.get("title", ""))
            if sim >= threshold:
                # 合并来源
                existing_sources = existing.get("_raw_sources", [existing.get("source", "")])
                existing_sources.append(signal.get("source", ""))
                existing["_raw_sources"] = existing_sources
                # 标记跨平台
                existing["discussion_count"] = max(
                    existing.get("discussion_count", 0),
                    signal.get("discussion_count", 0),
                )
                is_dup = True
                break

        if not is_dup:
            signal["_raw_sources"] = [signal.get("source", "")]
            unique.append(signal)
            if url:
                url_map[url] = len(unique) - 1

    dup_count = len(signals) - len(unique)
    print(f"[去重] {len(signals)} → {len(unique)}（合并 {dup_count} 条重复）")
    return unique


# ─── 聚类 ───────────────────────────────────────────

def cluster(signals: list[dict]) -> list[dict]:
    """
    将相关信号归为同一话题。
    基于关键词重叠率（Jaccard 相似度），将高度相关的信号合并为话题组。
    每个话题组选一条代表信号，附上所有子信号的引用。
    """
    if len(signals) <= 1:
        return signals

    kw_cache: dict[int, set[str]] = {}
    for i, s in enumerate(signals):
        title = s.get("title", "")
        summary = s.get("summary", "")
        kw_cache[i] = _extract_keywords(f"{title} {summary}")

    # 简单的连通分量聚类（Jaccard > 0.25）
    parent = list(range(len(signals)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    for i in range(len(signals)):
        for j in range(i + 1, len(signals)):
            kws_i = kw_cache[i]
            kws_j = kw_cache[j]
            if not kws_i or not kws_j:
                continue
            intersection = kws_i & kws_j
            union_size = len(kws_i | kws_j)
            jaccard = len(intersection) / union_size if union_size > 0 else 0

            # 同一源的信号即使关键词重叠也不聚类（避免自聚合）
            same_source = signals[i].get("source_key") == signals[j].get("source_key")
            threshold = 0.35 if same_source else 0.25

            if jaccard >= threshold:
                union(i, j)

    # 按 group 聚合
    groups: dict[int, list[int]] = {}
    for i in range(len(signals)):
        root = find(i)
        groups.setdefault(root, []).append(i)

    clustered: list[dict] = []
    multi_platform_count = 0

    for root, indices in groups.items():
        group_signals = [signals[i] for i in indices]

        # 选互动量最高的为代表
        best = max(group_signals, key=lambda s: s["engagement"]["total"])

        # 收集所有来源平台
        all_sources = []
        for s in group_signals:
            for src in s.get("_raw_sources", [s.get("source", "")]):
                if src not in all_sources:
                    all_sources.append(src)

        best["_raw_sources"] = all_sources

        # 如果组内有多个信号且跨多个源 → 标注跨平台验证
        if len(group_signals) >= 2 and len(set(s.get("source_key", "") for s in group_signals)) >= 2:
            multi_platform_count += 1
            best["_cluster_info"] = {
                "size": len(group_signals),
                "cross_platform": True,
                "related_ids": [s.get("id", "") for s in group_signals if s.get("id") != best.get("id")],
            }

        clustered.append(best)

    print(f"[聚类] {len(signals)} → {len(clustered)} 组（{multi_platform_count} 组跨平台验证）")
    return clustered


# ─── E-P-A 打分 ─────────────────────────────────────

def score_epa(signals: list[dict]) -> list[dict]:
    """
    E-P-A 打分。
    Score = cross_platform×3 + volume×2 + freshness×2 + actionability×2 + buyer_clarity×1

    cross_platform: 统计 _raw_sources 中不同平台
    volume: 讨论量 vs 阈值表
    freshness: 基于 collected_at 判断
    actionability: 基于关键词规则
    buyer_clarity: 基于关键词规则
    """
    config = load_config()
    weights = config["scoring"]["weights"]
    rubrics = config["scoring"]["rubrics"]
    today = datetime.now(TZ_SHANGHAI).date()

    for s in signals:
        # 1. cross_platform
        sources = s.get("_raw_sources", [s.get("source", "")])
        unique_sources = len(set(sources))
        if unique_sources >= 3:
            cp_score = rubrics["cross_platform"]["3_plus_platforms"]
        elif unique_sources >= 2:
            cp_score = rubrics["cross_platform"]["2_platforms"]
        else:
            cp_score = rubrics["cross_platform"]["1_platform"]

        # 2. volume
        discussion = s.get("discussion_count", 0)
        engagement_total = s.get("engagement", {}).get("total", discussion)
        volume = discussion + engagement_total // 2  # 综合 discussion 和 engagement
        if volume >= 500:
            v_score = rubrics["volume"]["gt_500"]
        elif volume >= 200:
            v_score = rubrics["volume"]["200_500"]
        elif volume >= 50:
            v_score = rubrics["volume"]["50_200"]
        else:
            v_score = rubrics["volume"]["lt_50"]

        # 3. freshness
        collected = s.get("collected_at", "")
        try:
            collected_date = datetime.fromisoformat(collected).date()
            days_old = (today - collected_date).days
        except (ValueError, TypeError):
            days_old = 0

        if days_old == 0:
            f_score = rubrics["freshness"]["today"]
        elif days_old == 1:
            f_score = rubrics["freshness"]["yesterday"]
        else:
            f_score = rubrics["freshness"]["3_days_plus"]

        # 4. actionability（基于文本关键词判断）
        tags = [t for t in s.get("tags", []) if isinstance(t, str)]
        text = f"{s.get('title', '')} {s.get('summary', '')} {' '.join(tags)}"
        text_lower = text.lower()

        actionable_patterns = [
            "alternative to", "open source", "free", "pricing", "revenue",
            "mrr", "替代", "免费", "开源", "产品", "发布", "launch",
            "收入", "定价", "赚钱", "副业", "创业", "工具",
            "builder", "template", "starter", "boilerplate", "saas",
            # 中文扩展 — 构建意图
            "怎么做", "求推荐", "有没有", "想做一个", "众筹",
            "接单", "外包", "教程", "课程", "付费", "会员",
            "订阅", "卖", "出海", "独立开发", "变现", "接活",
        ]
        complaint_patterns = [
            "抱怨", "为什么", "太贵", "不好用", "why is", "too expensive",
            "frustrated", "problem", "issue", "bug", "broken",
            # 中文扩展 — 抱怨信号
            "坑", "骗", "垃圾", "没人用", "倒闭", "跑路",
            "割韭菜", "难用", "找不到", "缺", "烦", "难受",
            "要是…就好了", "要是...就好了", "忍不了",
        ]

        actionable_count = sum(1 for p in actionable_patterns if p in text_lower)
        complaint_count = sum(1 for p in complaint_patterns if p in text_lower)

        if "show_hn" in s.get("signal_type", "") or "product-launch" in s.get("tags", []):
            a_score = rubrics["actionability"]["concrete_product_with_pricing"]
        elif actionable_count >= 3:
            a_score = rubrics["actionability"]["concrete_product_with_pricing"]
        elif actionable_count >= 1:
            a_score = rubrics["actionability"]["vague_direction"]
        elif complaint_count >= 2:
            a_score = 2  # 介于 vague 和 pure complaint 之间
        else:
            a_score = rubrics["actionability"]["pure_complaint"]

        # 5. buyer_clarity（基于角色关键词）
        buyer_patterns = [
            "工程经理", "cto", "vp", "manager", "founder", "创业",
            "独立开发者", "indie hacker", "freelancer", "自由职业",
            "developer", "engineer", "designer", "pm", "产品经理",
            "企业", "enterprise", "team", "small business",
            # 中文扩展 — 可识别买家角色
            "程序员", "老板", "小团队", "个人", "兼职", "远程",
            "数字游民", "学生", "宝妈", "自媒体", "博主", "运营",
            "hr", "财务", "律师", "医生", "教师", "设计师",
            "出海", "外贸", "电商",
        ]
        buyer_count = sum(1 for p in buyer_patterns if p in text_lower)

        if buyer_count >= 3:
            b_score = rubrics["buyer_clarity"]["specific_buyer"]
        elif buyer_count >= 1:
            b_score = rubrics["buyer_clarity"]["likely_buyer"]
        else:
            b_score = rubrics["buyer_clarity"]["unknown_buyer"]

        # 计算总分
        score = (
            cp_score * weights["cross_platform"]
            + v_score * weights["volume"]
            + f_score * weights["freshness"]
            + a_score * weights["actionability"]
            + b_score * weights["buyer_clarity"]
        )

        s["cross_platform_count"] = unique_sources
        s["score"] = score
        s["score_breakdown"] = {
            "cross_platform": {"raw": unique_sources, "score": cp_score, "weighted": cp_score * weights["cross_platform"]},
            "volume": {"raw": volume, "score": v_score, "weighted": v_score * weights["volume"]},
            "freshness": {"raw": days_old, "score": f_score, "weighted": f_score * weights["freshness"]},
            "actionability": {"raw": f"keywords:{actionable_count}", "score": a_score, "weighted": a_score * weights["actionability"]},
            "buyer_clarity": {"raw": f"buyer_keywords:{buyer_count}", "score": b_score, "weighted": b_score * weights["buyer_clarity"]},
        }

    # 最高分和平均分
    scores = [s["score"] for s in signals]
    if scores:
        print(f"[打分] 最高: {max(scores)} 分 | 平均: {sum(scores)/len(scores):.1f} 分")
        action_threshold = config["scoring"]["thresholds"]["action_trigger"]
        qualified = [s for s in signals if s["score"] >= action_threshold and s["cross_platform_count"] >= 3]
        print(f"[打分] 触发 Action 方案: {len(qualified)} 个")

    return signals


# ─── 衰减 ───────────────────────────────────────────

def apply_decay(signals: list[dict], date_str: str) -> list[dict]:
    """
    信号衰减：连续出现的同一话题降权。
    对比前 2-4 天处理后的信号，如果同一话题连续出现：
    - 连续 3 天 → score × 0.5
    - 连续 5 天 → 标记 cooling=true
    """
    today = datetime.strptime(date_str, "%Y-%m-%d")
    config = load_config()
    decay_factor = config["decay"]["3_days_same_topic"]

    # 加载前 4 天的处理结果
    previous_titles: list[str] = []
    for i in range(1, 5):
        prev_date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        prev_path = DAILY_DIR / prev_date / "signals.json"
        if prev_path.exists():
            try:
                prev_data = json.loads(prev_path.read_text(encoding="utf-8"))
                for ps in prev_data.get("signals", []):
                    previous_titles.append(ps.get("title", ""))
            except (json.JSONDecodeError, KeyError):
                pass

    decay_count = 0
    cooling_count = 0

    for s in signals:
        title = s.get("title", "")
        # 统计最近 4 天中标题相似的出现天数
        streak = 1  # 今天
        for prev_title in previous_titles:
            if _title_similarity(title, prev_title) >= 0.75:
                streak += 1

        if streak >= 5:
            s["cooling"] = True
            s["score"] = int(s["score"] * 0.3)
            cooling_count += 1
        elif streak >= 3:
            s["score"] = int(s["score"] * decay_factor)
            s["decayed"] = True
            decay_count += 1

    print(f"[衰减] 降权: {decay_count} 条 | 冷却: {cooling_count} 条")
    return signals


# ─── 主流程 ─────────────────────────────────────────

def run(date_str: str | None = None) -> list[dict]:
    """执行完整信号处理 pipeline。"""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    config = load_config()

    print(f"\n{'='*60}")
    print(f"[处理] KAKAOPC 信号处理引擎 — {date}")
    print(f"{'='*60}")

    # Step 1: 加载
    signals = load_raw_signals(date)
    if not signals:
        print("[处理] 无信号，跳过")
        return []

    # Step 2: 去重
    signals = deduplicate(signals)

    # Step 3: 聚类
    signals = cluster(signals)

    # Step 4: E-P-A 打分
    signals = score_epa(signals)

    # Step 5: 衰减
    signals = apply_decay(signals, date)

    # Step 6: 排序
    signals.sort(key=lambda s: s.get("score", 0), reverse=True)

    # Step 7: 清理内部字段（不输出 _raw_sources 到文件）
    for s in signals:
        s.pop("_raw_sources", None)

    # 保存
    output_dir = DAILY_DIR / date
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "signals.json"

    output_data = {
        "processed_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "date": date,
        "config": {
            "scoring_formula": config["scoring"]["formula"],
            "action_threshold": config["scoring"]["thresholds"]["action_trigger"],
        },
        "total_raw": len(signals),
        "signals": signals,
        "summary": {
            "top_score": max(s.get("score", 0) for s in signals) if signals else 0,
            "avg_score": round(sum(s.get("score", 0) for s in signals) / len(signals), 1) if signals else 0,
            "action_qualified": len([s for s in signals if s.get("score", 0) >= config["scoring"]["thresholds"]["action_trigger"]]),
            "cross_platform_signals": len([s for s in signals if s.get("cross_platform_count", 0) >= 2]),
        },
    }

    output_path.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[处理] 结果已保存 → {output_path}")

    # 打印 Top 10
    action_threshold = config["scoring"]["thresholds"]["action_trigger"]
    print(f"\n{'─'*60}")
    print(f"Top 10 信号（阈值: {action_threshold} 分）:")
    print(f"{'─'*60}")
    for i, s in enumerate(signals[:10], 1):
        flag = ">>>" if s["score"] >= action_threshold else "   "
        print(f"  {i:2d}. [{s['score']:3d}分] {flag} {s.get('title', 'N/A')[:65]}")
        print(f"      来源: {s.get('source', '?')} | 跨平台: {s.get('cross_platform_count', 0)} | 互动: {s.get('discussion_count', 0)}")

    return signals


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    run(today)
