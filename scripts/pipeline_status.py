"""
Pipeline 状态写入 —— 每个步骤在 daily/YYYY-MM-DD/pipeline.json 中记录自己的状态。
Dashboard 前端读取这些状态，在空态时显示真实的跳过原因。
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAILY_DIR = ROOT / "daily"
TZ_SHANGHAI = timezone(timedelta(hours=8))


def write(date_str: str, step: str, status: str, *, reason: str = "", message: str = ""):
    """写入某个 pipeline 步骤的状态到 daily/<date>/pipeline.json。

    status: "generated" | "skipped" | "error"
    """
    daily = DAILY_DIR / date_str
    daily.mkdir(parents=True, exist_ok=True)
    path = daily / "pipeline.json"

    existing = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    existing.setdefault("date", date_str)
    existing.setdefault("steps", {})

    entry = {
        "status": status,
        "updated_at": datetime.now(TZ_SHANGHAI).isoformat(),
    }
    if reason:
        entry["reason"] = reason
    if message:
        entry["message"] = message

    existing["steps"][step] = entry
    path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")


def read(date_str: str) -> dict:
    """读取 pipeline 状态。返回 {steps: {...}} 或空 dict。"""
    path = DAILY_DIR / date_str / "pipeline.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
