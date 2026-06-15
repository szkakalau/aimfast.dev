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


def _score_demand(category: dict, weekly_counts: dict[str, int], total_demand_signals: int, max_appearances: int, max_distinct_days: int) -> dict:
    """计算单个需求类别的机会评分。

    V3 公式（Market/Business 分离）:
      MarketScore  = (Trend×0.5 + Growth×0.3 + Consistency×0.2) × 100    → 0-100
      BusinessScore = (PainScore×0.5 + PayScore×0.5) × 100                 → 0-100
      Confidence   = log2(samples + 1) × 20, cap 100                       → 0-100
      Stage        = Early / Forming / Breaking / Mature
      Opportunity  = MarketScore × 0.6 + BusinessScore × 0.4               → 0-100
    """
    import math

    sorted_weeks = sorted(weekly_counts.keys())
    if not sorted_weeks:
        return _empty_score()

    # ─── 从配置读取属性 ───
    pain_cfg = category.get("pain", {})
    pay_cfg = category.get("pay", {})

    # ─── MARKET SCORE (从数据计算) ───

    # 1. Trend 子分数: 出现次数归一化 (0-1)
    total_appearances = sum(weekly_counts.values())
    if max_appearances > 0:
        trend_component = total_appearances / max_appearances  # 0-1
    else:
        trend_component = 0

    # 2. Growth 子分数: 增速 (0-1)
    recent_weeks = sorted_weeks[-2:] if len(sorted_weeks) >= 2 else sorted_weeks
    earlier_weeks = sorted_weeks[:-2] if len(sorted_weeks) > 2 else []

    recent_avg = sum(weekly_counts[w] for w in recent_weeks) / len(recent_weeks) if recent_weeks else 0
    if earlier_weeks:
        earlier_avg = sum(weekly_counts[w] for w in earlier_weeks) / len(earlier_weeks)
    else:
        earlier_avg = 0

    if earlier_avg > 0:
        growth_ratio = recent_avg / earlier_avg
        if growth_ratio >= 3.0:
            growth_component = 1.0
        elif growth_ratio >= 2.0:
            growth_component = 0.9
        elif growth_ratio >= 1.5:
            growth_component = 0.8
        elif growth_ratio >= 1.2:
            growth_component = 0.7
        elif growth_ratio >= 1.0:
            growth_component = 0.5
        elif growth_ratio >= 0.7:
            growth_component = 0.3
        else:
            growth_component = 0.1
    elif recent_avg > 0 and earlier_avg == 0:
        growth_component = 0.6  # 新出现的需求
    else:
        growth_component = 0.5

    # 3. Consistency 子分数: 出现天数 / 最大天数 (0-1)
    distinct_days = len([w for w in weekly_counts if weekly_counts[w] > 0])
    if max_distinct_days > 0:
        consistency_component = distinct_days / max_distinct_days  # 0-1
    else:
        consistency_component = 0

    # MarketScore = weighted sum, scale to 0-100
    market_score = round((trend_component * 0.5 + growth_component * 0.3 + consistency_component * 0.2) * 100)
    market_score = max(1, min(100, market_score))

    # ─── BUSINESS SCORE (从配置计算) ───

    # Pain: frequency × severity / 10 → 0-10, then to 0-1
    pain_freq = pain_cfg.get("frequency", 5)
    pain_sev = pain_cfg.get("severity", 5)
    pain_score = (pain_freq * pain_sev) / 100  # 0-1 (product 0-100 / 100)

    # Pay: budget × urgency / 10 → 0-10, then to 0-1
    pay_budget = pay_cfg.get("budget", 5)
    pay_urgency = pay_cfg.get("urgency", 5)
    pay_score = (pay_budget * pay_urgency) / 100  # 0-1

    # BusinessScore = weighted sum, scale to 0-100
    business_score = round((pain_score * 0.5 + pay_score * 0.5) * 100)
    business_score = max(1, min(100, business_score))

    # ─── COMPETITION (信号密度 + 人工基值) ───
    # 自动竞争度: 信号越多 = 竞争越激烈 (以最强需求为 100)
    if max_appearances > 0:
        auto_competition = round((total_appearances / max_appearances) * 100)
    else:
        auto_competition = 0
    # 人工基值: 已知大厂垄断或开源泛滥的赛道
    config_competition = category.get("competition", 50)
    # 取两者中较高值 — 兼顾市场实际和领域知识
    competition = min(100, max(auto_competition, config_competition))

    # ─── CONFIDENCE (基于样本量) ───
    confidence = round(math.log2(total_appearances + 1) * 20)
    confidence = max(1, min(100, confidence))

    # ─── STAGE (基于趋势 + 持续天数) ───
    if distinct_days <= 2 and total_appearances <= 3:
        stage = "early"
    elif distinct_days >= 15 and growth_component <= 0.3:
        stage = "mature"
    elif growth_component >= 0.7 and total_appearances >= 5:
        stage = "breaking"
    else:
        stage = "forming"

    # ─── OPPORTUNITY = (Market × 0.6 + Business × 0.4) × (100 - Competition) / 100 ───
    base_opportunity = market_score * 0.6 + business_score * 0.4
    opportunity_index = round(base_opportunity * (100 - competition) / 100)
    opportunity_index = max(1, min(100, opportunity_index))

    # 子分数显示 (0-10)
    pain_display = round(pain_score * 10)
    pay_display = round(pay_score * 10)
    trend_display = round(trend_component * 10)
    growth_display = round(growth_component * 10)

    return {
        "market_score": market_score,
        "business_score": business_score,
        "competition": competition,
        "confidence": confidence,
        "stage": stage,
        "opportunity_index": opportunity_index,
        # 子维度显示
        "trend_score": trend_display,
        "growth_score": growth_display,
        "consistency_score": round(consistency_component * 10),
        "pain_score": pain_display,
        "pay_score": pay_display,
        "pain_frequency": pain_freq,
        "pain_severity": pain_sev,
        "pay_budget": pay_budget,
        "pay_urgency": pay_urgency,
        "total_appearances": total_appearances,
        "distinct_days": distinct_days,
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

        # 检查是否都在上升 (growth_score >= 6 表示增长趋势)
        a_growing = sa["growth_score"] >= 6
        b_growing = sb["growth_score"] >= 6

        if a_growing and b_growing:
            # 找类别名称
            name_a = next((c["name"] for c in categories if c["id"] == id_a), id_a)
            name_b = next((c["name"] for c in categories if c["id"] == id_b), id_b)

            cross_score = round((sa["opportunity_index"] + sb["opportunity_index"]) / 20)  # 0-100 avg → 0-10
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
        "market_score": 0,
        "business_score": 0,
        "competition": 0,
        "confidence": 0,
        "stage": "early",
        "opportunity_index": 0,
        "trend_score": 0,
        "growth_score": 0,
        "consistency_score": 0,
        "pain_score": 0,
        "pay_score": 0,
        "pain_frequency": 0,
        "pain_severity": 0,
        "pay_budget": 0,
        "pay_urgency": 0,
        "total_appearances": 0,
        "distinct_days": 0,
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
    # 所有需求类别的总信号数 和 最大出现次数（用于归一化）
    total_demand_signals = sum(
        sum(counts.values()) for counts in weekly_counts.values()
    )
    max_appearances = max(
        (sum(counts.values()) for counts in weekly_counts.values()), default=1
    )
    max_distinct_days = max(
        (len([w for w in counts if counts[w] > 0]) for counts in weekly_counts.values()), default=1
    )
    scores: dict[str, dict] = {}
    for cat in categories:
        cat_id = cat["id"]
        counts = weekly_counts[cat_id]
        scores[cat_id] = _score_demand(cat, counts, total_demand_signals, max_appearances, max_distinct_days)

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
            # V3: Market/Business 分离
            "market_score": score["market_score"],
            "business_score": score["business_score"],
            "competition": score["competition"],
            "confidence": score["confidence"],
            "stage": score["stage"],
            "target_buyer": cat.get("target_buyer", ""),
            "opportunity_index": score["opportunity_index"],
            # 子维度
            "trend_score": score["trend_score"],
            "growth_score": score["growth_score"],
            "consistency_score": score["consistency_score"],
            "pain_score": score["pain_score"],
            "pay_score": score["pay_score"],
            "pain_frequency": score["pain_frequency"],
            "pain_severity": score["pain_severity"],
            "pay_budget": score["pay_budget"],
            "pay_urgency": score["pay_urgency"],
            "total_appearances": score["total_appearances"],
            "distinct_days": score["distinct_days"],
        })

    # ─── 按机会指数排序 ───
    demand_entries.sort(key=lambda d: d["opportunity_index"], reverse=True)

    # ─── 构建输出 ───
    output = {
        "_schema": "需求雷达 v3.0 — Market/Business 分离 + Confidence + Stage",
        "_version": "3.0",
        "_formula": "Market=(Trend×0.5+Growth×0.3+Consistency×0.2)×100, Business=(Pain×0.5+Pay×0.5)×100, Opportunity=Market×0.6+Business×0.4, Confidence=log2(n+1)×20",
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
    stage_icons = {"early": "[EARLY]", "forming": "[FORM]", "breaking": "[BREAK]", "mature": "[MATURE]"}
    print(f"\n[需求雷达 V3] Market/Business 分离评分 (0-100):")
    for i, d in enumerate(demand_entries[:8]):
        si = stage_icons.get(d["stage"], "?")
        print(f"  {i+1}. [{d['opportunity_index']}/100] {si} {d['name']}")
        print(f"       Market:{d['market_score']} | Business:{d['business_score']} | Competition:{d['competition']} | 置信:{d['confidence']}% | {d['target_buyer']}")

    if intersections:
        print(f"\n[需求雷达] 交叉机会 ({len(intersections)}):")
        for x in intersections[:5]:
            print(f"  [{x['cross_score']}/10] {x['label']}")

    print(f"\n[需求雷达] 结果已保存 → {output_path}")
    return output


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    run(today)
