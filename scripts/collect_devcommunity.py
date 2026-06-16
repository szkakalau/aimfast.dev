"""
DEV Community 信号采集
数据源: dev.to API (免费公开, 无需认证)
采集内容: 热门文章 — 编程/SaaS/AI/创业话题
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"

TZ_SHANGHAI = timezone(timedelta(hours=8))
DEV_API = "https://dev.to/api/articles"

HEADERS = {"User-Agent": "KAKAOPC-Intel/2.0 (+https://aimfast.dev)"}

# 覆盖 Reddit 原本的 5 个子版块话题
TAGS = [
    "programming",
    "ai",
    "saas",
    "startup",
    "machinelearning",
    "webdev",
    "productivity",
]


def _fetch_tag(tag: str, top_days: int = 3) -> list[dict]:
    """获取指定 tag 的热门文章。"""
    params = {"tag": tag, "top": str(top_days), "per_page": 15}
    try:
        resp = requests.get(DEV_API, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"[DEV] tag={tag} 请求失败: {e}")
        return []


def _to_signal(article: dict) -> dict | None:
    """将 DEV 文章转为标准信号格式。"""
    title = article.get("title", "")
    if len(title) < 10:
        return None

    art_id = article.get("id", "")
    url = article.get("url", "")
    comments = article.get("comments_count", 0)
    reactions = article.get("positive_reactions_count", 0)
    tags = article.get("tag_list", [])
    user = article.get("user", {}) or {}

    return {
        "id": f"dev-{art_id}",
        "title": title.strip(),
        "url": url,
        "source": "DEV Community",
        "source_key": "devcommunity",
        "signal_type": "article",
        "discussion_count": comments,
        "engagement": {
            "reactions": reactions,
            "comments": comments,
            "total": reactions + comments * 3,
        },
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "raw_created_at": article.get("published_at", ""),
        "summary": f"[DEV] {title[:80]}（{reactions} 赞 / {comments} 评论）",
        "tags": [t for t in tags if isinstance(t, str)][:5],
        "author": user.get("name") or user.get("username", ""),
    }


def collect(date_str: str | None = None) -> list[dict]:
    """采集 DEV 各 tag 热门文章, 去重取 top 40。"""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    seen: set[str] = set()
    signals: list[dict] = []

    for tag in TAGS:
        articles = _fetch_tag(tag)
        count = 0
        for art in articles:
            s = _to_signal(art)
            if s and s["id"] not in seen:
                seen.add(s["id"])
                signals.append(s)
                count += 1
        print(f"[DEV] #{tag}: {count} 条")

    signals.sort(key=lambda s: s["engagement"]["total"], reverse=True)
    signals = signals[:40]

    print(f"[DEV] 总计: {len(signals)} 条")
    return signals


def save_raw(signals: list[dict], date_str: str) -> None:
    """保存到 ./raw/YYYY-MM-DD/devcommunity.json"""
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "devcommunity",
        "count": len(signals),
        "signals": signals,
    }
    path = dir_path / "devcommunity.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[DEV] → {path}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
