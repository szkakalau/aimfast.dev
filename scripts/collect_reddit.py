"""
Reddit 信号采集
数据源: Reddit JSON API（无需认证，只需 User-Agent）
采集内容: 5 个目标子版块热帖
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"

TZ_SHANGHAI = timezone(timedelta(hours=8))
REDDIT_BASE = "https://www.reddit.com"

HEADERS = {"User-Agent": "KAKAOPC-Intel/1.0 (signal-collector; contact@aimfast.dev)"}

SUBREDDITS = [
    "programming",
    "MachineLearning",
    "SaaS",
    "SideProject",
    "Entrepreneur",
]


def _fetch_subreddit(sub: str, limit: int = 30) -> list[dict]:
    """获取单个子版块的热帖。"""
    url = f"{REDDIT_BASE}/r/{sub}/hot.json"
    try:
        resp = requests.get(url, headers=HEADERS, params={"limit": limit}, timeout=15)
        resp.raise_for_status()
        return resp.json().get("data", {}).get("children", [])
    except requests.RequestException as e:
        print(f"[Reddit] r/{sub} 请求失败: {e}")
        return []


def _to_signal(post_data: dict, subreddit: str) -> dict | None:
    """将 Reddit post 转为标准信号格式。"""
    d = post_data.get("data", {})
    if not d:
        return None

    title = d.get("title", "")
    # 跳过置顶帖和过短标题
    if d.get("stickied") or len(title) < 10:
        return None

    permalink = d.get("permalink", "")
    url = f"https://www.reddit.com{permalink}" if permalink else d.get("url", "")
    comments = d.get("num_comments", 0)
    ups = d.get("ups", 0)
    score = d.get("score", 0)

    return {
        "id": f"reddit-{d.get('id', '')}",
        "title": title.strip(),
        "url": url,
        "external_url": d.get("url") if d.get("is_self") is False else None,
        "source": f"Reddit r/{subreddit}",
        "source_key": "reddit",
        "signal_type": "post",
        "discussion_count": comments,
        "engagement": {
            "ups": ups,
            "score": score,
            "comments": comments,
            "upvote_ratio": d.get("upvote_ratio", 0),
            "total": comments * 3 + ups,
        },
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "raw_created_utc": d.get("created_utc", 0),
        "summary": f"[r/{subreddit}] {title[:80]}（{ups} 赞 / {comments} 评论）",
        "tags": [subreddit],
        "author": d.get("author", ""),
        "nsfw": d.get("over_18", False),
    }


def collect(date_str: str | None = None) -> list[dict]:
    """
    采集 5 个子版块热帖，每版 30 条。
    按互动量（comments×3 + ups）降序，去重后取 top 40。
    """
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    seen: set[str] = set()
    signals: list[dict] = []
    sub_stats: dict[str, int] = {}

    for sub in SUBREDDITS:
        posts = _fetch_subreddit(sub, limit=30)
        count = 0
        for p in posts:
            signal = _to_signal(p, sub)
            if signal and signal["id"] not in seen:
                seen.add(signal["id"])
                signals.append(signal)
                count += 1
        sub_stats[sub] = count
        print(f"[Reddit] r/{sub}: {count} 条有效信号")

    signals.sort(key=lambda s: s["engagement"]["total"], reverse=True)
    signals = signals[:40]

    print(f"[Reddit] 总计: {sum(sub_stats.values())} 条 → 去重排序后 {len(signals)} 条")
    return signals


def save_raw(signals: list[dict], date_str: str) -> None:
    """保存原始采集数据到 ./raw/YYYY-MM-DD/reddit.json"""
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "reddit",
        "subreddits": SUBREDDITS,
        "count": len(signals),
        "signals": signals,
    }
    path = dir_path / "reddit.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[Reddit] {len(signals)} 条信号 → {path}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
