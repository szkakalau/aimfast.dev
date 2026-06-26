"""
豆瓣 C 端信号采集 (v2.1 — 中文消费者市场信号源)
数据源: 豆瓣公开网页 (HTML 解析) + API v2 (备用)
采集内容:
  - 豆瓣电影排行榜 — 消费者文化消费趋势
  - 豆瓣图书 Top250 — 阅读消费趋势
  - 豆瓣小组热门讨论 — 生活方式/消费决策/产品推荐

信号价值: 豆瓣是中文互联网最大的兴趣社区, 用户讨论书籍/电影/音乐/旅行/家居/
         穿搭等消费决策, 是 C 端产品机会的富矿。

限速: 网页请求间隔 5 秒, API 仅作备用。
"""
import json
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from html import unescape

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"

TZ_SHANGHAI = timezone(timedelta(hours=8))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# 豆瓣网页 (HTML 解析 — 限速比 API 宽松)
DOUBAN_WEB = {
    "movie_ranking": "https://movie.douban.com/chart",
    "book_top250": "https://book.douban.com/top250",
    "group_explore": "https://www.douban.com/group/explore",
}

# API v2 备用 (经常被限速)
DOUBAN_API = {
    "movie_in_theaters": "https://api.douban.com/v2/movie/in_theaters",
}


def _fetch_url(url: str, label: str) -> str | None:
    """获取网页 HTML, 带重试。"""
    for attempt in range(2):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code == 200:
                return resp.text
            elif resp.status_code == 429:
                wait = 10 * (attempt + 1)
                print(f"[豆瓣] {label} 被限速, 等待 {wait}s...")
                time.sleep(wait)
            elif resp.status_code == 404:
                print(f"[豆瓣] {label} 页面不存在")
                return None
            else:
                print(f"[豆瓣] {label} HTTP {resp.status_code}")
                return None
        except requests.RequestException as e:
            print(f"[豆瓣] {label} 请求失败: {e}")
            time.sleep(5)
    return None


def _fetch_movie_chart() -> list[dict]:
    """解析豆瓣电影排行榜 HTML。"""
    signals: list[dict] = []

    html = _fetch_url(DOUBAN_WEB["movie_ranking"], "电影排行榜")
    if not html:
        return signals

    # 匹配电影条目: <a href="https://movie.douban.com/subject/NNNNNN/" class="">TITLE</a>
    # 同时匹配评分: <span class="rating_num">X.X</span>
    # 匹配评价人数: <span class="pl">(NNNNN人评价)</span>
    items = re.findall(
        r'<a\s+href="https://movie\.douban\.com/subject/(\d+)/"[^>]*class="[^"]*"[^>]*>'
        r'([^<]+)</a>.*?'
        r'<span\s+class="rating_num"[^>]*>(\d+\.\d+)</span>.*?'
        r'<span\s+class="pl">\((\d+)人评价\)</span>',
        html,
        re.DOTALL,
    )

    # 如果上面正则失败, 用更宽松的匹配
    if not items:
        # 尝试分别匹配
        titles = re.findall(
            r'<a\s+href="https://movie\.douban\.com/subject/(\d+)/"[^>]*>\s*([^<]+?)\s*</a>',
            html,
        )
        ratings = re.findall(r'<span\s+class="rating_num"[^>]*>(\d+\.\d+)</span>', html)
        seen_ids: set[str] = set()
        for i, (movie_id, title) in enumerate(titles[:15]):
            if movie_id in seen_ids:
                continue
            seen_ids.add(movie_id)
            title = unescape(title.strip())
            rating = float(ratings[i]) if i < len(ratings) else 0
            signals.append({
                "id": f"douban-movie-{movie_id}",
                "title": f"豆瓣电影: {title} — ⭐{rating}",
                "url": f"https://movie.douban.com/subject/{movie_id}/",
                "source": "豆瓣电影-排行榜",
                "source_key": "douban",
                "signal_type": "consumer_trend",
                "discussion_count": int(rating * 1000),
                "engagement": {
                    "rating": rating,
                    "total": int(rating * 500),
                },
                "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
                "raw_created_at": "",
                "summary": f"[豆瓣电影] {title} — ⭐{rating}",
                "tags": ["movie", "consumer", "entertainment"],
                "author": "",
            })
    else:
        seen_ids: set[str] = set()
        for movie_id, title, rating, evals in items[:15]:
            if movie_id in seen_ids:
                continue
            seen_ids.add(movie_id)
            title = unescape(title.strip())
            signals.append({
                "id": f"douban-movie-{movie_id}",
                "title": f"豆瓣电影: {title} — ⭐{rating}",
                "url": f"https://movie.douban.com/subject/{movie_id}/",
                "source": "豆瓣电影-排行榜",
                "source_key": "douban",
                "signal_type": "consumer_trend",
                "discussion_count": int(evals),
                "engagement": {
                    "rating": float(rating),
                    "evals": int(evals),
                    "total": int(float(rating) * int(evals) / 100),
                },
                "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
                "raw_created_at": "",
                "summary": f"[豆瓣电影] {title} — ⭐{rating}, {evals} 人评价",
                "tags": ["movie", "consumer", "entertainment"],
                "author": "",
            })

    if signals:
        print(f"[豆瓣] 电影排行榜: {len(signals)} 部")
    return signals


