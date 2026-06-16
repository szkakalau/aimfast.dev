"""
Reddit 信号采集
数据源: Reddit RSS feeds (公开免费, 无需认证)
采集内容: 5 个目标子版块热帖
"""
import json
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"

TZ_SHANGHAI = timezone(timedelta(hours=8))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

SUBREDDITS = [
    "programming",
    "MachineLearning",
    "SaaS",
    "SideProject",
    "Entrepreneur",
]


def _parse_rss_entry(entry: ET.Element, subreddit: str) -> dict | None:
    """将 RSS entry 转为标准信号格式。"""
    ns = {"atom": "http://www.w3.org/2005/Atom"}

    title_el = entry.find("title")
    link_el = entry.find("link")
    author_el = entry.find("author/name") or entry.find("author")
    updated_el = entry.find("updated") or entry.find("pubDate")

    title = title_el.text.strip() if title_el is not None and title_el.text else ""
    if len(title) < 10:
        return None

    url = link_el.get("href", "") if link_el is not None else ""
    author = author_el.text.strip() if author_el is not None and author_el.text else ""

    # 从 title 提取粗略互动量标记（如 "[123 comments]"）
    comments = 0
    comment_match = re.search(r"\[(\d+)\s*comments?\]", title, re.IGNORECASE)
    if comment_match:
        comments = int(comment_match.group(1))

    # 生成 ID
    post_id = re.sub(r"[^\w\-]", "", title[:40].replace(" ", "-").lower())

    return {
        "id": f"reddit-{subreddit}-{post_id}",
        "title": title.strip(),
        "url": url,
        "source": f"Reddit r/{subreddit}",
        "source_key": "reddit",
        "signal_type": "post",
        "discussion_count": comments,
        "engagement": {
            "comments": comments,
            "total": comments * 5 + 1,  # 粗略估算
        },
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "raw_created_utc": None,
        "summary": f"[r/{subreddit}] {title[:80]}",
        "tags": [subreddit],
        "author": author,
    }


def _fetch_subreddit(sub: str) -> list[dict]:
    """获取单个子版块的 RSS 热帖。"""
    url = f"https://www.reddit.com/r/{sub}/hot/.rss?limit=30"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

        # Reddit RSS uses Atom namespace
        atom_ns = "http://www.w3.org/2005/Atom"
        entries = root.findall(f".//{{{atom_ns}}}entry")
        if not entries:
            entries = root.findall(".//entry")

        signals = []
        for entry in entries:
            s = _parse_rss_entry(entry, sub)
            if s:
                signals.append(s)
        if not signals:
            print(f"[Reddit] r/{sub} 解析到 {len(entries)} 个 entry，但 0 条通过过滤")
        return signals
    except requests.RequestException as e:
        print(f"[Reddit] r/{sub} 请求失败: {e}")
        return []
    except ET.ParseError as e:
        print(f"[Reddit] r/{sub} XML 解析失败: {e}")
        return []


def collect(date_str: str | None = None) -> list[dict]:
    """
    采集 5 个子版块 RSS 热帖，每版最多 30 条。
    去重后取 top 40。
    """
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    seen: set[str] = set()
    signals: list[dict] = []
    sub_stats: dict[str, int] = {}

    for i, sub in enumerate(SUBREDDITS):
        if i > 0:
            time.sleep(3)  # 避免 429 rate-limit
        entries = _fetch_subreddit(sub)
        count = 0
        for s in entries:
            if s["id"] not in seen:
                seen.add(s["id"])
                signals.append(s)
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
