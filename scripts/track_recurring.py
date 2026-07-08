"""
重复信号追踪引擎
扫描所有 daily/*/signals.json，检测跨日期反复出现的信号话题。
输出: tracking/recurring_signals.json
"""
import json
import re
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAILY_DIR = ROOT / "daily"
TRACKING_DIR = ROOT / "tracking"

TZ_SHANGHAI = timezone(timedelta(hours=8))

# 停用词 — 过滤掉高频无意义词，避免倒排索引桶过大
STOPWORDS: set[str] = {
    # 英文功能词
    "the", "and", "for", "with", "from", "that", "this", "what", "your",
    "how", "its", "not", "are", "was", "all", "can", "has", "been", "will",
    "new", "just", "like", "have", "more", "when", "make", "than", "into",
    "over", "also", "some", "one", "two", "out", "use", "get", "see", "way",
    "now", "after", "about", "each", "our", "but", "you", "too", "did",
    # 技术文档常见无意义词
    "using", "based", "v0", "v1", "v2", "v3", "v4", "v5", "day", "days",
    "week", "may", "need", "set", "try", "end", "yet", "via", "api",
    "add", "big", "top", "llm", "ai",
}

# 高频词截断阈值 — 出现次数超过此比例的词不建索引
WORD_INDEX_MAX_RATIO = 0.30


def _title_similarity(a: str, b: str) -> float:
    """计算两个标题的相似度（0-1），与 process_signals.py 保持一致。"""
    a_clean = re.sub(r"[^\w\s]", "", a.lower()).strip()
    b_clean = re.sub(r"[^\w\s]", "", b.lower()).strip()
    if not a_clean or not b_clean:
        return 0.0
    return SequenceMatcher(None, a_clean, b_clean).ratio()


def _extract_keywords(title: str) -> list[str]:
    """从标题中提取关键词（去停用词、长度 ≥ 3、非纯数字）。"""
    cleaned = re.sub(r"[^\w\s]", " ", title.lower())
    words = cleaned.split()
    result: list[str] = []
    for w in words:
        w = w.strip()
        if len(w) < 3:
            continue
        if w in STOPWORDS:
            continue
        if w.isdigit():
            continue
        result.append(w)
    # 去重保序
    seen: set[str] = set()
    unique: list[str] = []
    for w in result:
        if w not in seen:
            seen.add(w)
            unique.append(w)
    return unique


def _build_word_index(all_signals: list[dict]) -> dict[str, list[int]]:
    """构建倒排索引：word → [signal_index, ...]，并截断过高频词。"""
    from collections import defaultdict

    n = len(all_signals)
    # 第一步：统计每个词的文档频率
    word_df: dict[str, int] = defaultdict(int)
    word_signals: dict[str, list[int]] = defaultdict(list)

    for i, s in enumerate(all_signals):
        keywords = _extract_keywords(s.get("title", ""))
        for kw in keywords:
            word_signals[kw].append(i)
        for kw in set(keywords):  # 每信号每词只计一次 DF
            word_df[kw] += 1

    # 第二步：截断高文档频率词
    max_df = int(n * WORD_INDEX_MAX_RATIO)
    skipped_words: list[str] = []
    index: dict[str, list[int]] = {}

    for word, indices in word_signals.items():
        df = word_df.get(word, 0)
        if df > max_df:
            skipped_words.append(word)
            continue
        # 同一词桶内，跳过同一天的信号对（之后 Union-Find 也会跳过）
        index[word] = indices

    print(f"[重复追踪] 词索引: {len(index)} 个关键词, "
          f"平均桶大小 {sum(len(v) for v in index.values()) / max(len(index), 1):.1f}, "
          f"最大桶 {max((len(v) for v in index.values()), default=0)}")
    if skipped_words:
        print(f"[重复追踪] 跳过高频词 ({len(skipped_words)}): "
              f"{', '.join(sorted(skipped_words, key=lambda w: -word_df[w])[:20])}")

    return index


def _load_all_signals() -> list[dict]:
    """加载所有日期的信号，附带日期信息。"""
    all_signals: list[dict] = []
    if not DAILY_DIR.exists():
        return all_signals

    for date_dir in sorted(DAILY_DIR.iterdir()):
        if not date_dir.is_dir():
            continue
        date_str = date_dir.name
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            continue

        signals_path = date_dir / "signals.json"
        if not signals_path.exists():
            continue

        try:
            data = json.loads(signals_path.read_text(encoding="utf-8"))
            for s in data.get("signals", []):
                s["_date"] = date_str
                all_signals.append(s)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[重复追踪] 读取 {date_str}/signals.json 失败: {e}")

    print(f"[重复追踪] 共加载 {len(all_signals)} 条信号（{len(set(s.get('_date', '') for s in all_signals))} 天）")
    return all_signals


