"""
Reddit 消费者版块信号采集 (v3.0 — 429 防护增强)
数据源: Reddit RSS + JSON API 降级
采集内容: 16 个消费者向子版块热帖 — 产品推荐 / 生活方式 / 购买决策 / 工具分享

v3.0 变更 (429 防护):
  1. UA 轮换池 — 5 个真实浏览器 UA, 每个请求随机选一个
  2. 指数退避 — 429 时 15s → 45s → 90s 递进重试, 最多 3 次
  3. 批量冷却 — 每 5 个 sub 后额外等待 60s
  4. JSON API 降级 — 连续 2 个 sub RSS 空结果时切换到 .json 端点
"""
import json
import random
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"

TZ_SHANGHAI = timezone(timedelta(hours=8))

# ── UA 轮换池 (v3.0) ──
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
]

# ── 限速配置 (v3.0 调整) ──
RSS_DELAY_S = 12              # 子版块间基础间隔 (8s → 12s)
BATCH_SIZE = 5                # 每 N 个 sub 后长冷却
BATCH_COOLDOWN_S = 60         # 批量冷却时间
MAX_RETRIES = 3               # 429 最大重试次数
RETRY_DELAYS = [15, 45, 90]   # 指数退避序列 (秒)
JSON_FALLBACK_THRESHOLD = 2   # 连续 RSS 空结果 N 次后切换到 JSON API

# 消费者向子版块 — 按价值优先级排序
SUBREDDITS_PRIORITY = [
    # ── P0: 最高价值 (产品推荐 + 大流量) ──
    "BuyItForLife",        # 耐用品推荐 (290 万会员)
    "InternetIsBeautiful", # 有趣的网站/产品 (1700 万会员)
    "digitalnomad",        # 数字游民生活方式 (220 万会员)
    "homeautomation",      # 智能家居 (290 万会员)
    "headphones",          # 耳机 (120 万会员)
    # ── P1: 高价值 (生活决策 + 硬件) ──
    "gadgets",             # 消费电子 (260 万会员)
    "personalfinance",     # 个人理财 (2100 万会员)
    "solotravel",          # 独自旅行 (360 万会员)
    "macapps",             # Mac App 推荐 (13 万会员)
    "MechanicalKeyboards", # 机械键盘 (140 万会员)
    "Frugal",              # 省钱技巧 (380 万会员)
    "minimalism",          # 极简主义生活方式 (130 万会员)
    # ── P2: 补充 (垂直品类) ──
    "androidapps",         # Android App 推荐 (30 万会员)
    "iosapps",             # iOS App 推荐 (14 万会员)
    "selfhosted",          # 自托管服务 (33 万会员)
    "onebag",              # 极简旅行装备
]

ATOM_NS = "http://www.w3.org/2005/Atom"


def _random_ua() -> str:
    return random.choice(_USER_AGENTS)


def _clean_xml(raw: bytes) -> bytes:
    """移除 XML 中的非法 surrogate 字符 (U+D800-U+DFFF)."""
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
    """解析 Atom RSS entry 为信号格式."""
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

    comments = 0
    cm = re.search(r"\[(\d+)\s*comments?\]", title, re.IGNORECASE)
    if cm:
        comments = int(cm.group(1))
        title = re.sub(r"\s*\[\d+\s*comments?\]", "", title).strip()

    estimated_votes = max(1, comments * 3)

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
        "tags": [subreddit, "consumer"],
        "author": author,
        "subreddit": subreddit,
    }


def _parse_json_post(post: dict, subreddit: str) -> dict | None:
    """解析 Reddit JSON API 的 post 为信号格式 (RSS 降级路径)."""
    data = post.get("data", {})
    title = data.get("title", "")
    if len(title) < 10:
        return None

    post_id = data.get("id", "")
    permalink = data.get("permalink", "")
    url = f"https://www.reddit.com{permalink}" if permalink else data.get("url", "")
    author = data.get("author", "")
    comments = data.get("num_comments", 0)
    score = data.get("score", 0)
    created_utc = data.get("created_utc", 0)
    updated = datetime.fromtimestamp(created_utc, tz=TZ_SHANGHAI).isoformat() if created_utc else ""

    cm = re.search(r"\[(\d+)\s*comments?\]", title, re.IGNORECASE)
    if cm:
        title = re.sub(r"\s*\[\d+\s*comments?\]", "", title).strip()

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
            "votes": score,
            "total": comments * 5 + score + 1,
        },
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "raw_created_at": updated,
        "summary": f"[Reddit r/{subreddit}] {title[:100]}",
        "tags": [subreddit, "consumer"],
        "author": author,
        "subreddit": subreddit,
    }


