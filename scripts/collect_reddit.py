"""
Reddit 信号采集 (v2.2 — 429 防护增强)
数据源: Reddit RSS feeds (hot.rss), 降级到 JSON API
采集内容: 11 个开发者向子版块热帖

429 防护策略:
  1. UA 轮换池 — 5 个真实浏览器 UA, 每个请求随机选一个
  2. 指数退避 — 429 时 15s → 45s → 90s 递进重试, 最多 3 次
  3. 批量冷却 — 每 5 个 sub 后额外等待 60s
  4. JSON API 降级 — 连续 2 个 sub RSS 失败时切换到 .json 端点
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

# ── UA 轮换池 (v2.2) ──
# Reddit RSS 对每个 UA 独立限速, 轮换可绕过单 UA 限制
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
]

# ── 限速配置 (v2.2 调整) ──
RSS_DELAY_S = 12              # 子版块间基础间隔 (8s → 12s)
BATCH_SIZE = 5                # 每 N 个 sub 后长冷却
BATCH_COOLDOWN_S = 60         # 批量冷却时间
MAX_RETRIES = 3               # 429 最大重试次数
RETRY_DELAYS = [15, 45, 90]   # 指数退避序列 (秒)
JSON_FALLBACK_THRESHOLD = 2   # 连续 RSS 失败 N 次后切换到 JSON API

SUBREDDITS = [
    "programming",
    "MachineLearning",
    "SideProject",
    "Entrepreneur",
    "SaaS",
    "startups",
    "webdev",
    "ExperiencedDevs",
    "selfhosted",
    "devops",
    "indiehackers",
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


def _parse_rss_entry(entry: ET.Element) -> dict | None:
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


def _parse_json_post(post: dict) -> dict | None:
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

    # 移除标题中的评论数标记
    cm = re.search(r"\[(\d+)\s*comments?\]", title, re.IGNORECASE)
    if cm:
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
            "votes": score,
            "total": comments * 5 + score + 1,
        },
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "raw_created_at": updated,
        "summary": f"[Reddit] {title[:80]}",
        "tags": [],
        "author": author,
    }


def _fetch_rss(sub: str) -> list[dict]:
    """通过 RSS 端点获取子版块热帖."""
    url = f"https://www.reddit.com/r/{sub}/hot.rss?limit=25"
    resp = requests.get(url, headers={"User-Agent": _random_ua()}, timeout=30)
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


def _fetch_json(sub: str) -> list[dict]:
    """通过 JSON API 获取子版块热帖 (RSS 降级路径)."""
    url = f"https://www.reddit.com/r/{sub}/hot.json?limit=25"
    resp = requests.get(url, headers={"User-Agent": _random_ua()}, timeout=30)
    resp.raise_for_status()

    data = resp.json()
    posts = data.get("data", {}).get("children", [])

    signals = []
    for child in posts:
        s = _parse_json_post(child)
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
                    print(f"  [Reddit] r/{sub} 429 rate limited, waiting {wait}s (attempt {attempt+1}/{MAX_RETRIES})...")
                    time.sleep(wait)
                    continue
                # RSS 429 重试耗尽 → 尝试 JSON API
                elif not use_json:
                    print(f"  [Reddit] r/{sub} RSS 429 重试耗尽, 尝试 JSON API...")
                    time.sleep(5)
                    use_json = True
                    attempt = -1  # 重置重试计数
                    continue
            elif status == 404:
                print(f"  [Reddit] r/{sub} 不存在或已设为私有")
                return []
            else:
                print(f"  [Reddit] r/{sub} HTTP {status}: {e}")
                return []
        except (requests.RequestException, ET.ParseError, json.JSONDecodeError) as e:
            if attempt < MAX_RETRIES:
                # 连接/解析失败也重试 (可能是临时问题)
                wait = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
                print(f"  [Reddit] r/{sub} {type(e).__name__}: {e}, retrying in {wait}s...")
                time.sleep(wait)
                # 解析失败时切到 JSON API
                if isinstance(e, (ET.ParseError, json.JSONDecodeError)):
                    use_json = True
                continue
            print(f"  [Reddit] r/{sub} 最终失败: {e}")
            return []
    return []


def collect(date_str: str | None = None) -> list[dict]:
    """采集 11 个子版块, 去重取 top 40."""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    seen: set[str] = set()
    signals: list[dict] = []
    consecutive_empty = 0
    use_json = False

    for i, sub in enumerate(SUBREDDITS):
        # 基础间隔 + 批量冷却
        if i > 0:
            delay = RSS_DELAY_S
            if i % BATCH_SIZE == 0:
                print(f"[Reddit] 已完成 {i}/{len(SUBREDDITS)} 个子版块, 冷却 {BATCH_COOLDOWN_S}s...")
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
            print(f"[Reddit] r/{sub}: {count} 条信号 (via {api_label})")
            consecutive_empty = 0
        else:
            consecutive_empty += 1
            print(f"[Reddit] r/{sub}: 0 条信号 (未获取到)")
            # 连续 2 次空结果 → 切换到 JSON API
            if consecutive_empty >= JSON_FALLBACK_THRESHOLD and not use_json:
                print(f"[Reddit] RSS 连续 {consecutive_empty} 次空结果, 切换到 JSON API...")
                use_json = True

    signals.sort(key=lambda s: s["engagement"]["total"], reverse=True)
    signals = signals[:40]

    sub_counts: dict[str, str] = {}
    for s in signals:
        sub_counts[s["id"]] = s["source"]

    print(f"[Reddit] 总计: {len(signals)} 条 (via RSS/JSON, {len(sub_counts)} 条去重)")
    return signals


def save_raw(signals: list[dict], date_str: str) -> None:
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "reddit (via RSS + JSON fallback)",
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
