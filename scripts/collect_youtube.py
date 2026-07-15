"""
YouTube 技术频道信号采集
数据源: YouTube RSS feeds (公开免费, 无需认证)
采集内容: 技术 YouTuber 最新视频 — 内容趋势 + 技术布道信号

YouTube 的频道 RSS 格式:
  https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}
每个频道有唯一 ID 或 handle。RSS 返回最新 15 个视频。
"""
import json
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"

TZ_SHANGHAI = timezone(timedelta(hours=8))

HEADERS = {"User-Agent": "AimFast-Dev/2.0 (+https://aimfast.dev)"}

ATOM_NS = "http://www.w3.org/2005/Atom"
MEDIA_NS = "http://search.yahoo.com/mrss/"

# 技术频道 — 聚焦 AI、开发工具、独立开发、技术趋势
# 仅包含已验证 RSS 可用的频道 (2026-07-16 实测)
# YouTube RSS 格式: https://www.youtube.com/feeds/videos.xml?channel_id={ID}
# 注意: YouTube 已逐步限制 RSS，部分频道关闭此功能
TRACKED_CHANNELS = [
    # AI / ML 研究 (已验证 ✅)
    {"id": "UCXZCJLdBC09xxGZ6gcdrc6A", "name": "Two Minute Papers", "focus": "AI research highlights"},
    {"id": "UCWN3xxRkmTPmbKwht9FuE5A", "name": "Yannic Kilcher", "focus": "AI/ML paper reviews"},
    {"id": "UCBa659QWEk1AI4Tg--mrJ2A", "name": "Tom Scott (tech explainers)", "focus": "tech explainers"},
    # 编程教育 (已验证 ✅)
    {"id": "UC8butISFwT-Wl7EV0hUK0BQ", "name": "freeCodeCamp", "focus": "programming education"},
    {"id": "UCsBjURrPvezykJAnRlaoLFQ", "name": "Fireship", "focus": "quick dev news & tutorials"},
    # 全栈 / 独立开发 (已验证 ✅)
    {"id": "UCcabW3x2I8jkSo9pFZgUKHA", "name": "Theo - t3.gg", "focus": "web dev & tech industry"},
    {"id": "UC-QHkN2hnlz47fSWFBJ8eSA", "name": "Jack Herrington", "focus": "fullstack tutorials"},
    # 开源/Infra (已验证 ✅)
    {"id": "UCZCFT0GHZ5TbB72fF6yQFSQ", "name": "Cloudflare", "focus": "infra & dev tools"},
    {"id": "UC8ENy4JaXk2Ch7zXY_2F4hA", "name": "Hugging Face", "focus": "AI platform & research"},
    # 独立开发者访谈
    {"id": "UCtxCXg-UvSnNPOOqYFhpx-Q", "name": "Indie Hackers", "focus": "indie founder interviews"},
    {"id": "UCR1cVJbjM2ZXnMJj7nBH6LQ", "name": "Levels.io", "focus": "indie hacking lifestyle"},
]


def _clean_xml(raw: bytes) -> bytes:
    """移除 XML 中的非法 surrogate 字符。"""
    cleaned = bytearray()
    i = 0
    while i < len(raw):
        if i + 2 < len(raw):
            if raw[i] == 0xED and (raw[i+1] & 0xF0) == 0xA0:
                i += 3
                continue
        cleaned.append(raw[i])
        i += 1
    return bytes(cleaned)


