"""
需求雷达引擎
扫描 daily/*/signals.json，按需求类别聚类，生成周快照 + 机会评分。
输出: tracking/demand_radar.json
"""
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAILY_DIR = ROOT / "daily"
CONFIG_DIR = ROOT / "config"
TRACKING_DIR = ROOT / "tracking"

TZ_SHANGHAI = timezone(timedelta(hours=8))


def _load_demand_patterns() -> list[dict]:
    """加载需求模式定义。"""
    path = CONFIG_DIR / "demand_patterns.json"
    if not path.exists():
        print("[需求雷达] demand_patterns.json 不存在，使用默认配置")
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("categories", [])


def _load_signals_by_week() -> dict[str, list[dict]]:
    """按周分组加载所有信号。返回 {week_label: [signals]}"""
    weeks: dict[str, list[dict]] = {}
    if not DAILY_DIR.exists():
        return weeks

    for date_dir in sorted(DAILY_DIR.iterdir()):
        if not date_dir.is_dir():
            continue
        date_str = date_dir.name
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            continue

        signals_path = date_dir / "signals.json"
        if not signals_path.exists():
            continue

        try:
            data = json.loads(signals_path.read_text(encoding="utf-8"))
            for s in data.get("signals", []):
                s["_date"] = date_str
        except (json.JSONDecodeError, KeyError):
            continue

        # 计算该日期所属的周一
        monday = d - timedelta(days=d.weekday())
        week_key = monday.strftime("%Y-%m-%d")

        if week_key not in weeks:
            weeks[week_key] = []
        weeks[week_key].extend(data.get("signals", []))

    return weeks


def _match_category(signal: dict, category: dict) -> int:
    """计算信号与需求类别的匹配度（0-10）。基于关键词命中数。"""
    tags = [t for t in signal.get('tags', []) if isinstance(t, str)]
    text = f"{signal.get('title', '')} {signal.get('summary', '')} {' '.join(tags)}"
    text_lower = text.lower()

    keywords = category.get("keywords", [])
    if not keywords:
        return 0

    hits = 0
    for kw in keywords:
        if kw.lower() in text_lower:
            hits += 1

    # 命中 1 个关键词 = 1 分，每多一个 +1，最高 10 分
    if hits == 0:
        return 0
    score = min(hits + 1, 10)

    # 如果标题直接包含类别名 → 额外加成
    name = category.get("name", "")
    if name and name.lower() in signal.get("title", "").lower():
        score = min(score + 2, 10)

    return score


def _score_demand(category: dict, weekly_counts: dict[str, int], weekly_totals: dict[str, int]) -> dict:
    """计算单个需求类别的机会评分。

    机会指数 = heat_score × growth_score × pain_score × payment_score
    每个维度 1-10，乘积归一化到 1-10。
    """
    sorted_weeks = sorted(weekly_counts.keys())
    if not sorted_weeks:
        return _empty_score()

    # 1. 热度（信号量 vs 总信号量）
    total_signals_in_category = sum(weekly_counts.values())
    total_signals_overall = sum(weekly_totals.values())
    if total_signals_overall > 0:
        ratio = total_signals_in_category / total_signals_overall
        heat_score = min(10, round(ratio * 100))
    else:
        heat_score = 0
    heat_score = max(1, heat_score)  # 最低 1 分

    # 2. 增速（最近 2 周 vs 前 2 周）
    recent_weeks = sorted_weeks[-2:] if len(sorted_weeks) >= 2 else sorted_weeks
    earlier_weeks = sorted_weeks[:-2] if len(sorted_weeks) > 2 else []

    recent_avg = sum(weekly_counts[w] for w in recent_weeks) / len(recent_weeks)
    if earlier_weeks:
        earlier_avg = sum(weekly_counts[w] for w in earlier_weeks) / len(earlier_weeks)
    else:
        earlier_avg = 0

    if earlier_avg > 0:
        growth_ratio = recent_avg / earlier_avg
        if growth_ratio >= 3.0:
            growth_score = 10
        elif growth_ratio >= 2.0:
            growth_score = 8
        elif growth_ratio >= 1.5:
            growth_score = 7
        elif growth_ratio >= 1.2:
            growth_score = 6
        elif growth_ratio >= 1.0:
            growth_score = 5
        elif growth_ratio >= 0.7:
            growth_score = 3
        else:
            growth_score = 1
    elif recent_avg > 0 and earlier_avg == 0:
        growth_score = 9  # 新出现的需求
    else:
        growth_score = 5

    # 3. 痛感（来自配置基值）
    pain_score = category.get("pain_base", 5)

    # 4. 付费能力（来自配置基值）
    payment_score = category.get("payment_base", 5)

    # 综合机会指数（归一化到 1-10）
    raw = heat_score * growth_score * pain_score * payment_score
    # 最大可能值 10×10×10×10 = 10000
    opportunity_index = round(raw ** 0.25)  # 几何平均 → 1-10
    opportunity_index = max(1, min(10, opportunity_index))

    return {
        "heat_score": heat_score,
        "growth_score": growth_score,
        "pain_score": pain_score,
        "payment_score": payment_score,
        "opportunity_index": opportunity_index,
    }


