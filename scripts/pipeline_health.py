"""
Pipeline Health Dashboard — 每日管线健康聚合
汇聚 5 个数据源: exit_code, timing, pipeline status, token usage, source counts
输出: tracking/pipeline_health.json (每日管线自动生成并提交到 git)
"""
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
TRACKING_DIR = ROOT / "tracking"
DAILY_DIR = ROOT / "daily"
LOGS_DIR = ROOT / "logs"
RAW_DIR = ROOT / "raw"
TZ_SHANGHAI = timezone(timedelta(hours=8))


def load_json_safe(path: Path) -> dict:
    """加载 JSON 文件，任何失败返回空 dict。"""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def read_exit_code(date_str: str) -> int | None:
    """从多个信号源判定管线是否成功（按可靠性排序）。

    1. daily/{DATE}/.pipeline_done — 只有完整成功才写入
    2. logs/.exit_code — trap 在脚本退出时写入
    3. daily/{DATE}/signals.json 存在 → 至少信源采集成功

    返回 0=成功, 1=失败, None=无法判定。
    """
    # 最可靠信号：锁文件只在管线完整跑完时才写入
    lock_file = DAILY_DIR / date_str / ".pipeline_done"
    if lock_file.exists():
        return 0

    # 次选：shell trap 写入的退出码文件
    exit_code_path = LOGS_DIR / ".exit_code"
    if exit_code_path.exists():
        try:
            content = exit_code_path.read_text(encoding="utf-8").strip()
            match = re.search(r"PIPELINE_EXIT_CODE=(\d+)", content)
            if match:
                return int(match.group(1))
        except OSError:
            pass

    # 兜底：signals.json 存在说明 Step 1 成功（管线至少部分运行）
    signals_file = DAILY_DIR / date_str / "signals.json"
    if signals_file.exists():
        return 0  # 部分成功视为成功 — 至少数据产出了

    return None


def parse_timings_from_log(date_str: str) -> dict[str, int]:
    """从 daily/{DATE}/pipeline.log 或 logs/{DATE}.log 解析 [TIMING] 条目。"""
    # 主路径：daily_run.sh 在 Summary 阶段复制到 daily 目录
    log_path = DAILY_DIR / date_str / "pipeline.log"
    if not log_path.exists():
        # 回退：logs 目录下的日志（旧格式或本地运行）
        log_path = LOGS_DIR / f"{date_str}.log"
    if not log_path.exists():
        return {}
    try:
        content = log_path.read_text(encoding="utf-8")
    except OSError:
        return {}

    timings: dict[str, int] = {}
    pattern = re.compile(r"\[TIMING\]\s+(.+?):\s+(\d+)s")
    for match in pattern.finditer(content):
        name = match.group(1).strip()
        seconds = int(match.group(2))
        timings[name] = seconds
    return timings


def load_pipeline_status(date_str: str) -> dict:
    """加载 pipeline.json（复用 pipeline_status.read()）。"""
    from scripts.pipeline_status import read as read_pipeline_status
    return read_pipeline_status(date_str)


def count_raw_sources(date_str: str) -> dict:
    """统计 raw/{DATE}/ 中每个采集器的输出状态。"""
    raw_date_dir = RAW_DIR / date_str
    if not raw_date_dir.exists():
        return {"total": 0, "successful": 0, "failed": 0, "failed_names": []}

    total = 0
    successful = 0
    failed_names: list[str] = []

    for f in sorted(raw_date_dir.glob("*.json")):
        if f.name.startswith("."):
            continue  # 跳过隐藏文件
        total += 1
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            signals = data.get("signals", [])
            if signals and len(signals) > 0:
                successful += 1
            else:
                # 文件存在但无信号 → 也算失败
                failed_names.append(f.stem)
        except (json.JSONDecodeError, OSError):
            failed_names.append(f.stem)

    return {
        "total": total,
        "successful": successful,
        "failed": total - successful,
        "failed_names": failed_names[:10],  # 截断，最多展示 10 个
    }


def count_terms_new(date_str: str, trend_terms: dict) -> int:
    """统计今日新增词条数（first_seen == date_str）。"""
    terms = trend_terms.get("terms", [])
    return sum(1 for t in terms if t.get("first_seen") == date_str)


