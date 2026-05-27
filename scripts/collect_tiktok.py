"""
TikTok 热销品 信号采集
数据源: TikTok 热销品定时任务（已有）
采集内容: 海外热销品 + GMV + 趋势

前置依赖: 已有 TikTok 热销品定时任务输出 JSON 数据。
默认读取路径: ./raw/tiktok_export/ 或通过 config.json 配置。
"""
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"
CONFIG_PATH = ROOT / "config.json"

TZ_SHANGHAI = timezone(timedelta(hours=8))

# 默认 TikTok 数据路径（用户已有定时任务产出）
DEFAULT_TIKTOK_DATA_DIR = ROOT / "raw" / "tiktok_export"


def _load_config_tiktok_path() -> Path | None:
    """从 config.json 读取 TikTok 数据路径配置。"""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        path_str = config.get("signals", {}).get("domestic", [])
        for source in path_str:
            if source.get("key") == "tiktok":
                data_path = source.get("data_path", "")
                if data_path:
                    return Path(data_path)
        return None
    except Exception:
        return None


def _find_latest_export(data_dir: Path) -> Path | None:
    """在数据目录中找到最新的导出文件。"""
    if not data_dir.exists():
        return None

    json_files = sorted(data_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return json_files[0] if json_files else None


def _parse_tiktok_export(filepath: Path) -> list[dict]:
    """
    解析 TikTok 热销品导出文件。
    支持常见的导出格式：list of products、{products: [...]}、{data: {items: [...]}}
    """
    try:
        data = json.loads(filepath.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        print(f"[TikTok] 无法解析文件: {filepath}")
        return []

    # 适配多种 JSON 结构
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = data.get("products") or data.get("items") or data.get("data", {}).get("items") or []
    else:
        items = []

    return items


def _to_signal(item: dict) -> dict:
    """将 TikTok 热销品条目转为标准信号格式。"""
    # 字段名可能因导出格式而异，做兼容处理
    name = item.get("product_name") or item.get("name") or item.get("title") or "Unknown"
    gmv = item.get("gmv") or item.get("revenue") or 0
    if isinstance(gmv, str):
        gmv = float(gmv.replace("$", "").replace(",", "")) if gmv else 0

    category = item.get("category") or item.get("product_category") or ""
    market = item.get("market") or item.get("region") or item.get("country") or ""

    return {
        "id": f"tiktok-{item.get('product_id', item.get('id', name.replace(' ', '-')))}",
        "title": name,
        "url": item.get("url") or item.get("link", ""),
        "source": "TikTok 热销品",
        "source_key": "tiktok",
        "signal_type": "hot_product",
        "discussion_count": 0,
        "engagement": {
            "gmv": round(float(gmv), 2),
            "total": max(int(float(gmv) / 100), 5),
        },
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "summary": f"[TikTok 热销] {name}（{category} / {market} / GMV ${gmv}）",
        "tags": ["hot-product", category, market],
        "author": "",
        "raw_data": {
            "gmv": gmv,
            "category": category,
            "market": market,
            "trend": item.get("trend", ""),
        },
    }


def collect(date_str: str | None = None) -> list[dict]:
    """
    采集 TikTok 热销品数据。
    1. 尝试从 config.json 中指定的路径读取
    2. 回退到默认路径 ./raw/tiktok_export/
    3. 取 GMV top 40
    """
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")

    # 确定数据目录
    data_dir = _load_config_tiktok_path() or DEFAULT_TIKTOK_DATA_DIR
    latest = _find_latest_export(data_dir)

    if latest is None:
        print(f"[TikTok] 未找到 TikTok 导出数据。")
        print(f"[TikTok] 请将 TikTok 热销品定时任务的 JSON 输出放到: {data_dir}")
        print(f"[TikTok] 或通过 config.json → signals.domestic → tiktok.data_path 配置路径")
        return []

    print(f"[TikTok] 读取: {latest}")
    items = _parse_tiktok_export(latest)

    signals = [_to_signal(item) for item in items]
    signals.sort(key=lambda s: s["engagement"]["total"], reverse=True)
    signals = signals[:40]

    print(f"[TikTok] {len(signals)} 条热销品信号")
    return signals


def save_raw(signals: list[dict], date_str: str) -> None:
    """保存原始采集数据。"""
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "tiktok",
        "count": len(signals),
        "signals": signals,
    }
    path = dir_path / "tiktok.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[TikTok] {len(signals)} 条信号 → {path}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
