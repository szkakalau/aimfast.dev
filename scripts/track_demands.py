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


def _score_demand(category: dict, weekly_counts: dict[str, int], total_demand_signals: int, max_appearances: int) -> dict:
    """计算单个需求类别的机会评分。

    V2 公式（三级评分）:
      PainScore  = (frequency × severity) / 10          → 0-10
      PayScore   = (budget × urgency) / 10              → 0-10
      TrendScore = appearances / max_appearances × 10   → 0-10 (归一化到最强需求)
      GrowthModifier = 1.2(rising) / 1.0(stable) / 0.8(falling)
      Opportunity = (0.35×Trend + 0.35×Pain + 0.30×Pay) × GrowthModifier
      最终: 归一化到 0-100
    """
    sorted_weeks = sorted(weekly_counts.keys())
    if not sorted_weeks:
        return _empty_score()

    # ─── 从配置读取 V2 结构 ───
    pain_cfg = category.get("pain", {})
    pay_cfg = category.get("pay", {})
    weights_cfg = json.loads(
        (CONFIG_DIR / "demand_patterns.json").read_text(encoding="utf-8")
    ).get("weights", {"trend": 0.35, "pain": 0.35, "pay": 0.30})

    # 1. Pain Score = frequency × severity / 10 (0-100 → 0-10)
    pain_freq = pain_cfg.get("frequency", 5)
    pain_sev = pain_cfg.get("severity", 5)
    pain_score = (pain_freq * pain_sev) / 10  # 0-10

    # 2. Pay Score = budget × urgency / 10 (0-100 → 0-10)
    pay_budget = pay_cfg.get("budget", 5)
    pay_urgency = pay_cfg.get("urgency", 5)
    pay_score = (pay_budget * pay_urgency) / 10  # 0-10

    # 3. Trend Score = appearances / max_appearances × 10 (归一化)
    total_appearances = sum(weekly_counts.values())
    if max_appearances > 0:
        trend_score = (total_appearances / max_appearances) * 10  # 0-10
    else:
        trend_score = 0

    # 4. Growth Modifier
    recent_weeks = sorted_weeks[-2:] if len(sorted_weeks) >= 2 else sorted_weeks
    earlier_weeks = sorted_weeks[:-2] if len(sorted_weeks) > 2 else []

    recent_avg = sum(weekly_counts[w] for w in recent_weeks) / len(recent_weeks)
    if earlier_weeks:
        earlier_avg = sum(weekly_counts[w] for w in earlier_weeks) / len(earlier_weeks)
    else:
        earlier_avg = 0

    if earlier_avg > 0:
        growth_ratio = recent_avg / earlier_avg
        if growth_ratio >= 1.2:
            growth_modifier = 1.2
        elif growth_ratio >= 1.0:
            growth_modifier = 1.0
        elif growth_ratio >= 0.7:
            growth_modifier = 0.9
        else:
            growth_modifier = 0.8
    elif recent_avg > 0 and earlier_avg == 0:
        growth_modifier = 1.1  # 新需求，略高于中性
    else:
        growth_modifier = 1.0

    # 5. 加权求和 → 0-100
    w_trend = weights_cfg.get("trend", 0.35)
    w_pain = weights_cfg.get("pain", 0.35)
    w_pay = weights_cfg.get("pay", 0.30)

    raw = (w_trend * trend_score + w_pain * pain_score + w_pay * pay_score) * growth_modifier
    opportunity_index = round(raw * 10)  # 0-10 scale × 10 → 0-100
    opportunity_index = max(1, min(100, opportunity_index))

    # 用于显示的子分数 (0-10)
    trend_display = min(10, round(trend_score))
    pain_display = min(10, round(pain_score))
    pay_display = min(10, round(pay_score))

    return {
        "trend_score": trend_display,
        "pain_score": pain_display,
        "pay_score": pay_display,
        "growth_modifier": round(growth_modifier, 2),
        "opportunity_index": opportunity_index,
        # 保留子维度供 dashboard 展示
        "pain_frequency": pain_freq,
        "pain_severity": pain_sev,
        "pay_budget": pay_budget,
        "pay_urgency": pay_urgency,
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

        # 检查是否都在上升 (growth_modifier >= 1.1 表示有增长)
        a_growing = sa["growth_modifier"] >= 1.1
        b_growing = sb["growth_modifier"] >= 1.1

        if a_growing and b_growing:
            # 找类别名称
            name_a = next((c["name"] for c in categories if c["id"] == id_a), id_a)
            name_b = next((c["name"] for c in categories if c["id"] == id_b), id_b)

            cross_score = round((sa["opportunity_index"] + sb["opportunity_index"]) / 20)  # 0-100 → 0-10
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
    # 所有需求类别的总信号数 和 最大出现次数（用于归一化）
    total_demand_signals = sum(
        sum(counts.values()) for counts in weekly_counts.values()
    )
    max_appearances = max(
        (sum(counts.values()) for counts in weekly_counts.values()), default=1
    )
    scores: dict[str, dict] = {}
    for cat in categories:
        cat_id = cat["id"]
        counts = weekly_counts[cat_id]
        scores[cat_id] = _score_demand(cat, counts, total_demand_signals, max_appearances)

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
            # V2: 三级评分
            "trend_score": score["trend_score"],
            "pain_score": score["pain_score"],
            "pay_score": score["pay_score"],
            "growth_modifier": score["growth_modifier"],
            "opportunity_index": score["opportunity_index"],
            # 子维度
            "pain_frequency": score["pain_frequency"],
            "pain_severity": score["pain_severity"],
            "pay_budget": score["pay_budget"],
            "pay_urgency": score["pay_urgency"],
        })

    # ─── 按机会指数排序 ───
    demand_entries.sort(key=lambda d: d["opportunity_index"], reverse=True)

    # ─── 构建输出 ───
    output = {
        "_schema": "需求雷达 v2.0 — 三级评分：Trend(35%) + Pain(35%) + Pay(30%) × Growth",
        "_version": "2.0",
        "_formula": "Pain=(freq×sev)/10, Pay=(budget×urgency)/10, Trend=appearances/max×10, Growth=1.2/1.0/0.8, Final=weighted_sum×10→0-100",
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
    print(f"\n[需求雷达] 机会评分 Top 8 (0-100):")
    trend_icons = {"rising": "[UP]", "stable": "[--]", "falling": "[DN]", "new": "[NEW]"}
    for i, d in enumerate(demand_entries[:8]):
        icon = trend_icons.get(d["delta"], "?")
        print(f"  {i+1}. [{d['opportunity_index']}/100] {icon} {d['name']}")
        print(f"       Trend:{d['trend_score']} | Pain:{d['pain_score']}(f:{d['pain_frequency']}×s:{d['pain_severity']}) | Pay:{d['pay_score']}(b:{d['pay_budget']}×u:{d['pay_urgency']}) | Growth:×{d['growth_modifier']}")

    if intersections:
        print(f"\n[需求雷达] 交叉机会 ({len(intersections)}):")
        for x in intersections[:5]:
            print(f"  [{x['cross_score']}/10] {x['label']}")

    print(f"\n[需求雷达] 结果已保存 → {output_path}")
    return output


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    run(today)
