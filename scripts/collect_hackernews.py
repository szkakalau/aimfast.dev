"""
Hacker News 信号采集
数据源: HN Algolia API (https://hn.algolia.com/api)
采集内容: Top stories + Show HN + Ask HN
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"
HN_API = "https://hn.algolia.com/api/v1"

TZ_SHANGHAI = timezone(timedelta(hours=8))


def _fetch(endpoint: str, params: dict) -> list[dict]:
    """调用 HN Algolia API，返回 hits 列表。"""
    url = f"{HN_API}/{endpoint}"
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("hits", [])
    except requests.RequestException as e:
        print(f"[HN] API 请求失败: {e}")
        return []


def _to_signal(hit: dict, signal_type: str = "story") -> dict:
    """将 HN hit 转为标准信号格式。"""
    title = hit.get("title", "(无标题)")
    url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit['objectID']}"
    discussion = hit.get("num_comments", 0) or 0
    points = hit.get("points", 0) or 0

    tags = hit.get("_tags", [])
    return {
        "id": f"hn-{hit['objectID']}",
        "title": title.strip(),
        "url": url,
        "source": "Hacker News",
        "source_key": "hn",
        "signal_type": signal_type,
        "discussion_count": discussion,
        "engagement": {
            "points": points,
            "comments": discussion,
            "total": points + discussion * 2,
        },
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "raw_created_at": hit.get("created_at", ""),
        "summary": f"{title}（{points} 赞 / {discussion} 评论）",
        "tags": tags,
        "author": hit.get("author", ""),
    }


def collect(date_str: str | None = None) -> list[dict]:
    """
    采集 HN 当日热帖: front page top 50 + Show HN top 30 + Ask HN top 10。
    按互动量（points + comments×2）降序，去重后取 top 40。
    """
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    seen: set[str] = set()
    hits: list[dict] = []

    # 1. 首页热帖（points > 30，最近 24h）
    front_page = _fetch("search", {
        "tags": "front_page",
        "hitsPerPage": 50,
        "numericFilters": "points>30",
    })
    for h in front_page:
        h["_source_tag"] = "front_page"

    # 2. Show HN（最近 3 天，按 points 排序）
    show_hn = _fetch("search_by_date", {
        "tags": "show_hn",
        "hitsPerPage": 30,
        "numericFilters": "points>5",
    })
    for h in show_hn:
        h["_source_tag"] = "show_hn"

    # 3. Ask HN（最近 3 天，高评论）
    ask_hn = _fetch("search_by_date", {
        "tags": "ask_hn",
        "hitsPerPage": 15,
        "numericFilters": "num_comments>20",
    })
    for h in ask_hn:
        h["_source_tag"] = "ask_hn"

    # 合并去重
    all_hits = front_page + show_hn + ask_hn
    for h in all_hits:
        oid = h.get("objectID", "")
        if oid in seen:
            continue
        seen.add(oid)
        signal = _to_signal(h, signal_type=h.get("_source_tag", "story"))
        hits.append(signal)

    # 按互动量降序
    hits.sort(key=lambda s: s["engagement"]["total"], reverse=True)
    hits = hits[:40]

    print(f"[HN] 采集完成: front_page={len(front_page)} show_hn={len(show_hn)} ask_hn={len(ask_hn)} → 去重后 {len(hits)} 条")
    return hits


def save_raw(signals: list[dict], date_str: str) -> None:
    """保存原始采集数据到 ./raw/YYYY-MM-DD/hn.json"""
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "hn",
        "count": len(signals),
        "signals": signals,
    }
    path = dir_path / "hn.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[HN] {len(signals)} 条信号 → {path}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
