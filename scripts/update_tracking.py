"""
追踪更新器
负责: 每日检查机会验证状态 + 经验库维护
输入: ./tracking/opportunities.json
输出: 更新后的 opportunities.json + lessons.json
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACKING_DIR = ROOT / "tracking"
CONFIG_PATH = ROOT / "config.json"

TZ_SHANGHAI = timezone(timedelta(hours=8))


def load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def find_due_opportunities() -> list[dict]:
    """查找到达验证期限（Day 7）且状态仍为 pending 的机会。"""
    path = TRACKING_DIR / "opportunities.json"
    if not path.exists():
        print(f"[追踪] {path} 不存在")
        return []

    data = json.loads(path.read_text(encoding="utf-8"))
    today = datetime.now(TZ_SHANGHAI).date()
    config = load_config()
    verification_days = config.get("landing_page", {}).get("verification_days", 7)

    due: list[dict] = []
    for op in data.get("opportunities", []):
        if op.get("verification_result") != "pending":
            continue
        try:
            op_date = datetime.strptime(op["date"], "%Y-%m-%d").date()
            days_elapsed = (today - op_date).days
            if days_elapsed >= verification_days:
                op["_days_elapsed"] = days_elapsed
                due.append(op)
        except (ValueError, KeyError):
            pass

    return due


def update_opportunities(updates: list[dict]) -> None:
    """批量更新 opportunities.json 中的状态。"""
    path = TRACKING_DIR / "opportunities.json"
    if not path.exists():
        return

    data = json.loads(path.read_text(encoding="utf-8"))
    updated = 0

    for op in data.get("opportunities", []):
        for upd in updates:
            if op.get("id") == upd.get("id"):
                op["verification_result"] = upd.get("verification_result", op.get("verification_result"))
                op["day7_decision"] = upd.get("day7_decision", op.get("day7_decision"))
                op["day7_uv"] = upd.get("day7_uv", op.get("day7_uv", 0))
                op["day7_signups"] = upd.get("day7_signups", op.get("day7_signups", 0))
                op["notes"] = upd.get("notes", op.get("notes", ""))
                op["current_status"] = upd.get("current_status", op.get("current_status"))
                updated += 1
                break

    if updated > 0:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[追踪] 已更新 {updated} 条机会")


def archive_to_lessons(opportunity: dict) -> str:
    """将失败的验证结果写入经验库。返回 lesson_id。"""
    path = TRACKING_DIR / "lessons.json"
    if not path.exists():
        print(f"[追踪] {path} 不存在")
        return ""

    data = json.loads(path.read_text(encoding="utf-8"))
    lesson_id = f"LN-{opportunity['date'].replace('-', '')}-{len(data['lessons']) + 1:03d}"

    failure_type = "signal_weak"
    decision = opportunity.get("day7_decision", "")
    if "fail" in str(decision).lower():
        if opportunity.get("day7_uv", 0) < 30:
            failure_type = "no_traffic"
        elif opportunity.get("day7_uv", 0) >= 30 and opportunity.get("day7_signups", 0) == 0:
            failure_type = "no_conversion"
    elif "adjust" in str(decision).lower():
        failure_type = "needs_pivot"

    lesson = {
        "id": lesson_id,
        "date": datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d"),
        "opportunity_id": opportunity.get("id", ""),
        "opportunity": opportunity.get("opportunity", ""),
        "signal_score": opportunity.get("score", 0),
        "failure_type": failure_type,
        "cause": _infer_cause(opportunity, failure_type),
        "lesson": _infer_lesson(opportunity, failure_type),
        "would_do_differently": "",
        "signal_pattern": f"score={opportunity.get('score', 0)}, cross_platform={opportunity.get('cross_platform_count', 0)}, uv={opportunity.get('day7_uv', 0)}",
    }
    data["lessons"].append(lesson)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[追踪] 经验已归档: {lesson_id}")
    return lesson_id


def _infer_cause(op: dict, failure_type: str) -> str:
    """基于数据推断失败原因。"""
    if failure_type == "no_traffic":
        return f"Landing Page 引流不足（{op.get('day7_uv', 0)} UV / 7 天），信号来源帖的流量未能有效转化"
    elif failure_type == "no_conversion":
        return f"有流量（{op.get('day7_uv', 0)} UV）但零注册——痛点不够痛或方案与用户期望不匹配"
    elif failure_type == "needs_pivot":
        return f"数据在临界区（{op.get('day7_uv', 0)} UV），需要调整定位或话术"
    return "信号本身强度不足以支撑产品机会"


def _infer_lesson(op: dict, failure_type: str) -> str:
    """基于失败类型生成经验教训。"""
    if failure_type == "no_traffic":
        return f"高分信号（{op.get('score', 0)}分）不必然等于高流量——信号讨论量不等于目标用户的搜索意图"
    elif failure_type == "no_conversion":
        return f"用户点进来了但没有注册——需要反思「谁会付钱」的判断是否准确"
    elif failure_type == "needs_pivot":
        return "临界数据不要立刻放弃——先调整一个变量（标题/话术/目标用户）再测一轮"
    return "信号强度与市场验证结果之间存在不确定性，需要更多数据点"


def run(date_str: str | None = None) -> list[dict]:
    """执行追踪更新。返回已处理的机会列表。"""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    print(f"\n{'='*50}")
    print(f"[追踪] 追踪更新 — {date}")
    print(f"{'='*50}")

    due = find_due_opportunities()
    print(f"[追踪] 到达验证期限的机会: {len(due)} 个")

    if not due:
        return []

    updates: list[dict] = []
    config = load_config()
    lp_thresholds = config.get("landing_page", {}).get("thresholds", {})

    for op in due:
        days = op.get("_days_elapsed", "?")
        lp_status = op.get("lp_status", "not_built")
        uv = op.get("day7_uv", 0)
        signups = op.get("day7_signups", 0)

        print(f"\n  [{op['id']}] {op['opportunity'][:50]}")
        print(f"    天数: Day {days} | LP 状态: {lp_status} | UV: {uv} | 注册: {signups}")

        if lp_status == "not_built":
            print(f"    → LP 未构建，状态保持 pending。请手动构建 LP 或标记为 abandoned。")
            updates.append({
                "id": op["id"],
                "verification_result": "pending",
                "day7_decision": "lp_not_built",
                "notes": f"Day {days}: LP 未构建。请主人决定是否构建或放弃。",
                "current_status": op.get("current_status", "monitoring"),
            })
            continue

        # 基于 LP 阈值判断
        success_uv = lp_thresholds.get("success", {}).get("uv", 100)
        fail_uv = lp_thresholds.get("fail", {}).get("uv", 30)

        if uv >= success_uv and signups > 0:
            verdict = "passed"
            decision = "build"
            status = "building"
            notes = f"Day {days}: ✅ 验证通过（{uv} UV, {signups} 注册）→ 投入做产品"
        elif uv < fail_uv:
            verdict = "failed"
            decision = "abandon"
            status = "archived"
            notes = f"Day {days}: ❌ 验证失败（{uv} UV < {fail_uv} 阈值）→ 放弃"
        else:
            verdict = "adjust"
            decision = "pivot_or_retry"
            status = "adjusting"
            notes = f"Day {days}: ⚠️ 临界区（{uv} UV, {signups} 注册）→ 需调整"

        updates.append({
            "id": op["id"],
            "verification_result": verdict,
            "day7_decision": decision,
            "day7_uv": uv,
            "day7_signups": signups,
            "notes": notes,
            "current_status": status,
        })

        # 失败 → 归档经验
        if verdict == "failed":
            op["day7_uv"] = uv
            op["day7_signups"] = signups
            op["day7_decision"] = decision
            archive_to_lessons(op)

    # 批量更新
    update_opportunities(updates)

    print(f"\n[追踪] 处理完成: {len(updates)} 条更新")
    return updates


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    try:
        run(today)
    except UnicodeEncodeError:
        print(f"[Tracking update completed, see tracking/ for details]")
