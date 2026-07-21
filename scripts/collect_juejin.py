"""
掘金信号采集 (v1.0)
数据源: 掘金推荐 API (api.juejin.cn)
采集内容: 推荐流热门文章 — 中文开发者社区的最大信源

掘金月活 1000 万+，是中文前端/全栈/AI 开发者的核心社区。
这个采集器弥补了当前中文信源只覆盖 V2EX 和 w2solo 的空白。
"""
import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"

TZ_SHANGHAI = timezone(timedelta(hours=8))

JUEJIN_API = "https://api.juejin.cn/recommend_api/v1/article/recommend_all_feed"
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
}

# ── 采集配置 ──
MAX_PAGES = 4               # 最多翻页数 (每页约 20 条)
PAGE_SIZE = 20              # 每页条数
PAGE_DELAY_S = 2            # 翻页间隔
MAX_SIGNALS = 40            # 最终输出上限


def _fetch_page(cursor: str = "0", limit: int = PAGE_SIZE) -> dict:
    """获取一页掘金推荐流数据。"""
    payload = {
        "id_type": 2,
        "sort_type": 200,   # 200 = 推荐排序
        "cursor": cursor,
        "limit": limit,
    }
    try:
        resp = requests.post(JUEJIN_API, headers=HEADERS, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data.get("err_no") != 0:
            print(f"  [掘金] API 错误: err_no={data.get('err_no')}, msg={data.get('err_msg')}")
            return {"data": [], "cursor": cursor, "has_more": False}
        return data
    except requests.RequestException as e:
        print(f"  [掘金] API 请求失败: {e}")
        return {"data": [], "cursor": cursor, "has_more": False}


def _to_signal(item: dict) -> dict | None:
    """将掘金文章转为标准信号格式。"""
    article = item.get("article_info", {})
    title = article.get("title", "")
    brief = article.get("brief_content", "")

    if len(title) < 5:
        return None

    article_id = article.get("article_id", "")
    user_info = item.get("author_user_info", {})
    author = user_info.get("user_name", "")

    # 标签
    tags = []
    for t in item.get("tags", []):
        tag_name = t.get("tag_name", "")
        if tag_name:
            tags.append(tag_name)

    # 互动指标
    views = article.get("view_count", 0)
    diggs = article.get("digg_count", 0)
    comments = article.get("comment_count", 0)
    collects = article.get("collect_count", 0)
    hot_index = article.get("hot_index", 0)

    # engagement total: 综合浏览量、点赞、评论、收藏、热度
    eng_total = min(hot_index, 200) + min(views // 500, 50) + diggs + comments * 2 + collects * 3

    return {
        "id": f"juejin-{article_id}",
        "title": title,
        "url": f"https://juejin.cn/post/{article_id}",
        "source": "掘金",
        "source_key": "juejin",
        "signal_type": "article",
        "discussion_count": comments,
        "engagement": {
            "views": views,
            "diggs": diggs,
            "comments": comments,
            "collects": collects,
            "hot_index": hot_index,
            "total": max(1, eng_total),
        },
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "raw_created_at": datetime.fromtimestamp(
            int(article.get("ctime", 0)), tz=TZ_SHANGHAI
        ).isoformat() if article.get("ctime") else "",
        "summary": f"[掘金] {title[:100]}" + (f" — {brief[:80]}" if brief else ""),
        "tags": [t for t in tags if t][:6],
        "author": author,
        "extra": {
            "brief": brief[:200],
            "read_time": article.get("read_time", ""),
        },
    }


def collect(date_str: str | None = None) -> list[dict]:
    """采集掘金推荐流热门文章。

    翻页采集，去重，按 hot_index 降序取 top 40。
    """
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    seen: set[str] = set()
    signals: list[dict] = []
    cursor = "0"

    for page in range(MAX_PAGES):
        if page > 0:
            time.sleep(PAGE_DELAY_S)

        data = _fetch_page(cursor=cursor, limit=PAGE_SIZE)
        items = data.get("data", [])
        if not items:
            break

        count = 0
        for item in items:
            # 只处理文章类型 (item_type=2)
            if item.get("item_type") != 2:
                continue
            s = _to_signal(item.get("item_info", {}))
            if s and s["id"] not in seen:
                seen.add(s["id"])
                signals.append(s)
                count += 1

        tag_preview = ", ".join(s["tags"][:3]) if signals and signals[-1]["tags"] else ""
        print(f"[掘金] 第{page+1}页: {count} 条 (cursor={cursor}) {tag_preview}")

        cursor = str(data.get("cursor", "0"))
        if not data.get("has_more", False):
            break

    # 按 hot_index 降序
    signals.sort(key=lambda s: s["engagement"].get("hot_index", 0), reverse=True)
    signals = signals[:MAX_SIGNALS]

    # 统计标签分布
    tag_counts: dict[str, int] = {}
    for s in signals:
        for t in s.get("tags", []):
            tag_counts[t] = tag_counts.get(t, 0) + 1
    top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:8]

    print(f"[掘金] 总计: {len(signals)} 条 | 热门标签: {', '.join(f'{t}({c})' for t,c in top_tags)}")
    return signals


def save_raw(signals: list[dict], date_str: str) -> None:
    """保存到 ./raw/YYYY-MM-DD/juejin.json"""
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "juejin (recommend_all_feed API)",
        "pages": MAX_PAGES,
        "count": len(signals),
        "signals": signals,
    }
    path = dir_path / "juejin.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[掘金] {len(signals)} 条信号 → {path}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
