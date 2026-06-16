"""
HuggingFace 模型趋势 信号采集
数据源: HuggingFace API (huggingface.co/api)
采集内容: 热门模型 + 下载量趋势 + 新发布模型
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"

TZ_SHANGHAI = timezone(timedelta(hours=8))

HF_API = "https://huggingface.co/api"

HEADERS = {
    "User-Agent": "AimFast-Dev/1.0 (signal-collector; contact@aimfast.dev)",
    "Accept": "application/json",
}

# 关注的模型类别（偏开发者和工具类）
TRACKED_TASKS = [
    "text-generation",
    "code-generation",
    "text-to-image",
    "automatic-speech-recognition",
    "image-classification",
    "sentence-transformers",
    "token-classification",
]


def _fetch_trending_models(limit: int = 20) -> list[dict]:
    """获取 HuggingFace 热门模型（按下载量排序，最近 30 天）。"""
    try:
        url = f"{HF_API}/models"
        params = {
            "sort": "downloads",
            "direction": "-1",
            "limit": limit,
            "full": "false",
        }
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        print(f"[HF] 模型列表 API 返回 {resp.status_code}")
        return []
    except requests.RequestException as e:
        print(f"[HF] 模型列表请求失败: {e}")
        return []


def _fetch_model_detail(model_id: str) -> dict | None:
    """获取单个模型的详细信息（包含下载量、likes、标签）。"""
    try:
        url = f"{HF_API}/models/{model_id}"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "model_id": model_id,
                "downloads": data.get("downloads", 0),
                "likes": data.get("likes", 0),
                "pipeline_tag": data.get("pipeline_tag", ""),
                "tags": data.get("tags", []),
                "author": data.get("author", ""),
                "last_modified": data.get("lastModified", ""),
                "created_at": data.get("createdAt", ""),
                "siblings_count": len(data.get("siblings", [])),
                "card_data": data.get("cardData", {}),
            }
        return None
    except requests.RequestException:
        return None


def _get_weekly_trending_models() -> list[dict]:
    """获取本周趋势模型（通过 API 的 trending 列表）。"""
    models: list[dict] = []
    try:
        # HF 没有直接的 trending API，用 models + downloads sort + 30d 窗口
        trending = _fetch_trending_models(limit=25)
        for m in trending:
            model_id = m.get("id", "")
            if not model_id:
                continue
            detail = _fetch_model_detail(model_id)
            if detail:
                models.append(detail)
    except Exception as e:
        print(f"[HF] 趋势模型获取异常: {e}")
    return models


def _to_signal(model: dict) -> dict:
    """将 HuggingFace 模型条目转为标准信号格式。"""
    model_id = model.get("model_id", "unknown")
    downloads = model.get("downloads", 0)
    likes = model.get("likes", 0)
    tags = model.get("tags", []) or []
    pipeline = model.get("pipeline_tag", "")
    author = model.get("author", "")

    # 生成易于理解的分类
    category = pipeline.replace("-", " ") if pipeline else "model"
    if isinstance(tags, list):
        for tag in tags:
            if tag.startswith("task:"):
                category = tag.replace("task:", "").replace("-", " ")
                break

    return {
        "id": f"hf-{model_id.replace('/', '-')}",
        "title": model_id,
        "url": f"https://huggingface.co/{model_id}",
        "source": "HuggingFace",
        "source_key": "huggingface",
        "signal_type": "model_trend",
        "discussion_count": likes,
        "engagement": {
            "downloads": downloads,
            "likes": likes,
            "total": max(_download_score(downloads) + likes, 5),
        },
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "summary": f"[HF 模型] {model_id}（{downloads:,} 下载 / {likes} likes / {category}）",
        "tags": [category, author] + (tags if isinstance(tags, list) else []),
        "author": author,
        "raw_data": {
            "downloads": downloads,
            "likes": likes,
            "pipeline_tag": pipeline,
            "last_modified": model.get("last_modified", ""),
            "category": category,
        },
    }


def _download_score(downloads: int) -> int:
    """将下载量映射为一个小分值（避免下载量主导排序）。"""
    if downloads > 10_000_000:
        return 15
    elif downloads > 1_000_000:
        return 10
    elif downloads > 100_000:
        return 7
    elif downloads > 10_000:
        return 4
    return 2


def collect(date_str: str | None = None) -> list[dict]:
    """
    采集 HuggingFace 模型趋势。

    1. 从 API 获取 Top 25 热门模型（按下载量）
    2. 补充模型详情（likes、标签等）
    3. 重点关注开发者工具类模型（text-generation, code-generation）
    """
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    signals: list[dict] = []

    print("[HF] 获取 HuggingFace 热门模型...")
    models = _get_weekly_trending_models()
    print(f"[HF] 获取到 {len(models)} 个模型详情")

    for model in models:
        signal = _to_signal(model)
        signals.append(signal)

    # 按 engagement 排序
    signals.sort(key=lambda s: s["engagement"]["total"], reverse=True)
    signals = signals[:25]

    # 标记开发者相关模型
    dev_tags = {"code", "text-generation", "sentence-transformers", "embedding", "tokenizer"}
    dev_count = 0
    for s in signals:
        raw = s.get("raw_data", {})
        pipeline = raw.get("pipeline_tag", "")
        if pipeline in dev_tags:
            s["tags"].append("dev-tools")
            dev_count += 1

    print(f"[HF] {len(signals)} 条模型信号（{dev_count} 条开发者相关）")
    return signals


def save_raw(signals: list[dict], date_str: str) -> None:
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "huggingface",
        "note": "HuggingFace 热门模型信号。关注开发者工具类模型趋势。",
        "count": len(signals),
        "signals": signals,
    }
    path = dir_path / "huggingface.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[HF] {len(signals)} 条信号 → {path}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