def _load_opportunities() -> dict[str, dict]:
    """加载机会追踪表，建立 title → opportunity 的映射。"""
    opp_map: dict[str, dict] = {}
    opp_path = TRACKING_DIR / "opportunities.json"
    if not opp_path.exists():
        return opp_map

    try:
        data = json.loads(opp_path.read_text(encoding="utf-8"))
        for op in data.get("opportunities", []):
            opp_name = op.get("opportunity", "").strip().lower()
            if opp_name:
                opp_map[opp_name] = op
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[重复追踪] 读取 opportunities.json 失败: {e}")

    return opp_map


def _find_linked_opportunity(topic: str, opp_map: dict[str, dict], related_ids: list[str]) -> dict | None:
    """查找与话题关联的机会。"""
    # 1. 直接按话题名匹配
    topic_lower = topic.strip().lower()
    if topic_lower in opp_map:
        return opp_map[topic_lower]

    # 2. 模糊匹配（标题相似度 > 0.65）
    for opp_name, op in opp_map.items():
        if _title_similarity(topic, opp_name) >= 0.65:
            return op

    # 3. 按 signal ID 匹配（机会的 signal_id 字段）
    for op in opp_map.values():
        op_signal_id = op.get("signal_id", "")
        if op_signal_id and op_signal_id in related_ids:
            return op

    return None


def _load_demand_patterns() -> list[dict]:
    """加载需求模式定义。"""
    patterns_path = ROOT / "config" / "demand_patterns.json"
    if not patterns_path.exists():
        return []
    try:
        return json.loads(patterns_path.read_text(encoding="utf-8")).get("categories", [])
    except Exception:
        return []


def _classify_demand(topic: str, summary: str, categories: list[dict]) -> str:
    """将话题归类到需求类别。返回类别 ID，无匹配则为空字符串。"""
    text = f"{topic} {summary}".lower()
    best_cat = ""
    best_hits = 0
    for cat in categories:
        hits = 0
        for kw in cat.get("keywords", []):
            if kw.lower() in text:
                hits += 1
        if hits > best_hits:
            best_hits = hits
            best_cat = cat["id"]
    # 至少命中 1 个关键词才算匹配
    return best_cat if best_hits >= 1 else ""


def _compute_trend(first_seen: str, last_seen: str, days_with_signal: set[str]) -> str:
    """计算趋势：rising / stable / fading。"""
    today = datetime.now(TZ_SHANGHAI).date()

    # 最近 7 天内出现的天数
    recent_count = 0
    for d_str in days_with_signal:
        try:
            d = datetime.strptime(d_str, "%Y-%m-%d").date()
            if (today - d).days <= 7:
                recent_count += 1
        except ValueError:
            pass

    # 前 7-14 天出现的天数（对比基线）
    earlier_count = 0
    for d_str in days_with_signal:
        try:
            d = datetime.strptime(d_str, "%Y-%m-%d").date()
            if 7 < (today - d).days <= 14:
                earlier_count += 1
        except ValueError:
            pass

    if recent_count > earlier_count:
        return "rising"
    elif recent_count == 0 and earlier_count > 0:
        return "fading"
    else:
        return "stable"


