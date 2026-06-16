"""
Lobsters 信号采集
数据源: lobste.rs JSON API (免费公开, 无需认证)
采集内容: 首页最热帖子
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"

TZ_SHANGHAI = timezone(timedelta(hours=8))
LOBSTERS_BASE = "https://lobste.rs"

HEADERS = {"User-Agent": "KAKAOPC-Intel/2.0 (+https://aimfast.dev)"}


def _fetch_hottest(page: int = 1) -> list[dict]:
    """获取 Lobsters 最热帖子 (JSON API, 每页 25 条)。"""
    url = f"{LOBSTERS_BASE}/hottest.json?page={page}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"[Lobsters] page {page} 请求失败: {e}")
        return []


def _to_signal(story: dict) -> dict | None:
    """将 Lobsters story 转为标准信号格式。"""
    title = story.get("title", "")
    if len(title) < 5:
        return None

    short_id = story.get("short_id", "")
    score = story.get("score", 0)
    comments = story.get("comment_count", 0)
    tags = story.get("tags", [])

    return {
        "id": f"lobsters-{short_id}",
        "title": title.strip(),
        "url": story.get("url") or f"{LOBSTERS_BASE}/s/{short_id}",
        "source": "Lobsters",
        "source_key": "lobsters",
        "signal_type": "story",
        "discussion_count": comments,
        "engagement": {
            "score": score,
            "comments": comments,
            "total": comments * 3 + score,
        },
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "raw_created_at": story.get("created_at", ""),
        "summary": f"{title[:80]}（{score} 分 / {comments} 评论）",
        "tags": [t for t in tags if isinstance(t, str)],
        "author": (story.get("submitter_user", {}) or {}).get("username", "") if isinstance(story.get("submitter_user"), dict) else story.get("submitter_user", ""),
    }


def collect(date_str: str | None = None) -> list[dict]:
    """采集 Lobsters 首页和第 2 页最热帖子 (最多 50 条)，去重取 top 40。"""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    seen: set[str] = set()
    signals: list[dict] = []

    for page in [1, 2]:
        stories = _fetch_hottest(page)
        for story in stories:
            signal = _to_signal(story)
            if signal and signal["id"] not in seen:
                seen.add(signal["id"])
                signals.append(signal)

    signals.sort(key=lambda s: s["engagement"]["total"], reverse=True)
    signals = signals[:40]

    print(f"[Lobsters] 采集 {len(signals)} 条信号")
    return signals


def save_raw(signals: list[dict], date_str: str) -> None:
    """保存到 ./raw/YYYY-MM-DD/lobsters.json"""
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "lobsters",
        "count": len(signals),
        "signals": signals,
    }
    path = dir_path / "lobsters.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[Lobsters] → {path}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
