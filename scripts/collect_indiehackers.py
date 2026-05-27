"""
独立开发者经济 信号采集
主数据源: Reddit r/SaaS + r/SideProject（MRR、定价、发布讨论）
辅助数据源: Indie Hackers 首页（JS 渲染，提取 server-rendered 元数据）
采集内容: 产品发布 + 收入讨论 + MRR + 定价策略
"""
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"

TZ_SHANGHAI = timezone(timedelta(hours=8))
REDDIT_BASE = "https://www.reddit.com"
IH_BASE = "https://www.indiehackers.com"

HEADERS = {"User-Agent": "KAKAOPC-Intel/1.0 (signal-collector; contact@aimfast.dev)"}


# ─── Reddit 搜索（替代 IH 的信号覆盖）─────────────────

def _search_reddit(subreddit: str, query: str, limit: int = 15) -> list[dict]:
    """在 Reddit 子版搜索，获取 IH 风格的信号（MRR/定价/发布）。"""
    url = f"{REDDIT_BASE}/r/{subreddit}/search.json"
    params = {"q": query, "sort": "new", "restrict_sr": "on", "limit": limit}
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json().get("data", {}).get("children", [])
    except requests.RequestException as e:
        print(f"[IH] Reddit r/{subreddit} search '{query}' 失败: {e}")
        return []


def _reddit_post_to_signal(post_data: dict, subreddit: str) -> dict | None:
    """将 Reddit 搜索结果转为标准信号格式。"""
    d = post_data.get("data", {})
    if not d:
        return None
    title = d.get("title", "")
    if len(title) < 10 or d.get("stickied"):
        return None

    permalink = d.get("permalink", "")
    url = f"https://www.reddit.com{permalink}" if permalink else d.get("url", "")
    comments = d.get("num_comments", 0)
    ups = d.get("ups", 0)

    return {
        "id": f"ih-r-{d.get('id', '')}",
        "title": title.strip(),
        "url": url,
        "source": f"Reddit r/{subreddit}",
        "source_key": "indiehackers",
        "signal_type": "indie_economy",
        "discussion_count": comments,
        "engagement": {
            "ups": ups,
            "comments": comments,
            "total": comments * 3 + ups,
        },
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "raw_created_utc": d.get("created_utc", 0),
        "summary": f"[r/{subreddit}] {title[:100]}（{ups} 赞 / {comments} 评论）",
        "tags": [subreddit, "indie-economy"],
        "author": d.get("author", ""),
    }


# ─── Indie Hackers 首页元数据提取 ─────────────────────

def _scrape_ih_metadata() -> list[dict]:
    """
    从 Indie Hackers 首页提取 server-rendered 元数据。
    虽然 IH 是 Ember SPA，但 meta 标签、JSON-LD、和 server-rendered 的 SEO 内容仍然存在。
    """
    entries: list[dict] = []
    try:
        resp = requests.get(f"{IH_BASE}/", headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return entries
        html = resp.text

        # 1. 提取 JSON-LD 结构化数据
        for match in re.finditer(r'<script type="application/ld\+json">([^<]+)</script>', html):
            try:
                data = json.loads(match.group(1))
                if isinstance(data, list):
                    entries.extend(data)
                elif isinstance(data, dict):
                    entries.append(data)
            except json.JSONDecodeError:
                continue

        # 2. 提取 Open Graph / Twitter meta
        meta_title = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html)
        meta_desc = re.search(r'<meta[^>]+property="og:description"[^>]+content="([^"]+)"', html)

        # 3. 尝试提取 server-rendered 链接（SEO 友好的 <a> 标签中的帖子链接）
        post_links = re.findall(r'<a[^>]+href="(/post/[^"]+)"[^>]*>([^<]+)</a>', html)
        for path, text in post_links:
            text_clean = re.sub(r"<[^>]+>", "", text).strip()
            if len(text_clean) > 5:
                entries.append({
                    "title": text_clean,
                    "url": f"{IH_BASE}{path}",
                    "type": "post_link",
                })

    except requests.RequestException as e:
        print(f"[IH] 首页元数据提取失败: {e}")

    return entries


def _ih_entry_to_signal(entry: dict) -> dict | None:
    """将 IH 元数据条目转为标准信号格式。"""
    title = entry.get("title") or entry.get("name") or ""
    if not title or len(title) < 5:
        return None

    url = entry.get("url", "")
    etype = entry.get("type", "metadata")

    return {
        "id": f"ih-meta-{title.replace(' ', '-')[:50]}",
        "title": title.strip(),
        "url": url or IH_BASE,
        "source": "Indie Hackers",
        "source_key": "indiehackers",
        "signal_type": etype,
        "discussion_count": 0,
        "engagement": {
            "total": 3,
        },
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "summary": f"[Indie Hackers] {title[:100]}",
        "tags": ["indie-economy"],
        "author": entry.get("author", ""),
    }


# ─── 主采集流程 ─────────────────────────────────────

def collect(date_str: str | None = None) -> list[dict]:
    """
    采集独立开发者经济信号。
    通道 1: Reddit r/SaaS + r/SideProject 搜索 MRR/定价/发布关键词
    通道 2: Indie Hackers 首页元数据（补充）
    去重后取 top 40。
    """
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    seen: set[str] = set()
    signals: list[dict] = []

    # 通道 1: Reddit 搜索（核心通道）
    search_queries = {
        "SaaS": ["MRR revenue", "monthly recurring revenue", "pricing strategy", "launched my", "just launched"],
        "SideProject": ["MRR", "revenue report", "just launched", "my first dollar", "pricing help"],
    }

    for sub, queries in search_queries.items():
        for query in queries:
            posts = _search_reddit(sub, query, limit=10)
            for p in posts:
                signal = _reddit_post_to_signal(p, sub)
                if signal and signal["id"] not in seen:
                    seen.add(signal["id"])
                    signals.append(signal)

    reddit_count = len(signals)
    print(f"[IH] Reddit 搜索: {reddit_count} 条独立开发者经济信号")

    # 通道 2: IH 首页元数据（辅助通道）
    ih_entries = _scrape_ih_metadata()
    ih_count = 0
    for entry in ih_entries:
        signal = _ih_entry_to_signal(entry)
        if signal and signal["id"] not in seen:
            seen.add(signal["id"])
            signals.append(signal)
            ih_count += 1
    print(f"[IH] IH 首页元数据: {ih_count} 条")

    # 去重 + 排序
    signals.sort(key=lambda s: s["engagement"]["total"], reverse=True)
    signals = signals[:40]

    print(f"[IH] 总计: {len(signals)} 条（Reddit:{reddit_count} + IH:{ih_count}）")
    return signals


def save_raw(signals: list[dict], date_str: str) -> None:
    """保存原始采集数据。"""
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "indiehackers",
        "note": "独立开发者经济信号 = Reddit r/SaaS+SideProject 搜索 + IH 首页元数据",
        "count": len(signals),
        "signals": signals,
    }
    path = dir_path / "indiehackers.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[IH] {len(signals)} 条信号 → {path}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
