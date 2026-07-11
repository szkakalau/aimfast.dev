"""
第五层：Term 评分引擎
──────────────────────────
多因子加权评分，决定哪些 term 值得在日报中展示。

公式:
  score = source_count × 15    // 跨源验证（独立来源数）
        + growth × 12          // 增长趋势（近期 vs 早期提及比）
        + authority × 8        // 来源权威（加权平均）
        + mentions × 5         // 提及总量（log 标准化）
        + freshness × 10       // 新鲜度（按 last_seen 衰减）

输入:
  - tracking/canonical_terms.json
  - tracking/term_index.json   (详细 mentions 数据)
  - tracking/term_stages.json  (阶段信息)

输出:
  - tracking/term_scores.json  (每日评分快照)
  - 更新 canonical_terms.json  (score 字段)
  - daily/{date}/score_report.json (日报用 Top 20)
"""
import json
import math
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACKING_DIR = ROOT / "tracking"
DAILY_DIR = ROOT / "daily"
CONFIG_PATH = ROOT / "config.json"

TZ_SHANGHAI = timezone(timedelta(hours=8))
CANONICAL_PATH = TRACKING_DIR / "canonical_terms.json"
TERM_INDEX_PATH = TRACKING_DIR / "term_index.json"
STAGES_PATH = TRACKING_DIR / "term_stages.json"
SCORES_PATH = TRACKING_DIR / "term_scores.json"

def _load_authority() -> dict[str, int]:
    """从 config.json 加载来源权威权重，不可用时回退到共享默认值。"""
    try:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        auth = cfg.get("source_authority")
        if auth:
            return auth
    except Exception:
        pass
    try:
        from scripts.defaults import DEFAULT_SOURCE_AUTHORITY
        return DEFAULT_SOURCE_AUTHORITY
    except ImportError:
        return {}


def _load_term_mentions() -> dict[str, list[dict]]:
    """从 term_index.json 提取每个 canonical term 的 mentions 列表。"""
    if not TERM_INDEX_PATH.exists():
        return {}

    ti = json.loads(TERM_INDEX_PATH.read_text(encoding="utf-8"))
    terms_db = ti.get("terms", {})
    mentions: dict[str, list[dict]] = defaultdict(list)

    for term_name, entry in terms_db.items():
        canonical = entry.get("canonical_name", term_name)
        for ref in entry.get("signals", []):
            mentions[canonical].append({
                "date": ref.get("date", ""),
                "source": ref.get("source", ""),
                "source_key": ref.get("source_key", ""),
            })

    return dict(mentions)


def _growth_factor(mentions: list[dict], today: datetime.date) -> float:
    """计算增长因子。近期 7 天 vs 前 7 天的提及比。"""
    recent = 0
    earlier = 0

    for m in mentions:
        try:
            m_date = datetime.strptime(m["date"], "%Y-%m-%d").date()
            days_ago = (today - m_date).days
            if 0 <= days_ago <= 7:
                recent += 1
            elif 8 <= days_ago <= 14:
                earlier += 1
        except (ValueError, TypeError):
            pass

    if earlier == 0 and recent == 0:
        return 5.0  # 无历史数据，默认中性
    if earlier == 0:
        # 新词无历史基线，无法判断增长方向 → 中性分
        # 新词的优势通过 freshness（新鲜度）维度体现，不重复计入 growth
        return 5.0

    ratio = recent / max(earlier, 1)
    return max(1.0, min(10.0, ratio * 5.0))


def _authority_score(mentions: list[dict], authority_map: dict[str, int]) -> float:
    """计算加权平均权威分。"""
    if not mentions:
        return 3.0

    total_weight = 0
    weighted_sum = 0

    for m in mentions:
        sk = m.get("source_key", "unknown")
        auth = authority_map.get(sk, 3)
        weighted_sum += auth
        total_weight += 1

    return weighted_sum / max(total_weight, 1)


def _mentions_score(appearances: int) -> float:
    """log 标准化提及量到 1-10 区间。"""
    if appearances <= 1:
        return 1.0
    return min(10.0, 1.0 + math.log2(appearances) * 1.5)


def _freshness_score(last_seen: str, today: datetime.date) -> float:
    """按 last_seen 的衰减计算新鲜度。今天=10, 昨天=7, 3天前=4, 7天前=1。"""
    if not last_seen:
        return 5.0
    try:
        ls_date = datetime.strptime(last_seen, "%Y-%m-%d").date()
        days = (today - ls_date).days
        if days <= 0:
            return 10.0
        elif days <= 1:
            return 7.0
        elif days <= 3:
            return 4.0
        elif days <= 7:
            return 2.0
        else:
            return 1.0
    except (ValueError, TypeError):
        return 5.0


def _source_count_score(distinct_sources: int) -> float:
    """跨源数量直接映射到 1-10。"""
    if distinct_sources >= 5:
        return 10.0
    if distinct_sources >= 3:
        return 8.0
    if distinct_sources >= 2:
        return 5.0
    return 1.0


