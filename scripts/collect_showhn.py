"""
Hacker News Show HN 信号采集 (v1.0)
数据源: HN Algolia API (hn.algolia.com) — Show HN tag
采集内容: 独立开发者在 HN 上展示的产品/项目

Show HN 是 HN 的特色板块，独立开发者在这里发布自己做的产品。
这是全球最集中的"独立开发者正在造什么"的信号源。

与主 HN 采集器（collect_hackernews.py）互补：
- collect_hackernews.py → 热门讨论帖（人们在讨论什么）
- collect_showhn.py → 产品发布帖（人们在做/用什么）
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"

TZ_SHANGHAI = timezone(timedelta(hours=8))

HN_ALGOLIA = "https://hn.algolia.com/api/v1"
HN_BASE = "https://news.ycombinator.com/item?id="
HEADERS = {"User-Agent": "AimFast-Dev/2.3 (+https://aimfast.dev)"}

MAX_SIGNALS = 30


def _search_show_hn() -> list[dict]:
    """搜索最近的 Show HN 帖子（按日期降序）。"""
    url = f"{HN_ALGOLIA}/search_by_date"
    params = {
        "query": "Show HN",
        "tags": "story",
        "numericFilters": "points>3",
        "hitsPerPage": 50,
    }
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json().get("hits", [])
    except requests.RequestException as e:
        print(f"  [ShowHN] API 请求失败: {e}")
        return []


def _extract_tech_tags(title: str) -> list[str]:
    """从 Show HN 标题提取技术标签。"""
    title_lower = title.lower()
    tags = []

    keyword_map = {
        "AI": ["ai", "llm", "gpt", "claude", "chatgpt", "copilot", "agent", "model", "prompt", "rag"],
        "DevTools": ["cli", "api", "sdk", "tool", "vscode", "plugin", "extension", "debug", "ide"],
        "Web": ["web", "browser", "react", "vue", "next", "svelte", "css", "html"],
        "Open Source": ["open source", "github", "oss", "free"],
        "Productivity": ["productivity", "workflow", "automation", "note", "task", "calendar"],
        "Database": ["database", "sql", "postgres", "sqlite", "vector", "embedding"],
        "DevOps": ["docker", "kubernetes", "k8s", "deploy", "ci/cd", "cloud", "serverless"],
        "Mobile": ["ios", "android", "app", "flutter", "react native"],
        "Security": ["security", "privacy", "encrypt", "auth", "password"],
        "Finance": ["finance", "crypto", "trading", "payment", "stripe", "bank"],
        "Startup": ["startup", "saas", "yc", "mrr", "revenue", "bootstrap"],
        "NoCode": ["no code", "nocode", "low code", "drag", "visual"],
    }

    for category, keywords in keyword_map.items():
        for kw in keywords:
            if kw in title_lower:
                tags.append(category)
                break

    return tags[:5]


def _to_signal(hit: dict) -> dict | None:
    """将 Show HN 帖转为标准信号格式。"""
    title = hit.get("title", "")
    if len(title) < 8:
        return None

    # 清理 "Show HN: " 前缀
    clean_title = title
    for prefix in ["Show HN: ", "Show HN:", "Show HN - ", "Show HN- "]:
        if clean_title.startswith(prefix):
            clean_title = clean_title[len(prefix):]
            break

    points = hit.get("points", 0) or 0
    num_comments = hit.get("num_comments", 0) or 0
    obj_id = hit.get("objectID", "")
    created = hit.get("created_at", "")
    url = hit.get("url") or f"{HN_BASE}{obj_id}"
    author = hit.get("author", "")

    tech_tags = _extract_tech_tags(title)
    # Show HN 帖热度：高票 + 高评论 = 社区高度关注
    heat_score = points * 2 + num_comments * 3

    return {
        "id": f"showhn-{obj_id}",
        "title": clean_title[:200],
        "url": url,
        "source": "HN Show HN",
        "source_key": "showhn",
        "signal_type": "product-launch",
        "discussion_count": num_comments,
        "engagement": {
            "points": points,
            "comments": num_comments,
            "total": max(1, heat_score),
        },
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "raw_created_at": created,
        "summary": f"[Show HN] {clean_title[:120]} — {points} pts / {num_comments} comments",
        "tags": ["show-hn", "product-launch"] + tech_tags,
        "author": author,
        "extra": {
            "original_title": title,
            "hn_url": f"{HN_BASE}{obj_id}",
        },
    }


def collect(date_str: str | None = None) -> list[dict]:
    """采集 Show HN 最新产品发布。

    按日期降序获取，按热度排序，去重取 top 30。
    """
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    seen: set[str] = set()
    signals: list[dict] = []

    print("[ShowHN] 搜索最新 Show HN 帖子...")
    hits = _search_show_hn()

    for hit in hits:
        # 严格过滤：只取标题明确包含 "Show HN" 的
        title = hit.get("title", "")
        if not title.lower().startswith("show hn"):
            continue
        s = _to_signal(hit)
        if s and s["id"] not in seen:
            seen.add(s["id"])
            signals.append(s)

    # 按热度降序
    signals.sort(key=lambda s: s["engagement"]["total"], reverse=True)
    signals = signals[:MAX_SIGNALS]

    # 统计
    total_points = sum(s["engagement"]["points"] for s in signals)
    total_comments = sum(s["engagement"]["comments"] for s in signals)
    # 标签分布
    tag_counts: dict[str, int] = {}
    for s in signals:
        for t in s.get("tags", []):
            if t not in ("show-hn", "product-launch"):
                tag_counts[t] = tag_counts.get(t, 0) + 1

    print(f"[ShowHN] {len(signals)} 个产品 | 总 {total_points} pts / {total_comments} comments")
    if tag_counts:
        print(f"[ShowHN] 热门标签: {', '.join(f'{t}({c})' for t,c in sorted(tag_counts.items(), key=lambda x:x[1], reverse=True)[:6])}")
    return signals


def save_raw(signals: list[dict], date_str: str) -> None:
    """保存到 ./raw/YYYY-MM-DD/showhn.json"""
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "showhn (HN Algolia API)",
        "count": len(signals),
        "signals": signals,
    }
    path = dir_path / "showhn.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ShowHN] {len(signals)} 条信号 → {path}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