def _fetch_book_top250() -> list[dict]:
    """解析豆瓣图书 Top250 HTML。"""
    signals: list[dict] = []

    html = _fetch_url(DOUBAN_WEB["book_top250"], "图书 Top250")
    if not html:
        return signals

    # 匹配图书条目
    titles = re.findall(
        r'<a\s+href="https://book\.douban\.com/subject/(\d+)/"[^>]*\s+title="([^"]+)"',
        html,
    )
    # 匹配评分
    ratings = re.findall(r'<span\s+class="rating_nums">(\d+\.\d+)</span>', html)
    # 匹配评价人数
    evals_list = re.findall(r'<span\s+class="pl">\((\d+)人评价\)</span>', html)

    seen_ids: set[str] = set()
    for i, (book_id, title) in enumerate(titles[:15]):
        if book_id in seen_ids:
            continue
        seen_ids.add(book_id)
        title = unescape(title.strip())
        rating = float(ratings[i]) if i < len(ratings) else 0
        evals = int(evals_list[i]) if i < len(evals_list) else 0

        signals.append({
            "id": f"douban-book-{book_id}",
            "title": f"豆瓣图书: {title} — ⭐{rating}",
            "url": f"https://book.douban.com/subject/{book_id}/",
            "source": "豆瓣图书-Top250",
            "source_key": "douban",
            "signal_type": "consumer_trend",
            "discussion_count": evals,
            "engagement": {
                "rating": rating,
                "evals": evals,
                "total": int(rating * evals / 50),
            },
            "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
            "raw_created_at": "",
            "summary": f"[豆瓣图书] {title} — ⭐{rating}, {evals} 人评价",
            "tags": ["book", "consumer", "reading"],
            "author": "",
        })

    if signals:
        print(f"[豆瓣] 图书 Top250: {len(signals)} 本")
    return signals


def _fetch_group_topics() -> list[dict]:
    """获取豆瓣小组热门讨论 — 消费决策 & 生活方式。"""
    signals: list[dict] = []

    html = _fetch_url(DOUBAN_WEB["group_explore"], "小组热门")
    if not html:
        return signals

    # 解析话题卡片
    topic_pattern = re.compile(
        r'<a\s+href="https://www\.douban\.com/group/topic/(\d+)/"[^>]*>'
        r'([^<]+)</a>.*?'
        r'(\d+)\s*回应',
        re.DOTALL,
    )
    matches = topic_pattern.findall(html)

    for topic_id, title, replies in matches[:20]:
        title = unescape(title.strip())
        if len(title) < 6:
            continue
        reply_count = int(replies) if replies else 0

        # 标记消费相关话题
        consumer_kw = [
            "推荐", "种草", "值不值", "好用", "买", "分享",
            "经验", "装修", "旅行", "穿搭", "护肤", "数码",
            "家居", "租房", "副业", "省钱", "好物", "测评",
            "对比", "性价比", "神器",
        ]
        is_consumer = any(kw in title for kw in consumer_kw)

        signals.append({
            "id": f"douban-topic-{topic_id}",
            "title": f"豆瓣小组: {title[:80]}",
            "url": f"https://www.douban.com/group/topic/{topic_id}/",
            "source": "豆瓣小组",
            "source_key": "douban",
            "signal_type": "consumer_discussion" if is_consumer else "discussion",
            "discussion_count": reply_count,
            "engagement": {
                "replies": reply_count,
                "total": reply_count * 3,
            },
            "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
            "raw_created_at": "",
            "summary": f"[豆瓣小组] {title[:100]}（{reply_count} 回应）",
            "tags": ["douban-group", "consumer" if is_consumer else "lifestyle"],
            "author": "",
        })

    if signals:
        consumer_count = sum(1 for s in signals if s.get("signal_type") == "consumer_discussion")
        print(f"[豆瓣] 小组热门: {len(signals)} 条 ({consumer_count} 条消费相关)")
    return signals


def collect(date_str: str | None = None) -> list[dict]:
    """采集豆瓣 C 端信号: 电影排行榜 + 图书 Top250 + 小组热门。"""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")

    print(f"\n[豆瓣] 开始采集 C 端信号 (网页解析模式)...")
    signals: list[dict] = []

    # 电影排行榜 (网页解析)
    movie_signals = _fetch_movie_chart()
    signals.extend(movie_signals)
    time.sleep(5)

    # 图书 Top250 (网页解析)
    book_signals = _fetch_book_top250()
    signals.extend(book_signals)
    time.sleep(5)

    # 小组热门
    group_signals = _fetch_group_topics()
    signals.extend(group_signals)

    # 去重 + 排序
    seen: set[str] = set()
    unique: list[dict] = []
    for s in signals:
        if s["id"] not in seen:
            seen.add(s["id"])
            unique.append(s)
    unique.sort(key=lambda s: s["engagement"]["total"], reverse=True)
    unique = unique[:40]

    print(f"[豆瓣] 总计: {len(unique)} 条 C 端信号")
    return unique


def save_raw(signals: list[dict], date_str: str) -> None:
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "douban (Web HTML parse)",
        "count": len(signals),
        "signals": signals,
    }
    path = dir_path / "douban.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[豆瓣] {len(signals)} 条信号 → {path}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
