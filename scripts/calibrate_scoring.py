"""
评分校准引擎
负责: 每日记录预测 → 每周回溯验证 → 自动调整评分参数

流程:
  每日: log_predictions() → 将当日 top 推荐写入 predictions.json
  每周日: calibrate() → 分析失败模式 → 调整 config.json 权重/阈值

保守策略:
  - 单次调整幅度上限: action_trigger ±2, weight ±0.5
  - 需连续 2 周同方向才生效（防单周噪音）
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAILY_DIR = ROOT / "daily"
TRACKING_DIR = ROOT / "tracking"
CONFIG_PATH = ROOT / "config.json"

TZ_SHANGHAI = timezone(timedelta(hours=8))
LOOKBACK_DAYS = 7


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print(f"[校准] config.json 已更新")


def load_predictions() -> dict:
    path = TRACKING_DIR / "predictions.json"
    if not path.exists():
        return {"predictions": [], "calibration_history": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save_predictions(data: dict):
    TRACKING_DIR.mkdir(parents=True, exist_ok=True)
    path = TRACKING_DIR / "predictions.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ─── 每日预测记录 ───────────────────────────────────

def log_predictions(date_str: str | None = None):
    """
    将当日 Top 信号中触发 Action Plan 的写入 predictions.json。
    应在 process_signals 完成后调用。
    """
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    signals_path = DAILY_DIR / date / "signals.json"
    if not signals_path.exists():
        print(f"[预测] {date} 无 signals.json，跳过")
        return

    config = load_config()
    action_threshold = config["scoring"]["thresholds"]["action_trigger"]

    signals_data = json.loads(signals_path.read_text(encoding="utf-8"))
    signals = signals_data.get("signals", [])

    # 选取触发了 Action 且排名 top 5 的信号
    action_signals = [
        s for s in signals
        if s.get("score", 0) >= action_threshold
    ][:5]

    if not action_signals:
        print(f"[预测] {date} 无信号触发 Action（阈值 {action_threshold}），跳过")
        return

    data = load_predictions()

    # 检查是否已记录（防重复）
    existing_ids = {p.get("signal_id") for p in data["predictions"] if p.get("date") == date}
    new_count = 0

    for s in action_signals:
        sid = s.get("id", "")
        if sid in existing_ids:
            continue

        data["predictions"].append({
            "date": date,
            "signal_id": sid,
            "title": s.get("title", ""),
            "score": s.get("score", 0),
            "score_breakdown": s.get("score_breakdown", {}),
            "cross_platform_count": s.get("cross_platform_count", 0),
            "action_triggered": True,
            "landing_page_url": "",
            "opportunity_id": "",
            "7day_verification": "pending",
            "7day_uv": 0,
            "7day_signups": 0,
            "calibration_applied": False,
        })
        new_count += 1

    if new_count > 0:
        save_predictions(data)
        print(f"[预测] 已记录 {new_count} 条新预测 ({date})")
    else:
        print(f"[预测] {date} 预测已存在，跳过 ({len(existing_ids)} 条)")


# ─── 每周校准 ───────────────────────────────────────

def _sync_verification_results(data: dict):
    """从 opportunities.json 同步验证结果到 predictions。"""
    opp_path = TRACKING_DIR / "opportunities.json"
    if not opp_path.exists():
        return False

    opportunities = json.loads(opp_path.read_text(encoding="utf-8")).get("opportunities", [])
    updated = False

    for pred in data["predictions"]:
        if pred.get("7day_verification") != "pending":
            continue

        # 按日期 + 标题模糊匹配
        pred_date = pred.get("date", "")
        pred_title = (pred.get("title", "") or "").lower()[:40]

        for op in opportunities:
            op_date = op.get("date", "")
            op_title = (op.get("opportunity", "") or "").lower()[:40]
            # 日期相近 + 标题相似 → 匹配
            if op_date and pred_date:
                try:
                    d1 = datetime.strptime(pred_date, "%Y-%m-%d").date()
                    d2 = datetime.strptime(op_date, "%Y-%m-%d").date()
                    days_diff = abs((d1 - d2).days)
                except ValueError:
                    days_diff = 999
            else:
                days_diff = 999

            if days_diff <= 3 and (pred_title in op_title or op_title in pred_title or pred_title[:20] == op_title[:20]):
                pred["opportunity_id"] = op.get("id", "")
                pred["landing_page_url"] = op.get("landing_page_url", "")
                pred["7day_uv"] = op.get("day7_uv", 0)
                pred["7day_signups"] = op.get("day7_signups", 0)

                vr = op.get("verification_result", "pending")
                if vr == "passed":
                    pred["7day_verification"] = "validated"
                elif vr == "failed":
                    pred["7day_verification"] = "false_positive"
                # 其他保持 pending

                updated = True
                break

    return updated


def calibrate(date_str: str | None = None):
    """
    每周校准: 分析过去 7 天的预测 → 验证结果 → 调整评分参数。

    仅在周日运行（或其他手动触发）。
    """
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    today = datetime.strptime(date, "%Y-%m-%d").date()

    print(f"\n{'='*60}")
    print(f"[校准] 评分校准引擎 — {date}")
    print(f"{'='*60}")

    data = load_predictions()
    predictions = data.get("predictions", [])

    # 筛选过去 7 天已出验证结果的预测
    recent_cutoff = today - timedelta(days=LOOKBACK_DAYS)
    evaluable = []
    for p in predictions:
        try:
            p_date = datetime.strptime(p["date"], "%Y-%m-%d").date()
        except (ValueError, KeyError):
            continue
        if p_date < recent_cutoff:
            continue
        evaluable.append(p)

    if not evaluable:
        print(f"[校准] 过去 {LOOKBACK_DAYS} 天内无可评估的预测")
        return _write_empty_report(date)

    # 同步验证结果
    updated = _sync_verification_results(data)
    if updated:
        save_predictions(data)
        # 重新加载以获取更新后的数据
        evaluable = [p for p in data["predictions"]
                     if (datetime.strptime(p["date"], "%Y-%m-%d").date() >= recent_cutoff
                         if p.get("date") else False)]

    # 统计
    validated = [p for p in evaluable if p.get("7day_verification") == "validated"]
    false_pos = [p for p in evaluable if p.get("7day_verification") == "false_positive"]
    pending = [p for p in evaluable if p.get("7day_verification") == "pending"]

    total_decided = len(validated) + len(false_pos)
    precision = len(validated) / total_decided if total_decided > 0 else None

    print(f"[校准] 过去 {LOOKBACK_DAYS} 天: {len(evaluable)} 条预测")
    print(f"  validated: {len(validated)} | false_positive: {len(false_pos)} | pending: {len(pending)}")
    if precision is not None:
        print(f"  precision: {precision:.1%}")

    # 如果没有足够的已决定样本，跳过调整
    if total_decided < 3:
        print(f"[校准] 已决定样本不足 ({total_decided} < 3)，跳过参数调整")
        return _write_report(date, precision, validated, false_pos, pending,
                           adjustments=[], note="样本不足，跳过调整")

    # ─── 维度偏差分析 ───
    # 对比 false_positive vs validated 在各维度的平均加权分
    dimension_keys = [
        "cross_platform", "volume", "freshness", "actionability",
        "buyer_clarity", "consumer_appeal", "problem_clarity",
    ]

    fp_avg = {}
    v_avg = {}
    for dim in dimension_keys:
        fp_scores = [
            p.get("score_breakdown", {}).get(dim, {}).get("weighted", 0)
            for p in false_pos
        ]
        v_scores = [
            p.get("score_breakdown", {}).get(dim, {}).get("weighted", 0)
            for p in validated
        ]
        fp_avg[dim] = sum(fp_scores) / len(fp_scores) if fp_scores else 0
        v_avg[dim] = sum(v_scores) / len(v_scores) if v_scores else 0

    # 找出 false_positive 中异常高的维度
    config = load_config()
    weights = config["scoring"]["weights"]
    adjustments = []

    for dim in dimension_keys:
        diff = fp_avg[dim] - v_avg[dim]
        current_weight = weights.get(dim, 2)

        # false_positive 的该维度显著高于 validated → 该维度可能过度加权
        if diff > 2.0 and current_weight > 0.5:
            new_weight = max(0.5, current_weight - 0.5)
            adjustments.append({
                "type": "weight_down",
                "dimension": dim,
                "reason": f"false_positive 平均 {fp_avg[dim]:.1f} vs validated {v_avg[dim]:.1f} (差 {diff:.1f})",
                "old_value": current_weight,
                "new_value": new_weight,
            })

        # validated 的该维度显著高于 false_positive → 该维度可能加权不足
        elif diff < -2.0 and current_weight < 4.0:
            new_weight = min(4.0, current_weight + 0.5)
            adjustments.append({
                "type": "weight_up",
                "dimension": dim,
                "reason": f"validated 平均 {v_avg[dim]:.1f} vs false_positive {fp_avg[dim]:.1f} (差 {abs(diff):.1f})",
                "old_value": current_weight,
                "new_value": new_weight,
            })

    # ─── 阈值调整 ───
    threshold_adjustment = None
    action_trigger = config["scoring"]["thresholds"]["action_trigger"]

    if precision is not None:
        if precision < 0.5 and len(false_pos) >= 3:
            new_threshold = min(25, action_trigger + 2)
            threshold_adjustment = {
                "type": "threshold_up",
                "reason": f"precision={precision:.1%} < 50%，提升阈值减少噪音",
                "old_value": action_trigger,
                "new_value": new_threshold,
            }
        elif precision > 0.8 and action_trigger > 12:
            new_threshold = max(10, action_trigger - 1)
            threshold_adjustment = {
                "type": "threshold_down",
                "reason": f"precision={precision:.1%} > 80%，降低阈值捕获更多机会",
                "old_value": action_trigger,
                "new_value": new_threshold,
            }

    # ─── 检查连续同方向（保守策略） ───
    history = data.get("calibration_history", [])
    applied_adjustments = []

    for adj in adjustments:
        # 检查上周是否有同方向调整
        same_direction = any(
            h.get("dimension") == adj["dimension"]
            and h.get("type") == adj["type"]
            for h in history[-2:]  # 最近 2 周
        )
        if same_direction or len(history) == 0:
            # 应用调整
            weights[adj["dimension"]] = adj["new_value"]
            adj["applied"] = True
            applied_adjustments.append(adj)
            print(f"[校准] 应用: {adj['dimension']} weight {adj['old_value']}→{adj['new_value']} ({adj['reason'][:60]})")
        else:
            adj["applied"] = False
            adj["reason"] += "（待连续 2 周同方向确认）"
            print(f"[校准] 待确认: {adj['dimension']} ({adj['reason'][:60]})")

    if threshold_adjustment:
        same_direction = any(
            h.get("type") == threshold_adjustment["type"]
            for h in history[-2:]
        )
        if same_direction or len(history) == 0:
            config["scoring"]["thresholds"]["action_trigger"] = threshold_adjustment["new_value"]
            threshold_adjustment["applied"] = True
            applied_adjustments.append(threshold_adjustment)
            print(f"[校准] 应用: action_trigger {threshold_adjustment['old_value']}→{threshold_adjustment['new_value']}")
        else:
            threshold_adjustment["applied"] = False
            threshold_adjustment["reason"] += "（待连续 2 周同方向确认）"
            print(f"[校准] 待确认: action_trigger ({threshold_adjustment['reason'][:60]})")

    # ─── 保存调整 ───
    if any(a.get("applied") for a in applied_adjustments):
        save_config(config)

    # ─── 记录校准历史 ───
    history.append({
        "date": date,
        "precision": precision,
        "total_decided": total_decided,
        "validated": len(validated),
        "false_positive": len(false_pos),
        "adjustments": [
            {k: v for k, v in a.items() if k != "reason"}
            for a in adjustments + ([threshold_adjustment] if threshold_adjustment else [])
        ],
        "applied_count": len(applied_adjustments),
    })
    data["calibration_history"] = history[-12:]  # 保留最近 12 周
    save_predictions(data)

    # ─── 写报告 ───
    _write_report(date, precision, validated, false_pos, pending,
                  adjustments + ([threshold_adjustment] if threshold_adjustment else []),
                  note=f"已应用 {len(applied_adjustments)} 项调整")

    print(f"\n[校准] 完成 — {len(applied_adjustments)} 项调整已应用")
    return data


def _write_report(date: str, precision, validated, false_pos, pending,
                  adjustments, note=""):
    """生成校准报告到 tracking/calibration_report.json"""
    report = {
        "date": date,
        "note": note,
        "stats": {
            "total_evaluated": len(validated) + len(false_pos) + len(pending),
            "validated": len(validated),
            "false_positive": len(false_pos),
            "pending": len(pending),
            "precision": round(precision, 3) if precision is not None else None,
        },
        "adjustments": [
            {
                "type": a.get("type"),
                "dimension": a.get("dimension"),
                "old_value": a.get("old_value"),
                "new_value": a.get("new_value"),
                "reason": a.get("reason", ""),
                "applied": a.get("applied", False),
            }
            for a in adjustments
        ],
        "false_positive_details": [
            {
                "title": p.get("title", ""),
                "score": p.get("score", 0),
                "cross_platform": p.get("cross_platform_count", 0),
                "breakdown": {
                    k: v.get("weighted", 0)
                    for k, v in p.get("score_breakdown", {}).items()
                },
            }
            for p in false_pos
        ],
    }

    path = TRACKING_DIR / "calibration_report.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[校准] 报告已保存 → {path}")


def _write_empty_report(date: str):
    _write_report(date, None, [], [], [], [], note="无足够数据进行校准")


# ─── CLI ───────────────────────────────────────────

if __name__ == "__main__":
    import sys

    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    is_sunday = datetime.now(TZ_SHANGHAI).weekday() == 6

    if len(sys.argv) > 1:
        mode = sys.argv[1]
    else:
        mode = "calibrate" if is_sunday else "log"

    if mode == "log":
        log_predictions(today)
    elif mode == "calibrate":
        calibrate(today)
    elif mode == "both":
        log_predictions(today)
        calibrate(today)
    else:
        print(f"用法: python -m scripts.calibrate_scoring [log|calibrate|both]")
        print(f"  默认: 周日运行 calibrate，其他日运行 log")