def compute_consecutive_success(date_str: str, today_success: bool) -> int:
    """从历史 pipeline_health.json 计算连续成功天数。"""
    health_path = TRACKING_DIR / "pipeline_health.json"

    # 先读今天刚写入的文件（如果存在）
    # 但我们是在写入之前计算，所以从昨天开始向后看

    # 简单实现：从 tracking/pipeline_health.json 读取上一次的值并递增
    # 如果没有历史文件，从 1（如果今天成功）或 0（如果失败）开始
    prev_data = load_json_safe(health_path)
    prev_consecutive = prev_data.get("consecutive_success_days", 0)

    if today_success:
        return prev_consecutive + 1
    else:
        return 0


def generate_warnings(
    steps: dict,
    timings: dict,
    sources: dict,
) -> list[str]:
    """从步骤耗时和状态生成警告。"""
    warnings: list[str] = []

    # 步骤耗时 > 300 秒警告
    for step_name, step_info in steps.items():
        status = step_info.get("status", "unknown")
        if status == "error":
            reason = step_info.get("reason", "未知错误")
            warnings.append(f"步骤 '{step_name}' 失败: {reason}")

    for name, seconds in timings.items():
        if seconds > 300:
            minutes = round(seconds / 60)
            warnings.append(f"步骤 '{name}' 耗时过长 ({minutes} 分钟)")

    # 信源失败率高
    if sources.get("total", 0) > 0:
        fail_rate = sources["failed"] / sources["total"]
        if fail_rate > 0.3:
            warnings.append(
                f"信源失败率 {fail_rate:.0%} ({sources['failed']}/{sources['total']}) — "
                f"失败: {', '.join(sources.get('failed_names', [])[:5])}"
            )

    return warnings


def run(date_str: str | None = None):
    """主入口：汇聚所有数据源，生成管线健康报告。"""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")

    # 1. 退出码
    exit_code = read_exit_code(date)

    # 2. 耗时解析
    timings = parse_timings_from_log(date)

    # 3. Pipeline 状态
    pipeline_status = load_pipeline_status(date)

    # 4. Token 用量
    token_data = load_json_safe(TRACKING_DIR / "token_usage.json")
    tokens = {
        "total": token_data.get("total_tokens", 0),
        "calls": token_data.get("calls", 0),
    }

    # 5. 信源采集状态
    sources = count_raw_sources(date)

    # 6. 词条统计
    trend_terms = load_json_safe(TRACKING_DIR / "trend_terms.json")
    total_terms = len(trend_terms.get("terms", []))
    new_today = count_terms_new(date, trend_terms)

    # 7. 总体耗时
    total_seconds = sum(timings.values())
    duration_minutes = round(total_seconds / 60) if total_seconds > 0 else 0

    # 8. 成功判定
    success = exit_code == 0

    # 9. 警告
    warnings = generate_warnings(
        pipeline_status.get("steps", {}),
        timings,
        sources,
    )

    # 10. 连续成功天数
    consecutive = compute_consecutive_success(date, success)

    # 11. 合并步骤信息（pipeline_status + timing）
    steps = {}
    for step_name, step_info in pipeline_status.get("steps", {}).items():
        # 匹配耗时（模糊匹配步骤名）
        duration = 0
        for timing_name, timing_sec in timings.items():
            if step_name.lower() in timing_name.lower():
                duration = timing_sec
                break

        steps[step_name] = {
            "status": step_info.get("status", "unknown"),
            "duration_sec": duration,
        }
        if step_info.get("reason"):
            steps[step_name]["reason"] = step_info["reason"]

    # 12. 组装输出
    output = {
        "date": date,
        "generated_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "success": success,
        "exit_code": exit_code,
        "duration_minutes": duration_minutes,
        "steps": steps,
        "tokens": tokens,
        "sources": sources,
        "terms": {"total": total_terms, "new_today": new_today},
        "warnings": warnings,
        "consecutive_success_days": consecutive,
    }

    # 13. 写入
    from scripts.defaults import atomic_write_json
    output_path = TRACKING_DIR / "pipeline_health.json"
    atomic_write_json(output_path, output)

    print(f"[PipelineHealth] 报告已保存到 {output_path}")
    print(
        f"[PipelineHealth] 状态: {'[OK] 成功' if success else f'[FAIL] 失败 (exit_code={exit_code})'}"
    )
    print(
        f"[PipelineHealth] 词条: {total_terms} 总 / +{new_today} 今日新增"
    )
    print(
        f"[PipelineHealth] 信源: {sources['successful']}/{sources['total']} 成功"
    )
    print(
        f"[PipelineHealth] 连续成功: {consecutive} 天"
    )
    if duration_minutes > 0:
        print(f"[PipelineHealth] 耗时: {duration_minutes} 分钟")
    if warnings:
        print(f"[PipelineHealth] {len(warnings)} 条警告")

    return output


if __name__ == "__main__":
    run()
