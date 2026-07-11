"""
产品动态通用采集器
数据源: RSS/Atom feeds（配置驱动，覆盖 OpenAI/Anthropic/Vercel 等 12+ 产品 blog）
采集内容: 近 3 天发布的博客/更新/changelog
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

try:
    import feedparser
except ImportError:
    feedparser = None  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"
CONFIG_PATH = ROOT / "config.json"

TZ_SHANGHAI = timezone(timedelta(hours=8))
HEADERS = {"User-Agent": "AimFast-Dev/2.3 (+https://aimfast.dev)"}


def _load_sources() -> list[dict]:
    """从 config.json 读取产品 changelog 源列表。"""
    try:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return cfg.get("product_changelogs", [])
    except (json.JSONDecodeError, OSError) as e:
        print(f"[Changelogs] config.json 读取失败: {e}")
        return []


def _to_signal(entry: dict, source: dict) -> dict | None:
    """将 feed entry 转为标准信号格式。"""
    title = entry.get("title", "").strip()
    url = entry.get("link", "")
    summary = entry.get("summary", "") or entry.get("description", "")

    if len(title) < 5:
        return None

    # 清理 HTML 摘要
    if summary:
        import re
        summary = re.sub(r"<[^>]+>", "", summary)[:200]

    published = entry.get("published_parsed") or entry.get("updated_parsed")
    published_str = ""
    if published:
        try:
            published_str = datetime(*published[:6], tzinfo=timezone.utc).isoformat()
        except (ValueError, TypeError, OverflowError):
            published_str = entry.get("published", "") or entry.get("updated", "")

    source_name = source.get("name", "")
    source_key = source.get("key", "")

    # 从标题和摘要提取 tags
    tags = [source_key, "product-update"]
    text_lower = (title + " " + summary).lower()
    for kw in ["ai", "api", "sdk", "launch", "release", "update", "pricing", "model",
               "open-source", "security", "agent", "chatgpt", "claude", "llm"]:
        if kw in text_lower:
            tags.append(kw)
    tags = list(dict.fromkeys(tags))[:8]  # 去重，最多 8 个

    signal_id = f"changelog-{abs(hash(url or title)) % 10_000_000:07d}"

    return {
        "id": signal_id,
        "title": title[:200],
        "url": url,
        "source": source_name,
        "source_key": source_key,
        "signal_type": "product-update",
        "discussion_count": 0,
        "engagement": {
            "total": 10,  # 产品动态基础权重
        },
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "raw_created_at": published_str,
        "summary": f"[{source_name}] {title[:150]}",
        "tags": tags[:6],
        "author": entry.get("author", ""),
    }


def _days_ago(entry) -> int | None:
    """估算 entry 距今多少天（0=今天, 1=昨天, ...）。"""
    published = entry.get("published_parsed") or entry.get("updated_parsed")
    if not published:
        return None
    try:
        pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return (now - pub_dt).days
    except (ValueError, TypeError, OverflowError):
        return None


def _fetch_feed(feed_url: str) -> list[dict]:
    """解析 RSS/Atom feed，返回 entry 列表。"""
    try:
        resp = requests.get(feed_url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        # feedparser 可以直接从字符串/bytes 解析
        feed = feedparser.parse(resp.content)
        if feed.get("bozo_exception") and not feed.entries:
            print(f"  [feed] 解析异常 ({feed_url[:60]}...): {feed.bozo_exception}")
        return feed.entries
    except requests.RequestException as e:
        print(f"  [feed] 请求失败 ({feed_url[:60]}...): {e}")
        return []
    except Exception as e:
        print(f"  [feed] 解析失败 ({feed_url[:60]}...): {e}")
        return []


def collect(date_str: str | None = None) -> list[dict]:
    """采集所有产品 changelog 源，去重取 top 60。"""
    if feedparser is None:
        print("[Changelogs] feedparser 未安装 — pip install feedparser")
        return []

    sources = _load_sources()
    if not sources:
        print("[Changelogs] config 中无 product_changelogs 配置")
        return []

    seen_urls: set[str] = set()
    signals: list[dict] = []

    for src in sources:
        name = src.get("name", src.get("key", "?"))
        feed_url = src.get("feed", "")
        if not feed_url:
            print(f"[Changelogs] {name}: 跳过（无 feed URL）")
            continue

        entries = _fetch_feed(feed_url)
        count = 0
        for entry in entries:
            age = _days_ago(entry)
            if age is not None and age > 3:
                continue  # 超过 3 天的忽略

            sig = _to_signal(entry, src)
            if sig is None:
                continue
            url = sig["url"]
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)
            signals.append(sig)
            count += 1
        print(f"[Changelogs] {name}: {count} 条 (近 3 天)")

    # 按发布日期降序
    signals.sort(key=lambda s: s.get("raw_created_at", ""), reverse=True)
    signals = signals[:60]

    print(f"[Changelogs] 总计: {len(signals)} 条（去重后）")
    return signals


def save_raw(signals: list[dict], date_str: str) -> None:
    """保存到 ./raw/YYYY-MM-DD/changelogs.json"""
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "product-changelogs",
        "count": len(signals),
        "signals": signals,
    }
    path = dir_path / "changelogs.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[Changelogs] {len(signals)} 条信号 → {path}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