def _detect_intersections(categories: list[dict], scores: dict[str, dict], weekly_counts: dict[str, dict]) -> list[dict]:
    """检测需求交叉点。当两个需求同时上升时，标记交叉机会。"""
    patterns = json.loads(
        (CONFIG_DIR / "demand_patterns.json").read_text(encoding="utf-8")
    ).get("intersection_rules", {})
    pairs = patterns.get("pairs", [])

    intersections = []
    for id_a, id_b in pairs:
        if id_a not in scores or id_b not in scores:
            continue
        sa = scores[id_a]
        sb = scores[id_b]

        # 两个需求都至少有数据
        counts_a = weekly_counts.get(id_a, {})
        counts_b = weekly_counts.get(id_b, {})

        if not counts_a or not counts_b:
            continue

        # 检查是否都在上升
        a_growing = sa["growth_score"] >= 6
        b_growing = sb["growth_score"] >= 6

        if a_growing and b_growing:
            # 找类别名称
            name_a = next((c["name"] for c in categories if c["id"] == id_a), id_a)
            name_b = next((c["name"] for c in categories if c["id"] == id_b), id_b)

            cross_score = round((sa["opportunity_index"] + sb["opportunity_index"]) / 2)
            intersections.append({
                "demand_a": id_a,
                "demand_b": id_b,
                "label": f"{name_a} × {name_b}",
                "cross_score": cross_score,
            })

    intersections.sort(key=lambda x: x["cross_score"], reverse=True)
    return intersections


def _empty_score() -> dict:
    return {
        "heat_score": 0,
        "growth_score": 0,
        "pain_score": 0,
        "payment_score": 0,
        "opportunity_index": 0,
    }


def run(date_str: str | None = None) -> dict:
    """执行需求雷达分析。"""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    print(f"\n{'='*50}")
    print(f"[需求雷达] 需求聚类与机会评分 — {date}")
    print(f"{'='*50}")

    categories = _load_demand_patterns()
    if not categories:
        print("[需求雷达] 无需求模式定义，跳过")
        return {}

    weeks = _load_signals_by_week()
    if not weeks:
        print("[需求雷达] 无信号数据，跳过")
        return {}

    sorted_weeks = sorted(weeks.keys())
    print(f"[需求雷达] 时间范围: {sorted_weeks[0]} → {sorted_weeks[-1]} ({len(weeks)} 周)")
    print(f"[需求雷达] {len(categories)} 个需求类别")

    # ─── 计算每周每个需求类别的信号数 ───
    weekly_counts: dict[str, dict[str, int]] = {}  # {demand_id: {week: count}}
    weekly_totals: dict[str, int] = {}  # {week: total_signals}

    for week, signals in weeks.items():
        weekly_totals[week] = len(signals)

    for cat in categories:
        cat_id = cat["id"]
        weekly_counts[cat_id] = {}
        for week, signals in weeks.items():
            count = sum(1 for s in signals if _match_category(s, cat) >= 3)
            weekly_counts[cat_id][week] = count

    # ─── 计算每个需求的机会评分 ───
    scores: dict[str, dict] = {}
    for cat in categories:
        cat_id = cat["id"]
        counts = weekly_counts[cat_id]
        scores[cat_id] = _score_demand(cat, counts, weekly_totals)

    # ─── 检测交叉机会 ───
    intersections = _detect_intersections(categories, scores, weekly_counts)

    # ─── 构建周快照列表（用于前端表格） ───
    demand_entries = []
    for cat in categories:
        cat_id = cat["id"]
        score = scores[cat_id]
        counts = weekly_counts[cat_id]

        # 取最近 3 周的快照数据
        recent_3_weeks = sorted_weeks[-3:] if len(sorted_weeks) >= 3 else sorted_weeks
        snapshots = {}
        for w in recent_3_weeks:
            snapshots[w] = counts.get(w, 0)

        # 计算变化方向
        if len(recent_3_weeks) >= 2:
            latest = counts.get(recent_3_weeks[-1], 0)
            prev = counts.get(recent_3_weeks[-2], 0)
            if latest > prev:
                delta = "rising"
            elif latest < prev:
                delta = "falling"
            else:
                delta = "stable"
        else:
            delta = "new"

        # 总信号数
        total_signals = sum(counts.values())

        demand_entries.append({
            "id": cat_id,
            "name": cat["name"],
            "name_en": cat.get("name_en", cat["name"]),
            "description": cat.get("description", ""),
            "snapshots": snapshots,
            "total_signals": total_signals,
            "delta": delta,
            "heat_score": score["heat_score"],
            "growth_score": score["growth_score"],
            "pain_score": score["pain_score"],
            "payment_score": score["payment_score"],
            "opportunity_index": score["opportunity_index"],
        })

    # ─── 按机会指数排序 ───
    demand_entries.sort(key=lambda d: d["opportunity_index"], reverse=True)

    # ─── 构建输出 ───
    output = {
        "_schema": "需求雷达 — 需求聚类 + 周快照 + 机会评分",
        "_version": "1.0",
        "generated_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "weeks": sorted_weeks[-6:],  # 最近 6 周的标签
        "demands": demand_entries,
        "intersections": intersections,
    }

    output_path = TRACKING_DIR / "demand_radar.json"
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    # ─── 打印摘要 ───
    print(f"\n[需求雷达] 需求机会评分 (Top 8):")
    trend_icons = {"rising": "[UP]", "stable": "[--]", "falling": "[DN]", "new": "[NEW]"}
    for i, d in enumerate(demand_entries[:8]):
        icon = trend_icons.get(d["delta"], "?")
        print(f"  {i+1}. [{d['opportunity_index']}/10] {icon} {d['name']} "
              f"(热度:{d['heat_score']} 增速:{d['growth_score']} 痛感:{d['pain_score']} 付费:{d['payment_score']})")

    if intersections:
        print(f"\n[需求雷达] 交叉机会 ({len(intersections)}):")
        for x in intersections[:5]:
            print(f"  [{x['cross_score']}/10] {x['label']}")

    print(f"\n[需求雷达] 结果已保存 → {output_path}")
    return output


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    run(today)
