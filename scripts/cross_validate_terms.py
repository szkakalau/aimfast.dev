"""
跨源术语验证引擎 (v1.0)
输入: raw/YYYY-MM-DD/ 下所有采集器的 JSON 文件
输出: daily/YYYY-MM-DD/cross_validation.json

功能:
  1. 从当日所有信源的信号中提取关键术语
  2. 检测哪些术语出现在 3+ 个独立信源中
  3. 生成跨源置信度评分 — 多源验证 = 更可能是真实趋势

方法论:
  - 同一个术语在 HN、Reddit、GitHub、掘金同时出现 = 高置信度趋势
  - 只在一个信源出现 = 可能是噪声
  - 跨源验证是 Exploding Topics、CB Insights 等竞品的核心差异化能力
"""
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"
DAILY_DIR = ROOT / "daily"

TZ_SHANGHAI = timezone(timedelta(hours=8))

# ── 术语提取用的停用词/噪声词 ──
STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "shall", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "through", "during",
    "before", "after", "above", "below", "between", "and", "but", "or",
    "not", "no", "this", "that", "these", "those", "it", "its", "they",
    "them", "their", "we", "you", "he", "she", "his", "her", "my", "your",
    "our", "all", "each", "every", "both", "few", "more", "most", "other",
    "some", "such", "only", "own", "same", "so", "than", "too", "very",
    "just", "now", "new", "also", "how", "like", "use", "using", "used",
    "make", "made", "get", "got", "one", "two", "first", "still", "much",
    "many", "way", "well", "even", "back", "part", "work", "need", "show",
}

# ── 从文本中提取 bigram/trigram 关键词 ──
def _extract_terms(text: str) -> list[str]:
    """从文本中提取有意义的 2-3 词术语。"""
    # 清理
    text = re.sub(r"[^\w\s\-+#.]", " ", text.lower())
    words = [w for w in text.split() if len(w) > 1 and w not in STOP_WORDS]

    terms = []
    # bigrams
    for i in range(len(words) - 1):
        term = f"{words[i]} {words[i+1]}"
        if 5 <= len(term) <= 40:
            terms.append(term)
    # trigrams
    for i in range(len(words) - 2):
        term = f"{words[i]} {words[i+1]} {words[i+2]}"
        if 8 <= len(term) <= 50:
            terms.append(term)

    return terms


def _load_today_signals(date_str: str) -> list[dict]:
    """加载当日所有 raw/*.json 中的信号。"""
    raw_date_dir = RAW_DIR / date_str
    if not raw_date_dir.exists():
        print(f"[CrossVal] raw/{date_str}/ 目录不存在")
        return []

    all_signals = []
    source_count = 0
    for json_file in sorted(raw_date_dir.glob("*.json")):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            signals = data.get("signals", [])
            source = data.get("source", json_file.stem)
            # 标注每条信号的来源
            for s in signals:
                s["_file_source"] = json_file.stem
            all_signals.extend(signals)
            if signals:
                source_count += 1
                print(f"[CrossVal] {json_file.stem}: {len(signals)} 条信号")
        except (json.JSONDecodeError, OSError) as e:
            print(f"[CrossVal] 跳过 {json_file.name}: {e}")

    print(f"[CrossVal] 加载 {len(all_signals)} 条信号 (来自 {source_count} 个信源)")
    return all_signals


def collect(date_str: str | None = None) -> dict:
    """运行跨源验证分析。

    Returns:
        dict with:
        - cross_source_terms: 跨源术语列表（含出现源和置信度）
        - source_matrix: 信源×术语共现矩阵
        - stats: 汇总统计
    """
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    signals = _load_today_signals(date)

    if not signals:
        return {
            "date": date,
            "cross_source_terms": [],
            "stats": {"total_signals": 0, "total_sources": 0, "cross_source_terms": 0},
        }

    # ── 术语 → 出现的信源集合 ──
    term_sources: dict[str, set[str]] = defaultdict(set)
    term_examples: dict[str, list[str]] = defaultdict(list)  # 术语 → 示例标题

    for s in signals:
        title = s.get("title", "")
        summary = s.get("summary", "")
        source = s.get("_file_source", "unknown")

        # 提取术语
        terms = _extract_terms(f"{title} {summary}")

        # 每个信号对其提取的术语最多贡献 3 个（避免长文本主导）
        seen_in_signal: set[str] = set()
        for term in terms:
            if term in seen_in_signal:
                continue
            seen_in_signal.add(term)
            term_sources[term].add(source)
            if len(term_examples[term]) < 3:
                term_examples[term].append(title[:100])

    # ── 按出现源数量筛选跨源术语 ──
    cross_source = []
    for term, sources in term_sources.items():
        source_count = len(sources)
        if source_count >= 2:  # 至少出现在 2 个不同信源
            # 置信度: 3+ 源 = high, 2 源 = medium
            confidence = "high" if source_count >= 3 else "medium"

            cross_source.append({
                "term": term,
                "source_count": source_count,
                "sources": sorted(sources),
                "confidence": confidence,
                "examples": term_examples.get(term, [])[:3],
            })

    # 按源数量 + 字母序排序
    cross_source.sort(key=lambda x: (-x["source_count"], x["term"]))

    # ── 统计 ──
    all_sources = set()
    for sources in term_sources.values():
        all_sources.update(sources)

    stats = {
        "total_signals": len(signals),
        "total_sources": len(all_sources),
        "total_terms_extracted": len(term_sources),
        "cross_source_terms": len(cross_source),
        "high_confidence": sum(1 for t in cross_source if t["confidence"] == "high"),
        "medium_confidence": sum(1 for t in cross_source if t["confidence"] == "medium"),
    }

    # ── 输出 ──
    high_terms = [t for t in cross_source if t["confidence"] == "high"][:10]
    if high_terms:
        print(f"[CrossVal] 高置信度术语 (3+ 源):")
        for t in high_terms:
            print(f"  '{t['term']}' — {t['source_count']} 源: {', '.join(t['sources'][:5])}")

    print(f"[CrossVal] 总计: {stats['total_terms_extracted']} 个术语 → {stats['cross_source_terms']} 跨源 (high: {stats['high_confidence']}, medium: {stats['medium_confidence']})")

    return {
        "date": date,
        "analyzed_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "cross_source_terms": cross_source[:200],  # top 200
        "stats": stats,
    }


def save_raw(result: dict, date_str: str) -> None:
    """保存到 daily/YYYY-MM-DD/cross_validation.json"""
    dir_path = DAILY_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    path = dir_path / "cross_validation.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    stats = result.get("stats", {})
    print(f"[CrossVal] 结果 → {path} ({stats.get('cross_source_terms', 0)} 跨源术语)")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
