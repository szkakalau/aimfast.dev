"""
竞品追踪目标合并工具 (Phase 1)
读取 Dashboard 用户通过 localStorage 添加的 pending 目标，
合并到 tracking/competitor_targets.json。
由 daily_run 管线在 Step 2.6 之前调用。
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACKING_DIR = ROOT / "tracking"
TZ_SHANGHAI = timezone(timedelta(hours=8))


def merge_pending_targets() -> int:
    """
    读取 pending targets（从 Dashboard 导出的 JSON），合并到 competitor_targets.json。
    由于 Dashboard 是静态 HTML，pending targets 通过以下方式传递：
      1. 用户在 Dashboard 中「添加追踪」→ 保存到 localStorage
      2. 用户运行导出命令 → 生成 tracking/competitor_targets_pending.json
      3. 本脚本合并 pending → 正式 targets，并清理 pending

    返回合并数量。
    """
    pending_path = TRACKING_DIR / "competitor_targets_pending.json"
    targets_path = TRACKING_DIR / "competitor_targets.json"

    # 检查是否有 pending targets
    if not pending_path.exists():
        print("[合并目标] 无 pending targets，跳过")
        return 0

    try:
        pending_data = json.loads(pending_path.read_text(encoding="utf-8"))
        pending_targets = pending_data.get("targets", [])
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[合并目标] 读取 pending 失败: {e}")
        return 0

    if not pending_targets:
        print("[合并目标] pending 列表为空")
        return 0

    # 加载现有 targets
    existing = []
    if targets_path.exists():
        try:
            data = json.loads(targets_path.read_text(encoding="utf-8"))
            existing = data.get("targets", [])
        except (json.JSONDecodeError, KeyError):
            pass

    # 去重：跳过已存在的（按 name 匹配）
    existing_names = {t.get("name", "").lower() for t in existing}
    existing_ids = {t.get("id", "") for t in existing}

    merged_count = 0
    for pt in pending_targets:
        name_lower = pt.get("name", "").lower()
        if name_lower in existing_names:
            print(f"[合并目标] 跳过重复: {pt.get('name')}")
            continue
        # 分配正式 ID
        pt["id"] = f"target-{len(existing) + merged_count + 1:03d}"
        pt["status"] = "active"
        pt["paused_at"] = None
        existing.append(pt)
        merged_count += 1
        print(f"[合并目标] 新增: {pt.get('name')} (type={pt.get('type')})")

    if merged_count > 0:
        # 检查上限
        active_count = sum(1 for t in existing if t.get("status") == "active")
        if active_count > 10:
            print(f"[合并目标] ⚠️ 活跃目标 {active_count} 个 > 10 上限，请手动清理")

        output = {
            "_schema": targets_path.read_text(encoding="utf-8").split("\n")[0].strip() if targets_path.exists() else "Competitor & Topic Tracking Targets",
            "_version": "1.0",
            "_limit": 10,
            "_matching": "语义匹配为主 + 关键词匹配兜底",
            "targets": existing,
            "updated_at": datetime.now(TZ_SHANGHAI).isoformat(),
        }
        targets_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[合并目标] 已合并 {merged_count} 个新目标 → {targets_path}")
    else:
        print("[合并目标] 无新目标需要合并")

    # 清理 pending（重命名为 .merged 防重复处理）
    merged_path = TRACKING_DIR / f"competitor_targets_pending_merged_{datetime.now(TZ_SHANGHAI).strftime('%Y%m%d_%H%M%S')}.json"
    try:
        pending_path.rename(merged_path)
        print(f"[合并目标] Pending 已归档 → {merged_path.name}")
    except OSError:
        print(f"[合并目标] 无法重命名 pending 文件")

    return merged_count


if __name__ == "__main__":
    count = merge_pending_targets()
    print(f"\n[合并目标] 完成 — 合并了 {count} 个目标")
