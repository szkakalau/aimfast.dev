"""
Builder Workbench 数据更新器
读取需求雷达 + 关注列表，生成工作台周报。
输出: tracking/workbench_report.json
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACKING_DIR = ROOT / "tracking"

TZ_SHANGHAI = timezone(timedelta(hours=8))


def run(date_str: str | None = None) -> dict:
    """生成工作台报告数据。"""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    print(f"\n{'='*50}")
    print(f"[Workbench] Builder Workbench 数据更新 — {date}")
    print(f"{'='*50}")

    # ─── 加载数据 ───
    radar_path = TRACKING_DIR / "demand_radar.json"
    if not radar_path.exists():
        print("[Workbench] demand_radar.json 不存在，请先运行 track_demands.py")
        return {}
    radar = json.loads(radar_path.read_text(encoding="utf-8"))

    watchlist_path = TRACKING_DIR / "watchlist.json"
    watched_ids = []
    if watchlist_path.exists():
        watchlist = json.loads(watchlist_path.read_text(encoding="utf-8"))
        watched_ids = watchlist.get("watched", [])

    # ─── 提取关注需求的数据 ───
    demands = {d["id"]: d for d in radar.get("demands", [])}
    watched_demands = []

    for did in watched_ids:
        if did not in demands:
            continue
        d = demands[did]

        # 计算周变化（最近两周的差值）
        snaps = d.get("snapshots", {})
        sorted_weeks = sorted(snaps.keys())
        if len(sorted_weeks) >= 2:
            this_week = snaps.get(sorted_weeks[-1], 0)
            last_week = snaps.get(sorted_weeks[-2], 0)
            if last_week > 0:
                change_pct = round((this_week - last_week) / last_week * 100)
            elif this_week > 0:
                change_pct = 100  # 新出现
            else:
                change_pct = 0
        else:
            change_pct = 0

        # 生成建议
        stage = d.get("stage", "forming")
        competition = d.get("competition", 50)
        market = d.get("market_score", 0)
        business = d.get("business_score", 0)

        if stage == "forming" and competition < 40 and business >= 50:
            recommendation = "prepare_validate"
            rec_text = "建议准备验证 — 形成期 + 低竞争 + 高商业价值"
        elif stage == "breaking" and competition < 50:
            recommendation = "observe_closely"
            rec_text = "密切关注 — 爆发期但竞争尚可控"
        elif competition >= 80:
            recommendation = "avoid"
            rec_text = "竞争过热，不建议独立开发者进入"
        elif business < 30:
            recommendation = "low_priority"
            rec_text = "商业价值偏低，优先级放后"
        else:
            recommendation = "watch"
            rec_text = "持续观察，等待更好时机"

        watched_demands.append({
            "id": did,
            "name": d.get("name", did),
            "name_en": d.get("name_en", d.get("name", did)),
            "market_score": market,
            "business_score": business,
            "competition": competition,
            "stage": stage,
            "opportunity_index": d.get("opportunity_index", 0),
            "confidence": d.get("confidence", 0),
            "change_pct": change_pct,
            "delta": d.get("delta", "stable"),
            "recommendation": recommendation,
            "recommendation_text": rec_text,
            "target_buyer": d.get("target_buyer", ""),
            "snapshots": snaps,
        })

    # 按机会指数排序
    watched_demands.sort(key=lambda d: d["opportunity_index"], reverse=True)

    # 生成周报摘要 (中英双语)
    stage_names_zh = {"early": "萌芽期", "forming": "形成期", "breaking": "爆发期", "mature": "成熟期"}
    stage_names_en = {"early": "Early", "forming": "Forming", "breaking": "Breaking", "mature": "Mature"}

    if watched_demands:
        rising = [d for d in watched_demands if d["change_pct"] > 0]
        if rising:
            top_rising = max(rising, key=lambda d: d["change_pct"])
            nm_zh = top_rising['name']
            nm_en = top_rising.get('name_en', nm_zh)
            stg = top_rising['stage']
            pct = top_rising['change_pct']
            weekly_insight = f"关注重点: {nm_zh} 本周上升 {pct}%，处于{stage_names_zh.get(stg, stg)}阶段"
            weekly_insight_en = f"Focus: {nm_en} rose {pct}% this week, in {stage_names_en.get(stg, stg)} stage"
        else:
            weekly_insight = "本周关注需求无明显上升，继续观察现有趋势"
            weekly_insight_en = "No significant upward movement in watched demands. Continue observing."
    else:
        weekly_insight = "尚未设置关注列表"
        weekly_insight_en = "No watchlist configured yet."

    # ─── 构建输出 ───
    output = {
        "_schema": "Builder Workbench 报告",
        "_version": "1.0",
        "generated_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "date": date,
        "watched_demands": watched_demands,
        "weekly_insight": weekly_insight,
        "weekly_insight_en": weekly_insight_en,
        "all_demands": radar.get("demands", []),
        "intersections": radar.get("intersections", []),
    }

    output_path = TRACKING_DIR / "workbench_report.json"
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"[Workbench] 关注 {len(watched_demands)} 个需求")
    for d in watched_demands:
        arrow = "[UP]" if d["change_pct"] > 0 else ("[DN]" if d["change_pct"] < 0 else "[--]")
        print(f"  {arrow} {d['name']}: {d['change_pct']:+d}% | [{d['recommendation']}] {d['recommendation_text'][:40]}")
    print(f"[Workbench] 周报: {weekly_insight}")
    print(f"[Workbench] 结果已保存 → {output_path}")
    return output


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    run(today)