def _fetch_rss(sub: str) -> list[dict]:
    """通过 RSS 端点获取子版块热帖."""
    url = f"https://www.reddit.com/r/{sub}/hot.rss?limit=20"
    resp = requests.get(url, headers={"User-Agent": _random_ua()}, timeout=30)
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


def _fetch_json(sub: str) -> list[dict]:
    """通过 JSON API 获取子版块热帖 (RSS 降级路径)."""
    url = f"https://www.reddit.com/r/{sub}/hot.json?limit=20"
    resp = requests.get(url, headers={"User-Agent": _random_ua()}, timeout=30)
    resp.raise_for_status()

    data = resp.json()
    posts = data.get("data", {}).get("children", [])

    signals = []
    for child in posts:
        s = _parse_json_post(child, sub)
        if s:
            signals.append(s)
    return signals


def _fetch_with_retry(sub: str, use_json: bool = False) -> list[dict]:
    """带指数退避重试的获取逻辑.
    当 RSS 429 重试耗尽时自动尝试 JSON API 作为最后降级路径."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            if use_json:
                return _fetch_json(sub)
            else:
                return _fetch_rss(sub)
        except requests.HTTPError as e:
            status = e.response.status_code if hasattr(e, 'response') else 0
            if status == 429:
                if attempt < MAX_RETRIES:
                    wait = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
                    print(f"  [Reddit-C] r/{sub} 429 rate limited, waiting {wait}s (attempt {attempt+1}/{MAX_RETRIES})...")
                    time.sleep(wait)
                    continue
                # RSS 429 重试耗尽 → 尝试 JSON API
                elif not use_json:
                    print(f"  [Reddit-C] r/{sub} RSS 429 重试耗尽, 尝试 JSON API...")
                    time.sleep(5)
                    use_json = True
                    attempt = -1  # 重置重试计数
                    continue
            elif status == 404:
                print(f"  [Reddit-C] r/{sub} 不存在或已设为私有")
                return []
            else:
                print(f"  [Reddit-C] r/{sub} HTTP {status}: {e}")
                return []
        except (requests.RequestException, ET.ParseError, json.JSONDecodeError) as e:
            if attempt < MAX_RETRIES:
                wait = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
                print(f"  [Reddit-C] r/{sub} {type(e).__name__}: {e}, retrying in {wait}s...")
                time.sleep(wait)
                if isinstance(e, (ET.ParseError, json.JSONDecodeError)):
                    use_json = True
                continue
            print(f"  [Reddit-C] r/{sub} 最终失败: {e}")
            return []
    return []


def collect(date_str: str | None = None) -> list[dict]:
    """采集消费者子版块热帖, 去重取 top 60."""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    seen: set[str] = set()
    signals: list[dict] = []
    consecutive_empty = 0
    use_json = False

    for i, sub in enumerate(SUBREDDITS_PRIORITY):
        # 基础间隔 + 批量冷却
        if i > 0:
            delay = RSS_DELAY_S
            if i % BATCH_SIZE == 0:
                print(f"[Reddit-C] 已完成 {i}/{len(SUBREDDITS_PRIORITY)} 个子版块, 冷却 {BATCH_COOLDOWN_S}s...")
                delay = BATCH_COOLDOWN_S
            time.sleep(delay)

        posts = _fetch_with_retry(sub, use_json=use_json)
        count = 0
        for p in posts:
            if p["id"] not in seen:
                seen.add(p["id"])
                signals.append(p)
                count += 1

        if count > 0:
            api_label = "JSON" if use_json else "RSS"
            print(f"[Reddit-C] r/{sub}: {count} 条信号 (via {api_label})")
            consecutive_empty = 0
        else:
            consecutive_empty += 1
            print(f"[Reddit-C] r/{sub}: 0 条信号 (未获取到)")
            if consecutive_empty >= JSON_FALLBACK_THRESHOLD and not use_json:
                print(f"[Reddit-C] RSS 连续 {consecutive_empty} 次空结果, 切换到 JSON API...")
                use_json = True

    # 按互动量排序, 取 Top 60
    signals.sort(key=lambda s: s["engagement"]["total"], reverse=True)
    signals = signals[:60]

    # 统计子版块分布
    sub_counts: dict[str, int] = {}
    for s in signals:
        sub = s.get("subreddit", "unknown")
        sub_counts[sub] = sub_counts.get(sub, 0) + 1

    print(f"[Reddit-C] 总计: {len(signals)} 条 (via {len(sub_counts)} 个子版块)")
    return signals


def save_raw(signals: list[dict], date_str: str) -> None:
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "reddit-consumer (via RSS + JSON fallback)",
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