def _compute_scores(
    canonicals: dict,
    mentions_map: dict[str, list[dict]],
    authority_map: dict[str, int],
    today: datetime.date,
) -> list[dict]:
    """对所有 canonical term 计算评分。"""
    scored: list[dict] = []

    for name, entry in canonicals.items():
        term_mentions = mentions_map.get(name, [])

        # 计算各因子
        src_count = _source_count_score(entry.get("distinct_sources", 1))
        growth = _growth_factor(term_mentions, today)
        authority = _authority_score(term_mentions, authority_map)
        mentions_raw = _mentions_score(entry.get("appearances", 0))
        freshness = _freshness_score(entry.get("last_seen", ""), today)

        # 加权总分
        score = round(
            src_count * 15
            + growth * 12
            + authority * 8
            + mentions_raw * 5
            + freshness * 10,
            1,
        )

        scored.append({
            "term": name,
            "term_type": entry.get("term_type", "unknown"),
            "stage": entry.get("stage", "nascent"),
            "age_days": entry.get("age_days", 0),
            "score": score,
            "breakdown": {
                "source_count": {"raw": entry.get("distinct_sources", 1), "score": round(src_count, 1), "weighted": round(src_count * 15, 1)},
                "growth": {"raw": f"ratio={growth:.1f}", "score": round(growth, 1), "weighted": round(growth * 12, 1)},
                "authority": {"raw": f"avg={authority:.1f}", "score": round(authority, 1), "weighted": round(authority * 8, 1)},
                "mentions": {"raw": entry.get("appearances", 0), "score": round(mentions_raw, 1), "weighted": round(mentions_raw * 5, 1)},
                "freshness": {"raw": entry.get("last_seen", ""), "score": round(freshness, 1), "weighted": round(freshness * 10, 1)},
            },
        })

    scored.sort(key=lambda s: s["score"], reverse=True)
    return scored


def run(date_str: str | None = None):
    """执行 term 评分。"""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    today = datetime.strptime(date, "%Y-%m-%d").date()

    print(f"\n{'='*50}")
    print(f"[Scores] 第五层：Term 多因子评分 — {date}")
    print(f"{'='*50}")

    # Step 1: 加载数据
    if not CANONICAL_PATH.exists():
        print("[Scores] canonical_terms.json 不存在，跳过")
        return

    canonicals = json.loads(CANONICAL_PATH.read_text(encoding="utf-8"))["canonicals"]
    mentions_map = _load_term_mentions()
    authority_map = _load_authority()

    print(f"[Scores] 评分 {len(canonicals)} 个 canonical terms")

    # Step 2: 计算评分
    scored = _compute_scores(canonicals, mentions_map, authority_map, today)

    # Step 3: 更新 canonical_terms.json
    score_map = {s["term"]: s["score"] for s in scored}
    canonical_data = json.loads(CANONICAL_PATH.read_text(encoding="utf-8"))
    for name, entry in canonical_data["canonicals"].items():
        entry["score"] = score_map.get(name, 0)
    canonical_data["last_updated"] = datetime.now(TZ_SHANGHAI).isoformat()
    from scripts.defaults import atomic_write_json
    atomic_write_json(CANONICAL_PATH, canonical_data)

    # Step 4: 保存评分快照
    score_data = {
        "_schema": "Term 多因子评分 — 决定日报展示优先级",
        "_version": "1.0",
        "_formula": "source_count×15 + growth×12 + authority×8 + mentions×5 + freshness×10",
        "date": date,
        "total_terms": len(scored),
        "scores": scored,
    }

    from scripts.defaults import atomic_write_json
    atomic_write_json(SCORES_PATH, score_data)

    # Step 5: 输出日报摘要
    print(f"\n[Scores] 评分分布:")
    buckets = {"90+": 0, "70-89": 0, "50-69": 0, "30-49": 0, "<30": 0}
    for s in scored:
        sc = s["score"]
        if sc >= 90: buckets["90+"] += 1
        elif sc >= 70: buckets["70-89"] += 1
        elif sc >= 50: buckets["50-69"] += 1
        elif sc >= 30: buckets["30-49"] += 1
        else: buckets["<30"] += 1
    for label, count in buckets.items():
        bar = "█" * max(1, count // max(1, max(buckets.values()) // 20))
        print(f"  {label:6s}: {count:3d}  {bar}")

    top_n = min(20, len(scored))
    print(f"\n[Scores] Top {top_n} — 应上日报首页:")
    for i, s in enumerate(scored[:top_n], 1):
        bd = s["breakdown"]
        print(f"  {i:2d}. [{s['score']:5.1f}] {s['term'][:60]}")
        print(f"      源:{s['term_type']} | 阶段:{s['stage']} | "
              f"跨源:{bd['source_count']['raw']} | "
              f"增长:{bd['growth']['score']:.1f} | "
              f"权威:{bd['authority']['score']:.1f}")

    # Step 6: 保存日报文件
    output_dir = DAILY_DIR / date
    output_dir.mkdir(parents=True, exist_ok=True)
    score_report = {
        "date": date,
        "formula": "source_count×15 + growth×12 + authority×8 + mentions×5 + freshness×10",
        "top_20": scored[:20],
        "distribution": buckets,
    }
    (output_dir / "score_report.json").write_text(
        json.dumps(score_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n[Scores] term_scores.json → {SCORES_PATH}")
    print(f"[Scores] score_report.json → {output_dir / 'score_report.json'}")
    return scored


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    run(today)
