"""
Google News 信号采集器
数据源: Google News RSS (关键字搜索)
采集内容: AI/dev/工具领域近期新闻
"""
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import quote

import requests

try:
    import feedparser
except ImportError:
    feedparser = None  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"
CONFIG_PATH = ROOT / "config.json"

TZ_SHANGHAI = timezone(timedelta(hours=8))
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AimFast-Dev/2.3; +https://aimfast.dev)"}

def _load_queries() -> list[str]:
    """从 config.json 读取搜索话题，不可用时回退到共享默认值。"""
    try:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return cfg.get("googlenews_queries")
    except (json.JSONDecodeError, OSError):
        pass
    try:
        from scripts.defaults import DEFAULT_GOOGLENEWS_QUERIES
        return DEFAULT_GOOGLENEWS_QUERIES
    except ImportError:
        return []


def _to_signal(entry: dict, query: str) -> dict | None:
    """将 Google News entry 转为标准信号。"""
    title = entry.get("title", "").strip()
    url = entry.get("link", "")

    # Google News title 格式: "Title - Source Name"
    # 提取来源
    source_match = re.search(r"\s+-\s+(.+)$", title)
    publisher = source_match.group(1).strip() if source_match else ""

    if publisher:
        # 从标题中去掉来源后缀
        title = title[: source_match.start()].strip()

    if len(title) < 5:
        return None

    published = entry.get("published_parsed")
    published_str = ""
    if published:
        try:
            published_str = datetime(*published[:6], tzinfo=timezone.utc).isoformat()
        except (ValueError, TypeError, OverflowError):
            published_str = ""
    if not published_str:
        published_str = entry.get("published", "")

    # 从标题提取 tags
    tags = ["googlenews", "news"]
    keywords = ["ai", "api", "sdk", "launch", "release", "startup", "saas",
                "open-source", "agent", "model", "tool", "platform"]
    text_lower = title.lower()
    for kw in keywords:
        if kw in text_lower:
            tags.append(kw)
    tags = list(dict.fromkeys(tags))[:6]

    signal_id = f"gn-{abs(hash(url or title)) % 10_000_000:07d}"

    return {
        "id": signal_id,
        "title": title[:200],
        "url": url,
        "source": "Google News",
        "source_key": "googlenews",
        "signal_type": "news",
        "discussion_count": 0,
        "engagement": {
            "total": 5,
        },
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "raw_created_at": published_str,
        "summary": f"{title[:150]}{' (' + publisher + ')' if publisher else ''}",
        "tags": tags[:6],
        "author": publisher,
    }


def _search_news(query: str) -> list[dict]:
    """搜索 Google News RSS，返回 entries。"""
    url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en-US&gl=US&ceid=US:en"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        if feed.get("bozo_exception") and not feed.entries:
            print(f"  [News] 解析异常: {feed.bozo_exception}")
        return feed.entries
    except Exception as e:
        print(f"  [News] 请求失败 '{query}': {e}")
        return []


def collect(date_str: str | None = None) -> list[dict]:
    """采集 Google News RSS 各话题新闻，去重取 top 30。"""
    if feedparser is None:
        print("[GoogleNews] feedparser 未安装 — pip install feedparser")
        return []

    queries = _load_queries()
    seen_urls: set[str] = set()
    signals: list[dict] = []

    for query in queries:
        entries = _search_news(query)
        count = 0
        for entry in entries:
            sig = _to_signal(entry, query)
            if sig is None:
                continue
            url = sig["url"]
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)
            signals.append(sig)
            count += 1
        print(f"[GoogleNews] '{query[:40]}': {count} 条")

    # 按发布日期降序
    signals.sort(key=lambda s: s.get("raw_created_at", ""), reverse=True)
    signals = signals[:30]

    print(f"[GoogleNews] 总计: {len(signals)} 条（去重后）")
    return signals


def save_raw(signals: list[dict], date_str: str) -> None:
    """保存到 ./raw/YYYY-MM-DD/googlenews.json"""
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "googlenews",
        "count": len(signals),
        "signals": signals,
    }
    path = dir_path / "googlenews.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[GoogleNews] {len(signals)} 条信号 → {path}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
