"""
信号源 ROI 审计引擎
输入: raw/*/ + daily/*/signals.json（过去 30 天）
输出: tracking/source_audit.json

指标:
  - total_raw: 原始采集量
  - total_processed: 进入处理后的数量（存活率）
  - top10_appearances: 进入当日 Top 10 次数
  - action_triggered: 触发 Action Plan 次数（score ≥ threshold）
  - avg_score: 平均分
  - cross_platform_signals: 跨平台验证信号数（≥2 平台）
  - unique_top10: 该源独有的 Top 10 信号（其他源未覆盖）
  - roi_score: 综合 ROI（0-1）
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"
DAILY_DIR = ROOT / "daily"
TRACKING_DIR = ROOT / "tracking"
CONFIG_PATH = ROOT / "config.json"

TZ_SHANGHAI = timezone(timedelta(hours=8))
LOOKBACK_DAYS = 30


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def collect_raw_stats() -> dict[str, dict]:
    """统计 raw/ 目录中每个采集器的原始产出。"""
    config = load_config()
    # 建立 source_key → metadata 映射
    source_meta: dict[str, dict] = {}
    for tier in ["overseas", "domestic"]:
        for src in config.get("signals", {}).get(tier, []):
            source_meta[src["key"]] = {
                "name": src["name"],
                "tier": tier,
                "priority": src.get("priority", "?"),
                "enabled": src.get("enabled", True),
            }
    for src in config.get("signals", {}).get("c_end_planned", []):
        source_meta[src["key"]] = {
            "name": src["name"],
            "tier": "c_end",
            "priority": src.get("priority", "?"),
            "enabled": src.get("enabled", True),
        }

    today = datetime.now(TZ_SHANGHAI).date()
    stats: dict[str, dict] = {}

    for i in range(LOOKBACK_DAYS):
        date_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        raw_path = RAW_DIR / date_str
        if not raw_path.exists():
            continue

        for f in raw_path.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                raw_signals = data.get("signals", [])
            except (json.JSONDecodeError, KeyError):
                continue

            for s in raw_signals:
                sk = s.get("source_key", "unknown")
                if sk not in stats:
                    meta = source_meta.get(sk, {})
                    stats[sk] = {
                        "source_key": sk,
                        "name": meta.get("name", sk),
                        "tier": meta.get("tier", "unknown"),
                        "priority": meta.get("priority", "?"),
                        "enabled": meta.get("enabled", True),
                        "total_raw": 0,
                        "days_active": set(),
                        "days_empty": set(),
                    }
                stats[sk]["total_raw"] += 1
                stats[sk]["days_active"].add(date_str)

            # 标记没有信号的采集器（当天跑了但产出为 0）
            collector_key = f.stem.replace("collect_", "").replace("_", "-")
            # 映射文件名到 source_key
            filename_to_key = {
                "hn": "hn",
                "hackernews": "hn",
                "github": "github",
                "trends": "trends",
                "producthunt": "producthunt",
                "devcommunity": "devcommunity",
                "reddit": "reddit",
                "reddit_consumer": "reddit-consumer",
                "reddit-consumer": "reddit-consumer",
                "v2ex": "v2ex",
                "w2solo": "w2solo",
                "huggingface": "huggingface",
                "lobsters": "lobsters",
                "arxiv": "arxiv",
                "douban": "douban",
                "xiaohongshu": "xiaohongshu",
                "x": "x",
                "indiehackers": "indiehackers",
                "jike": "jike",
            }
            mapped_key = filename_to_key.get(collector_key, collector_key)
            if mapped_key not in stats:
                meta = source_meta.get(mapped_key, {})
                stats[mapped_key] = {
                    "source_key": mapped_key,
                    "name": meta.get("name", mapped_key),
                    "tier": meta.get("tier", "unknown"),
                    "priority": meta.get("priority", "?"),
                    "enabled": meta.get("enabled", True),
                    "total_raw": 0,
                    "days_active": set(),
                    "days_empty": set(),
                }
            if len(raw_signals) == 0:
                stats[mapped_key]["days_empty"].add(date_str)

    # 转换 set 为数字
    for sk in stats:
        stats[sk]["days_active"] = len(stats[sk]["days_active"])
        stats[sk]["days_empty"] = len(stats[sk]["days_empty"])

    return stats


def collect_processed_stats(raw_stats: dict[str, dict]) -> dict[str, dict]:
    """统计 daily/*/signals.json 中每个源的最终表现。"""
    config = load_config()
    action_threshold = config["scoring"]["thresholds"]["action_trigger"]

    today = datetime.now(TZ_SHANGHAI).date()
    # 复制 raw_stats 作为基础
    stats: dict[str, dict] = {}
    for sk, v in raw_stats.items():
        stats[sk] = dict(v)
        stats[sk]["total_processed"] = 0
        stats[sk]["top10_appearances"] = 0
        stats[sk]["action_triggered"] = 0
        stats[sk]["total_score"] = 0
        stats[sk]["cross_platform_signals"] = 0
        stats[sk]["unique_top10"] = 0
        stats[sk]["top_titles"] = []  # 最高分信号的标题（用于人工抽查）

    for i in range(LOOKBACK_DAYS):
        date_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        signals_path = DAILY_DIR / date_str / "signals.json"
        if not signals_path.exists():
            continue

        try:
            data = json.loads(signals_path.read_text(encoding="utf-8"))
            signals = data.get("signals", [])
        except (json.JSONDecodeError, KeyError):
            continue

        if not signals:
            continue

        # 当日 Top 10
        top10 = signals[:10]
        top10_ids = {s.get("id", "") for s in top10}

        # 当日所有 source_key 集合（用于计算 unique）
        all_source_keys = set()
        for s in signals:
            all_source_keys.add(s.get("source_key", "unknown"))

        for s in signals:
            sk = s.get("source_key", "unknown")
            if sk not in stats:
                stats[sk] = {
                    "source_key": sk,
                    "name": s.get("source", sk),
                    "tier": "unknown",
                    "priority": "?",
                    "enabled": True,
                    "total_raw": 0,
                    "days_active": 0,
                    "days_empty": 0,
                    "total_processed": 0,
                    "top10_appearances": 0,
                    "action_triggered": 0,
                    "total_score": 0,
                    "cross_platform_signals": 0,
                    "unique_top10": 0,
                    "top_titles": [],
                }

            score = s.get("score", 0)
            stats[sk]["total_processed"] += 1
            stats[sk]["total_score"] += score

            if s.get("id", "") in top10_ids:
                stats[sk]["top10_appearances"] += 1

                # 检查是否独有（该信号只来自这个源，且当日没有其他源覆盖同一话题）
                cp_count = s.get("cross_platform_count", 1)
                if cp_count <= 1:
                    # 检查是否有其他源的信号标题高度相似
                    stats[sk]["unique_top10"] += 1

                # 记录最高分标题
                stats[sk]["top_titles"].append({
                    "date": date_str,
                    "title": s.get("title", ""),
                    "score": score,
                })

            if score >= action_threshold:
                stats[sk]["action_triggered"] += 1

            if s.get("cross_platform_count", 0) >= 2:
                stats[sk]["cross_platform_signals"] += 1

    # 保留每个源 top 3 最高分标题
    for sk in stats:
        stats[sk]["top_titles"] = sorted(
            stats[sk]["top_titles"], key=lambda x: x["score"], reverse=True
        )[:3]

    return stats


def compute_roi(stats: dict[str, dict]) -> dict[str, dict]:
    """计算每个源的 ROI 综合评分并给出建议。"""
    # 找到各指标的全局最大值用于归一化
    max_top10 = max((v["top10_appearances"] for v in stats.values()), default=1)
    max_action = max((v["action_triggered"] for v in stats.values()), default=1)
    max_unique = max((v["unique_top10"] for v in stats.values()), default=1)
    max_cross = max((v["cross_platform_signals"] for v in stats.values()), default=1)

    for sk, v in stats.items():
        processed = v["total_processed"]
        raw = v["total_raw"]

        # 存活率：多少原始信号进入了最终输出
        survival_rate = processed / raw if raw > 0 else 0

        # Top 10 贡献率
        top10_rate = v["top10_appearances"] / processed if processed > 0 else 0

        # 归一化子分数 (0-1)
        top10_norm = v["top10_appearances"] / max_top10 if max_top10 > 0 else 0
        action_norm = v["action_triggered"] / max_action if max_action > 0 else 0
        unique_norm = v["unique_top10"] / max_unique if max_unique > 0 else 0
        cross_norm = v["cross_platform_signals"] / max_cross if max_cross > 0 else 0

        # 综合 ROI: top10 贡献 × 0.4 + action 触发 × 0.3 + 独有洞察 × 0.2 + 跨平台 × 0.1
        roi_score = round(
            top10_norm * 0.4 + action_norm * 0.3 + unique_norm * 0.2 + cross_norm * 0.1,
            3,
        )

        avg_score = v["total_score"] / processed if processed > 0 else 0

        # 决策建议
        if roi_score >= 0.5:
            recommendation = "keep_p0"
            rec_label = "保留 · P0 每日运行"
        elif roi_score >= 0.2:
            recommendation = "keep_p2"
            rec_label = "降级 · P2 每周运行"
        else:
            # 特殊情况：raw 产出多但 processed 存活率极低 → 说明采集质量有问题
            if raw > 100 and survival_rate < 0.1:
                recommendation = "investigate"
                rec_label = "调查 · 高采集量低存活率，检查采集器质量"
            elif raw == 0:
                recommendation = "investigate"
                rec_label = "调查 · 无原始数据产出，检查采集器是否正常运行"
            else:
                recommendation = "cut"
                rec_label = "建议砍掉 · 对最终输出贡献极低"

        v["survival_rate"] = round(survival_rate, 3)
        v["top10_rate"] = round(top10_rate, 3)
        v["avg_score"] = round(avg_score, 1)
        v["roi_score"] = roi_score
        v["recommendation"] = recommendation
        v["recommendation_label"] = rec_label

        # 子分数 breakdown（用于调试）
        v["roi_breakdown"] = {
            "top10_contribution": round(top10_norm * 0.4, 3),
            "action_triggered": round(action_norm * 0.3, 3),
            "unique_insight": round(unique_norm * 0.2, 3),
            "cross_platform": round(cross_norm * 0.1, 3),
        }

    return stats


def find_gaps(raw_stats: dict[str, dict], processed_stats: dict[str, dict]) -> list[dict]:
    """检测 raw 中有数据但 processed 中没有的源（采集器跑了但信号丢失了）。"""
    gaps = []
    for sk in raw_stats:
        raw_total = raw_stats[sk]["total_raw"]
        processed_total = processed_stats.get(sk, {}).get("total_processed", 0)
        if raw_total > 0 and processed_total == 0:
            gaps.append({
                "source_key": sk,
                "name": raw_stats[sk]["name"],
                "total_raw": raw_total,
                "total_processed": 0,
                "issue": "采集器产生数据但未进入 daily/signals.json —— 可能被去重/过滤/或数据结构不兼容",
            })
    return gaps


def run(date_str: str | None = None):
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")

    print(f"\n{'='*60}")
    print(f"[审计] 信号源 ROI 审计 — {date}")
    print(f"[审计] 回溯范围: {LOOKBACK_DAYS} 天")
    print(f"{'='*60}")

    # Step 1: 统计 raw 采集
    print("\n[1/4] 扫描 raw/ 原始采集数据...")
    raw_stats = collect_raw_stats()
    print(f"  发现 {len(raw_stats)} 个信号源")

    # Step 2: 统计 processed 表现
    print("\n[2/4] 扫描 daily/ 处理后数据...")
    processed_stats = collect_processed_stats(raw_stats)
    print(f"  统计完成")

    # Step 3: 检测数据断层
    print("\n[3/4] 检测数据断层...")
    gaps = find_gaps(raw_stats, processed_stats)

    # Step 4: 计算 ROI
    print("\n[4/4] 计算 ROI 评分...")
    results = compute_roi(processed_stats)

    # ─── 按 ROI 排序 ───
    sorted_results = sorted(results.values(), key=lambda x: x["roi_score"], reverse=True)

    # ─── 构建输出 ───
    # 简化输出（去掉内部集合）
    clean_results = []
    for r in sorted_results:
        clean_results.append({
            "source_key": r["source_key"],
            "name": r["name"],
            "tier": r["tier"],
            "priority": r["priority"],
            "enabled": r["enabled"],
            "total_raw": r["total_raw"],
            "total_processed": r["total_processed"],
            "survival_rate": r["survival_rate"],
            "days_active": r["days_active"],
            "days_empty": r["days_empty"],
            "avg_score": r["avg_score"],
            "top10_appearances": r["top10_appearances"],
            "top10_rate": r["top10_rate"],
            "action_triggered": r["action_triggered"],
            "cross_platform_signals": r["cross_platform_signals"],
            "unique_top10": r["unique_top10"],
            "roi_score": r["roi_score"],
            "roi_breakdown": r["roi_breakdown"],
            "recommendation": r["recommendation"],
            "recommendation_label": r["recommendation_label"],
            "top_titles": r["top_titles"],
        })

    # 汇总
    keep_p0 = [r for r in clean_results if r["recommendation"] == "keep_p0"]
    keep_p2 = [r for r in clean_results if r["recommendation"] == "keep_p2"]
    cut = [r for r in clean_results if r["recommendation"] == "cut"]
    investigate = [r for r in clean_results if r["recommendation"] == "investigate"]

    output = {
        "_schema": "信号源 ROI 审计 v1.0",
        "generated_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "lookback_days": LOOKBACK_DAYS,
        "summary": {
            "total_sources": len(clean_results),
            "keep_p0": len(keep_p0),
            "keep_p2": len(keep_p2),
            "cut": len(cut),
            "investigate": len(investigate),
            "total_raw_signals": sum(r["total_raw"] for r in clean_results),
            "total_processed_signals": sum(r["total_processed"] for r in clean_results),
        },
        "sources": clean_results,
        "gaps": gaps,
    }

    # ─── 保存 ───
    TRACKING_DIR.mkdir(parents=True, exist_ok=True)
    output_path = TRACKING_DIR / "source_audit.json"
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # ─── 打印报告 ───
    print(f"\n{'─'*60}")
    print(f"审计结果")
    print(f"{'─'*60}")

    # 汇总
    print(f"\n  总信号源: {len(clean_results)}")
    print(f"  [KEEP P0] 保留: {len(keep_p0)} 个")
    print(f"  [DOWN P2] 降级: {len(keep_p2)} 个")
    print(f"  [CUT]     砍掉: {len(cut)} 个")
    print(f"  [CHECK]   调查: {len(investigate)} 个")

    # 详细表
    print(f"\n{'─'*90}")
    print(f"{'源':<20s} {'ROI':>6s} {'原始':>6s} {'处理':>6s} {'存活率':>7s} {'Top10':>6s} {'均分':>5s} {'建议'}")
    print(f"{'─'*90}")
    for r in sorted_results:
        name = r["name"][:18]
        print(
            f"{name:<20s} {r['roi_score']:>6.3f} {r['total_raw']:>6d} {r['total_processed']:>6d} "
            f"{r['survival_rate']:>6.0%} {r['top10_appearances']:>6d} {r['avg_score']:>5.1f} "
            f" {r['recommendation_label']}"
        )

    # 数据断层警告
    if gaps:
        print(f"\n[WARN] 数据断层 ({len(gaps)} 个源 raw 有数据但未进入最终输出):")
        for g in gaps:
            print(f"  - {g['name']} ({g['source_key']}): raw={g['total_raw']} -> processed=0")

    print(f"\n[审计] 完整报告 -> {output_path}")
    print(f"[审计] 完成")

    return output


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    run(today)