def _fetch_channel(channel_id: str) -> list[dict]:
    """获取 YouTube 频道的 RSS feed。"""
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        raw = _clean_xml(resp.content)
        root = ET.fromstring(raw)

        signals = []
        for entry in root.findall(f"{{{ATOM_NS}}}entry"):
            title_el = entry.find(f"{{{ATOM_NS}}}title")
            link_el = entry.find(f"{{{ATOM_NS}}}link")
            author_el = entry.find(f"{{{ATOM_NS}}}author")
            published_el = entry.find(f"{{{ATOM_NS}}}published")
            updated_el = entry.find(f"{{{ATOM_NS}}}updated")
            media_group = entry.find(f"{{{MEDIA_NS}}}group")

            title = title_el.text.strip() if title_el is not None and title_el.text else ""
            link = link_el.get("href", "") if link_el is not None else ""
            author_name = ""
            if author_el is not None:
                name_el = author_el.find(f"{{{ATOM_NS}}}name")
                author_name = name_el.text.strip() if name_el is not None and name_el.text else ""
            published = published_el.text.strip() if published_el is not None and published_el.text else ""
            updated = updated_el.text.strip() if updated_el is not None and updated_el.text else ""

            if not title or len(title) < 5:
                continue

            # YouTube RSS 没有直接提供观看数/评论数，用视频发布作为信号权重
            # 发布时间越近，信号越强
            hours_ago = 0
            try:
                if published:
                    pub_dt = datetime.strptime(published, "%Y-%m-%dT%H:%M:%S%z")
                    hours_ago = max(0, (datetime.now(TZ_SHANGHAI).replace(tzinfo=None) -
                                       pub_dt.replace(tzinfo=None)).total_seconds() / 3600)
            except (ValueError, TypeError):
                hours_ago = 48  # unknown age, moderate signal

            # 越新的视频信号越强 (24h 内: 10, 72h 内: 5, 更老: 2)
            if hours_ago <= 24:
                freshness_bonus = 10
            elif hours_ago <= 72:
                freshness_bonus = 5
            else:
                freshness_bonus = 2

            video_id = ""
            if link and "v=" in link:
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(link)
                qs = parse_qs(parsed.query)
                video_ids = qs.get("v", [])
                video_id = video_ids[0] if video_ids else ""

            signals.append({
                "id": f"yt-{video_id}" if video_id else f"yt-{hash(title) & 0xFFFFFFFF:08x}",
                "title": title,
                "url": link,
                "source": "YouTube",
                "source_key": "youtube",
                "signal_type": "video",
                "discussion_count": 0,
                "engagement": {
                    "freshness_hours": round(hours_ago, 1),
                    "total": freshness_bonus,
                },
                "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
                "raw_created_at": published or updated,
                "summary": f"[YouTube] {title[:80]}",
                "tags": [],
                "author": author_name,
            })

        return signals
    except (requests.RequestException, ET.ParseError) as e:
        print(f"[YouTube] channel_id={channel_id} 请求失败: {e}")
        return []


def collect(date_str: str | None = None) -> list[dict]:
    """采集 YouTube 技术频道的最近视频。"""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    seen: set[str] = set()
    signals: list[dict] = []

    for i, channel in enumerate(TRACKED_CHANNELS):
        if i > 0:
            time.sleep(2)  # YouTube RSS 限速

        videos = _fetch_channel(channel["id"])
        channel_count = 0
        for v in videos:
            if v["id"] not in seen:
                seen.add(v["id"])
                # 附加频道元信息到 tags
                v["tags"] = [channel["focus"]]
                v["author"] = channel["name"]
                signals.append(v)
                channel_count += 1

        print(f"[YouTube] {channel['name']}: {channel_count} 个视频")

    signals.sort(key=lambda s: s["engagement"]["total"], reverse=True)
    signals = signals[:40]

    print(f"[YouTube] 总计: {len(signals)} 条信号 (来自 {len(TRACKED_CHANNELS)} 个频道)")
    return signals


def save_raw(signals: list[dict], date_str: str) -> None:
    """保存到 ./raw/YYYY-MM-DD/youtube.json"""
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "youtube",
        "count": len(signals),
        "channels_tracked": [c["name"] for c in TRACKED_CHANNELS],
        "signals": signals,
    }
    path = dir_path / "youtube.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[YouTube] → {path}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
