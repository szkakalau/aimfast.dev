"""
Reddit 消费者版块信号采集 (v2.1 — C 端信号源)
数据源: Reddit RSS feeds (公开免费, hot.rss 端点可用)
采集内容: 12 个消费者向子版块热帖 — 产品推荐 / 生活方式 / 购买决策 / 工具分享
与 collect_reddit.py 的区别: 该脚本专门面向 C 端消费者子版块,
                         而非编程/ML/创业等开发者子版块
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

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AimFast-Dev/2.0; +https://aimfast.dev)"}

# 消费者向子版块 — 按价值优先级排序 (前 10 个是最重要的)
# Reddit RSS 限速严格: 每请求间隔 8 秒, 分批采集以避免全量 429
SUBREDDITS_PRIORITY = [
    # ── P0: 最高价值 (产品推荐 + 大流量) ──
    "BuyItForLife",        # 耐用品推荐 (290 万会员) — 消费者付费意愿最强
    "InternetIsBeautiful", # 有趣的网站/产品 (1700 万会员) — 病毒传播潜力
    "digitalnomad",        # 数字游民生活方式 (220 万会员) — 工具/服务需求
    "homeautomation",      # 智能家居 (290 万会员) — IoT 消费
    "headphones",          # 耳机 (120 万会员) — 音频消费
    # ── P1: 高价值 (生活决策 + 硬件) ──
    "gadgets",             # 消费电子 (260 万会员) — 硬件产品
    "personalfinance",     # 个人理财 (2100 万会员) — 金融工具
    "solotravel",          # 独自旅行 (360 万会员) — 旅行工具/App
    "macapps",             # Mac App 推荐 (13 万会员) — 桌面工具
    "MechanicalKeyboards", # 机械键盘 (140 万会员) — 外设硬件
    "Frugal",              # 省钱技巧 (380 万会员) — 省钱工具
    "minimalism",          # 极简主义生活方式 (130 万会员)
    # ── P2: 补充 (垂直品类) ──
    "androidapps",         # Android App 推荐 (30 万会员)
    "iosapps",             # iOS App 推荐 (14 万会员)
    "selfhosted",          # 自托管服务 (33 万会员)
    "onebag",              # 极简旅行装备 — 实物产品
]

# Reddit RSS 限速配置
RSS_DELAY_S = 8          # 子版块间基础间隔
RSS_RETRY_DELAY_S = 30   # 429 后的重试等待

ATOM_NS = "http://www.w3.org/2005/Atom"


def _clean_xml(raw: bytes) -> bytes:
    """移除 XML 中的非法 surrogate 字符 (U+D800-U+DFFF)。"""
    cleaned = bytearray()
    i = 0
    while i < len(raw):
        if i + 2 < len(raw):
            if raw[i] == 0xED and (raw[i + 1] & 0xF0) == 0xA0:
                i += 3
                continue
        cleaned.append(raw[i])
        i += 1
    return bytes(cleaned)


def _parse_rss_entry(entry: ET.Element, subreddit: str) -> dict | None:
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

    # 提取投票数 (RSS feed 通常不含 votes, 用评论数估算)
    estimated_votes = max(1, comments * 3)

    # 标记 C 端类别
    tags = [subreddit, "consumer"]

    return {
        "id": f"redditc-{post_id}" if post_id else f"redditc-{re.sub(r'[^\\w\\-]', '', title[:30])}",
        "title": title,
        "url": url,
        "source": f"Reddit r/{subreddit}",
        "source_key": "reddit-consumer",
        "signal_type": "consumer_post",
        "discussion_count": comments,
        "engagement": {
            "comments": comments,
            "votes": estimated_votes,
            "total": comments * 5 + estimated_votes,
        },
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "raw_created_at": updated,
        "summary": f"[Reddit r/{subreddit}] {title[:100]}",
        "tags": tags,
        "author": author,
        "subreddit": subreddit,
    }


def _fetch_subreddit(sub: str) -> list[dict]:
    """获取子版块 RSS 热帖 (hot.rss 端点)。"""
    url = f"https://www.reddit.com/r/{sub}/hot.rss?limit=20"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code == 429:
            print(f"[Reddit-C] r/{sub} 被限速, 等待 10s...")
            time.sleep(10)
            resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code == 404:
            print(f"[Reddit-C] r/{sub} 不存在或已设为私有")
            return []
        resp.raise_for_status()

        raw = _clean_xml(resp.content)
        root = ET.fromstring(raw)
        entries = root.findall(f"{{{ATOM_NS}}}entry")

        signals = []
        for entry in entries:
            s = _parse_rss_entry(entry, sub)
            if s:
                signals.append(s)
        return signals
    except requests.RequestException as e:
        print(f"[Reddit-C] r/{sub} 请求失败: {e}")
        return []
    except ET.ParseError as e:
        print(f"[Reddit-C] r/{sub} XML 解析失败: {e}")
        return []


def collect(date_str: str | None = None) -> list[dict]:
    """采集消费者子版块 RSS 热帖 (优先 P0/P1), 去重取 top 60。"""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    seen: set[str] = set()
    signals: list[dict] = []
    consecutive_429 = 0

    for i, sub in enumerate(SUBREDDITS_PRIORITY):
        if i > 0:
            # 遇到连续 429 时延长等待
            wait = RSS_DELAY_S + (consecutive_429 * 10)
            time.sleep(wait)

        posts = _fetch_subreddit(sub)
        count = 0
        for p in posts:
            if p["id"] not in seen:
                seen.add(p["id"])
                signals.append(p)
                count += 1
        if count > 0:
            print(f"[Reddit-C] r/{sub}: {count} 条信号")
            consecutive_429 = 0
        else:
            consecutive_429 += 1
            if consecutive_429 >= 3:
                print(f"[Reddit-C] 连续 {consecutive_429} 个子版块无数据, 可能被全局限速, 等待 {RSS_RETRY_DELAY_S}s...")
                time.sleep(RSS_RETRY_DELAY_S)
                consecutive_429 = 0

    # 按互动量排序, 取 Top 60
    signals.sort(key=lambda s: s["engagement"]["total"], reverse=True)
    signals = signals[:60]

    # 统计子版块分布
    sub_counts: dict[str, int] = {}
    for s in signals:
        sub = s.get("subreddit", "unknown")
        sub_counts[sub] = sub_counts.get(sub, 0) + 1

    print(f"[Reddit-C] 总计: {len(signals)} 条 (via {len(sub_counts)} 个子版块 RSS)")
    return signals


def save_raw(signals: list[dict], date_str: str) -> None:
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "reddit-consumer (via RSS)",
        "subreddits": SUBREDDITS_PRIORITY,
        "count": len(signals),
        "signals": signals,
    }
    path = dir_path / "reddit_consumer.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[Reddit-C] {len(signals)} 条信号 → {path}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
