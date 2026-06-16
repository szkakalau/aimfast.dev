"""
Reddit 信号采集
数据源: Reddit RSS feeds (公开免费, hot.rss 端点可用)
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

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; KAKAOPC-Intel/2.0; +https://aimfast.dev)"}

SUBREDDITS = [
    "programming",
    "MachineLearning",
    "SideProject",
    "Entrepreneur",
]

ATOM_NS = "http://www.w3.org/2005/Atom"


def _clean_xml(raw: bytes) -> bytes:
    """移除 XML 中的非法 surrogate 字符 (U+D800-U+DFFF)。"""
    cleaned = bytearray()
    i = 0
    while i < len(raw):
        if i + 2 < len(raw):
            # Check for UTF-8 encoded surrogate (ED A0 80 - ED BF BF)
            if raw[i] == 0xED and (raw[i+1] & 0xF0) == 0xA0:
                i += 3  # skip 3-byte surrogate
                continue
        cleaned.append(raw[i])
        i += 1
    return bytes(cleaned)


def _parse_rss_entry(entry: ET.Element) -> dict | None:
    """解析 Atom RSS entry 为信号格式。"""
    def _text(tag: str) -> str:
        xpath = "{%s}%s" % (ATOM_NS, tag)
        el = entry.find(xpath)
        return el.text.strip() if el is not None and el.text else ""

    title = _text("title")
    if len(title) < 10:
        return None

    link_el = entry.find(f"{{{ATOM_NS}}}link")
    url = link_el.get("href", "") if link_el is not None else ""

    author_el = entry.find(f"{{{ATOM_NS}}}author")
    author = ""
    if author_el is not None:
        name_el = author_el.find(f"{{{ATOM_NS}}}name")
        author = name_el.text.strip() if name_el is not None and name_el.text else ""

    updated = _text("updated")
    post_id = _text("id").split("/")[-1] if _text("id") else ""

    # 从 title 提取粗略评论数 (如 "[123 comments]")
    comments = 0
    cm = re.search(r"\[(\d+)\s*comments?\]", title, re.IGNORECASE)
    if cm:
        comments = int(cm.group(1))
        title = re.sub(r"\s*\[\d+\s*comments?\]", "", title).strip()

    return {
        "id": f"reddit-{post_id}" if post_id else f"reddit-{re.sub(r'[^\\w\\-]', '', title[:30])}",
        "title": title,
        "url": url,
        "source": "Reddit",
        "source_key": "reddit",
        "signal_type": "post",
        "discussion_count": comments,
        "engagement": {
            "comments": comments,
            "total": comments * 5 + 1,
        },
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "raw_created_at": updated,
        "summary": f"[Reddit] {title[:80]}",
        "tags": [],
        "author": author,
    }


def _fetch_subreddit(sub: str) -> list[dict]:
    """获取子版块 RSS 热帖 (hot.rss 端点)。"""
    url = f"https://www.reddit.com/r/{sub}/hot.rss?limit=25"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code == 429:
            print(f"[Reddit] r/{sub} 被限速, 等待 10s...")
            time.sleep(10)
            resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()

        raw = _clean_xml(resp.content)
        root = ET.fromstring(raw)
        entries = root.findall(f"{{{ATOM_NS}}}entry")

        signals = []
        for entry in entries:
            s = _parse_rss_entry(entry)
            if s:
                signals.append(s)
        return signals
    except requests.RequestException as e:
        print(f"[Reddit] r/{sub} 请求失败: {e}")
        return []
    except ET.ParseError as e:
        print(f"[Reddit] r/{sub} XML 解析失败: {e}")
        return []


def collect(date_str: str | None = None) -> list[dict]:
    """采集 5 个子版块 RSS 热帖, 去重取 top 40。"""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    seen: set[str] = set()
    signals: list[dict] = []

    for i, sub in enumerate(SUBREDDITS):
        if i > 0:
            time.sleep(8)  # Reddit RSS 限速严格, 需较长间隔
        posts = _fetch_subreddit(sub)
        count = 0
        for p in posts:
            if p["id"] not in seen:
                seen.add(p["id"])
                signals.append(p)
                count += 1
        print(f"[Reddit] r/{sub}: {count} 条信号")

    signals.sort(key=lambda s: s["engagement"]["total"], reverse=True)
    signals = signals[:40]

    print(f"[Reddit] 总计: {len(signals)} 条 (via RSS)")
    return signals


def save_raw(signals: list[dict], date_str: str) -> None:
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "reddit (via RSS)",
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
