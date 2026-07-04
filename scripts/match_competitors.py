"""
竞品/话题匹配引擎 (Phase 1 — 双引擎架构)
输入: ./daily/YYYY-MM-DD/signals.json + ./tracking/competitor_targets.json
输出: ./daily/YYYY-MM-DD/competitor_matches.json
策略: 语义匹配（contains + fuzzy）为主，关键词匹配兜底
      所有匹配结果保留原始信号引用，不做去噪（去噪留给 LLM）
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAILY_DIR = ROOT / "daily"
TRACKING_DIR = ROOT / "tracking"

TZ_SHANGHAI = timezone(timedelta(hours=8))

# 匹配阈值
FUZZY_THRESHOLD = 0.65   # fuzzy 匹配最低相似度
KEYWORD_MATCH_MIN = 1     # 至少命中几个关键词才算匹配


def load_targets() -> list[dict]:
    """加载活跃追踪目标。"""
    path = TRACKING_DIR / "competitor_targets.json"
    if not path.exists():
        print(f"[竞品匹配] {path} 不存在，跳过")
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    targets = data.get("targets", [])
    active = [t for t in targets if t.get("status") == "active"]
    if not active:
        print(f"[竞品匹配] 无活跃追踪目标（共 {len(targets)} 个，活跃 0）")
    else:
        print(f"[竞品匹配] 加载 {len(active)} 个活跃目标（共 {len(targets)} 个）")
    return active


def _fuzzy_match(text: str, target: str) -> float:
    """计算两段文本的模糊相似度（0-1）。"""
    return SequenceMatcher(None, text.lower(), target.lower()).ratio()


def _keyword_match(text: str, keywords: list[str]) -> int:
    """统计命中的关键词数量。"""
    text_lower = text.lower()
    count = 0
    for kw in keywords:
        if kw.lower() in text_lower:
            count += 1
    return count


def match_target_to_signals(target: dict, signals: list[dict]) -> list[dict]:
    """
    对一个追踪目标，在所有信号中做匹配。
    匹配策略（按优先级）：
      1. 直接名称/别名包含匹配（高置信度）
      2. 模糊匹配（标题相似度 ≥ FUZZY_THRESHOLD）
      3. 关键词兜底（命中 ≥ KEYWORD_MATCH_MIN 个关键词）
    返回带匹配分数的信号列表。
    """
    name = target.get("name", "")
    aliases = target.get("aliases", [])
    keywords = target.get("keywords", [])
    all_terms = [name] + aliases

    matches = []
    for sig in signals:
        title = sig.get("title", "")
        summary = sig.get("summary", "")
        combined = f"{title} {summary}"

        match_score = 0
        match_method = None

        # 1. 直接包含匹配
        for term in all_terms:
            if term.lower() in combined.lower():
                match_score = max(match_score, 0.9)
                match_method = "contains"
                break

        # 2. 模糊匹配（仅在 contains 未命中时）
        if match_score < 0.9:
            best_fuzzy = 0.0
            for term in all_terms:
                if len(term) >= 3:
                    sim = _fuzzy_match(title[:200], term)
                    best_fuzzy = max(best_fuzzy, sim)
            if best_fuzzy >= FUZZY_THRESHOLD:
                match_score = best_fuzzy
                match_method = "fuzzy"

        # 3. 关键词兜底（仅在以上都未命中时）
        if match_score == 0 and keywords:
            kw_count = _keyword_match(combined, keywords)
            if kw_count >= KEYWORD_MATCH_MIN:
                match_score = min(0.5 + kw_count * 0.1, 0.85)
                match_method = f"keywords({kw_count})"

        if match_score > 0:
            matches.append({
                "signal_id": sig.get("id", ""),
                "title": title,
                "url": sig.get("url", ""),
                "source": sig.get("source", sig.get("source_key", "")),
                "score": sig.get("score", 0),
                "discussion_count": sig.get("discussion_count", 0),
                "summary": summary[:500],
                "tags": sig.get("tags", []),
                "collected_at": sig.get("collected_at", ""),
                "match_score": round(match_score, 2),
                "match_method": match_method,
            })

    # 按匹配分排序
    matches.sort(key=lambda m: m["match_score"], reverse=True)
    return matches


def load_signals(date_str: str) -> list[dict]:
    """加载当日处理后的信号。"""
    path = DAILY_DIR / date_str / "signals.json"
    if not path.exists():
        print(f"[竞品匹配] {path} 不存在")
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    signals = data.get("signals", [])
    print(f"[竞品匹配] 加载 {len(signals)} 条信号")
    return signals


def run(date_str: str | None = None) -> dict:
    """运行竞品匹配，返回按目标分组的匹配结果。"""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    print(f"\n{'='*50}")
    print(f"[竞品匹配] 追踪目标匹配 — {date}")
    print(f"{'='*50}")

    targets = load_targets()
    if not targets:
        return {"date": date, "targets": []}

    signals = load_signals(date)
    if not signals:
        return {"date": date, "targets": []}

    results = []
    for target in targets:
        tid = target.get("id", "")
        tname = target.get("name", "")
        matches = match_target_to_signals(target, signals)
        print(f"[竞品匹配]   {tname}: {len(matches)} 个匹配 "
              f"(contains={sum(1 for m in matches if m['match_method'] == 'contains')}, "
              f"fuzzy={sum(1 for m in matches if m['match_method'] == 'fuzzy')}, "
              f"keywords={sum(1 for m in matches if 'keywords' in m['match_method'])})")

        results.append({
            "target_id": tid,
            "target_name": tname,
            "target_type": target.get("type", "competitor"),
            "aliases": target.get("aliases", []),
            "keywords": target.get("keywords", []),
            "matches": matches,
            "match_count": len(matches),
        })

    output = {
        "date": date,
        "generated_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "target_count": len(targets),
        "targets": results,
    }

    # 保存到 daily/
    out_dir = DAILY_DIR / date
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "competitor_matches.json"
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[竞品匹配] 已保存 → {out_path}")

    total_matches = sum(r["match_count"] for r in results)
    print(f"[竞品匹配] 共 {total_matches} 个匹配（{len(targets)} 个目标）")
    return output


if __name__ == "__main__":
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
    else:
        date_str = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    run(date_str)
