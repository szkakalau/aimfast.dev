"""
Reddit 信号采集
数据源: PullPush.io (Reddit 公开数据归档, 免费无需认证)
备选: RSS feeds (被封锁时降级)
采集内容: 5 个目标子版块近 3 天热帖
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"

TZ_SHANGHAI = timezone(timedelta(hours=8))
PULLPUSH_API = "https://api.pullpush.io/reddit/search/submission/"

HEADERS = {"User-Agent": "KAKAOPC-Intel/2.0 (+https://aimfast.dev)"}

SUBREDDITS = [
    "programming",
    "MachineLearning",
    "SaaS",
    "SideProject",
    "Entrepreneur",
]


def _fetch_subreddit(sub: str, after_days: int = 7) -> list[dict]:
    """通过 PullPush.io 获取子版块近 N 天帖子 (按分数降序, 最多 40 条)。PullPush 数据有 2-3 天延迟。"""
    since = int((datetime.now(TZ_SHANGHAI) - timedelta(days=after_days)).timestamp())
    params = {
        "subreddit": sub,
        "size": 40,
        "sort": "desc",
        "sort_type": "score",
        "after": since,
    }
    try:
        resp = requests.get(PULLPUSH_API, headers=HEADERS, params=params, timeout=20)
        resp.raise_for_status()
        return resp.json().get("data", [])
    except requests.RequestException as e:
        print(f"[Reddit] PullPush r/{sub} 请求失败: {e}")
        return []


def _to_signal(post: dict, subreddit: str) -> dict | None:
    """将 PullPush post 转为标准信号格式。"""
    title = post.get("title", "")
    if len(title) < 10 or post.get("stickied"):
        return None

    post_id = post.get("id", "")
    permalink = post.get("permalink", "")
    url = f"https://www.reddit.com{permalink}" if permalink else post.get("url", "")
    comments = post.get("num_comments", 0)
    score = post.get("score", 0)
    ups = post.get("ups", score)
    created = post.get("created_utc", 0)

    return {
        "id": f"reddit-{post_id}",
        "title": title.strip(),
        "url": url,
        "source": f"Reddit r/{subreddit}",
        "source_key": "reddit",
        "signal_type": "post",
        "discussion_count": comments,
        "engagement": {
            "score": score,
            "ups": ups,
            "comments": comments,
            "upvote_ratio": post.get("upvote_ratio", 0),
            "total": comments * 3 + ups,
        },
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "raw_created_utc": created,
        "summary": f"[r/{subreddit}] {title[:80]}（{ups} 赞 / {comments} 评论）",
        "tags": [subreddit],
        "author": post.get("author", ""),
    }


def collect(date_str: str | None = None) -> list[dict]:
    """采集 5 个子版块帖子, 去重取 top 40。"""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    seen: set[str] = set()
    signals: list[dict] = []

    for sub in SUBREDDITS:
        posts = _fetch_subreddit(sub)
        count = 0
        for p in posts:
            signal = _to_signal(p, sub)
            if signal and signal["id"] not in seen:
                seen.add(signal["id"])
                signals.append(signal)
                count += 1
        print(f"[Reddit] r/{sub}: {count} 条有效信号")

    signals.sort(key=lambda s: s["engagement"]["total"], reverse=True)
    signals = signals[:40]

    print(f"[Reddit] 总计: {len(signals)} 条 (via PullPush.io)")
    return signals


def save_raw(signals: list[dict], date_str: str) -> None:
    """保存到 ./raw/YYYY-MM-DD/reddit.json"""
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "reddit (via PullPush.io)",
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