def run(date_str: str | None = None) -> list[dict]:
    """执行重复信号追踪。"""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    print(f"\n{'='*50}")
    print(f"[重复追踪] 跨日期重复信号检测 — {date}")
    print(f"{'='*50}")

    all_signals = _load_all_signals()
    if not all_signals:
        print("[重复追踪] 无信号数据，跳过")
        return []

    opp_map = _load_opportunities()
    demand_categories = _load_demand_patterns()

    # ─── 使用连通分量算法分组 ───
    # 如果两条信号标题相似度 >= 0.75，归为同一话题
    n = len(all_signals)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    # ─── 构建词索引，生成候选对 ───
    word_index = _build_word_index(all_signals)

    # 从词索引桶中收集候选信号对（去重）
    candidate_pairs: set[tuple[int, int]] = set()
    for word, indices in word_index.items():
        bucket_size = len(indices)
        if bucket_size < 2:
            continue
        for a in range(bucket_size):
            for b in range(a + 1, bucket_size):
                i, j = indices[a], indices[b]
                if i > j:
                    i, j = j, i
                candidate_pairs.add((i, j))

    print(f"[重复追踪] 候选对数量: {len(candidate_pairs)} "
          f"(vs 全量 O(n^2) = {n * (n-1) // 2:,})")

    # 跨日期标题相似度匹配（仅在候选对内比较）
    threshold = 0.75
    match_count = 0
    for i, j in candidate_pairs:
        # 同一天内的重复信号已经被 process_signals 的 dedup/cluster 处理过
        if all_signals[i]["_date"] == all_signals[j]["_date"]:
            continue
        sim = _title_similarity(
            all_signals[i].get("title", ""),
            all_signals[j].get("title", "")
        )
        if sim >= threshold:
            union(i, j)
            match_count += 1

    print(f"[重复追踪] 跨日期标题匹配: {match_count} 对（阈值 {threshold}）")

    # ─── 聚合分组 ───
    groups: dict[int, list[int]] = {}
    for i in range(n):
        root = find(i)
        groups.setdefault(root, []).append(i)

    # ─── 过滤：只保留出现在 >= 2 天的组 ───
    recurring: list[dict] = []
    counter = 0

    for root, indices in groups.items():
        group_signals = [all_signals[i] for i in indices]
        dates = set(s.get("_date", "") for s in group_signals)

        # 至少出现在 2 个不同日期
        if len(dates) < 2:
            continue

        counter += 1

        # 选互动量最高的为代表信号
        best = max(group_signals, key=lambda s: s.get("engagement", {}).get("total", 0))

        # 收集所有来源
        sources = list(dict.fromkeys(
            s.get("source", "") for s in group_signals if s.get("source")
        ))

        # 收集所有 signal ID
        related_ids = [s.get("id", "") for s in group_signals if s.get("id")]

        # 计算最高分
        peak_score = max(s.get("score", 0) for s in group_signals)

        # 日期排序
        sorted_dates = sorted(dates)
        first_seen = sorted_dates[0]
        last_seen = sorted_dates[-1]

        # 趋势
        trend = _compute_trend(first_seen, last_seen, dates)

        # 关联机会
        linked_opp = _find_linked_opportunity(
            best.get("title", ""), opp_map, related_ids
        )

        rec_id = f"REC-{counter:03d}"

        # 需求分类
        demand_cat = _classify_demand(
            best.get("title", ""),
            best.get("summary", ""),
            demand_categories
        )

        recurring.append({
            "id": rec_id,
            "topic": best.get("title", ""),
            "first_seen": first_seen,
            "last_seen": last_seen,
            "appearances": len(group_signals),
            "distinct_days": len(dates),
            "sources": sources,
            "peak_score": peak_score,
            "trend": trend,
            "demand_category": demand_cat,
            "linked_opportunity_id": linked_opp.get("id", "") if linked_opp else "",
            "related_signal_ids": related_ids,
            "last_updated": date,
        })

    # ─── 排序：按出现天数降序，同天数按最高分降序 ───
    recurring.sort(key=lambda r: (r["distinct_days"], r["peak_score"]), reverse=True)

    # 重新编号
    for i, r in enumerate(recurring):
        r["id"] = f"REC-{i+1:03d}"

    # ─── 保存 ───
    output_data = {
        "_schema": "重复信号追踪表 — 跨日期反复出现的信号话题",
        "_version": "1.0",
        "_fields": {
            "id": "唯一追踪 ID，格式：REC-XXX",
            "topic": "话题名称（代表信号的标题）",
            "first_seen": "首次出现日期",
            "last_seen": "最近出现日期",
            "appearances": "总出现次数（跨所有日期）",
            "distinct_days": "出现天数（去重日期数）",
            "sources": "来源平台列表",
            "peak_score": "最高单日得分",
            "trend": "趋势：rising（近7天增加）/ stable（持平）/ fading（近7天无新出现）",
            "linked_opportunity_id": "关联的机会追踪 ID（可为空）",
            "related_signal_ids": "所有相关信号的 ID 列表",
            "last_updated": "最后更新日期",
        },
        "recurring": recurring,
    }

    output_path = TRACKING_DIR / "recurring_signals.json"
    output_path.write_text(
        json.dumps(output_data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"[重复追踪] 发现 {len(recurring)} 个重复话题")
    for r in recurring[:10]:
        trend_icon = {"rising": "RISING", "stable": "STABLE", "fading": "FADING"}.get(r["trend"], "?")
        print(f"  {r['id']} [{trend_icon}] [{r['distinct_days']}天/{r['appearances']}次] {r['topic'][:60]}")
        print(f"       {r['first_seen']} -> {r['last_seen']} | 最高 {r['peak_score']}分 | 来源: {', '.join(r['sources'][:3])}")

    print(f"\n[重复追踪] 结果已保存 → {output_path}")
    return recurring


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    run(today)
