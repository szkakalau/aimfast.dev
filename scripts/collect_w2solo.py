"""
w2solo 信号采集
数据源: w2solo.com RSS feed (/topics/feed)
采集内容: 独立开发者项目发布、收入分享、出海经验
"""
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

import feedparser
import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"

TZ_SHANGHAI = timezone(timedelta(hours=8))

W2SOLO_RSS = "https://w2solo.com/topics/feed"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# 高价值话题关键词（信号类型分类）
CATEGORY_PATTERNS = [
    ("product-launch", ["发布", "上线", "新项目", "做了", "开发了", "上线了", "开源", "新产品", "首发", "show",
                        "launch", "ship", "release"]),
    ("revenue", ["收入", "赚了", "盈利", "MRR", "ARR", "营收", "付费", "变现", "订阅", "月收入", "日入",
                 "revenue", "profit"]),
    ("going-global", ["出海", "海外", "国际化", "global", "英语", "翻译", "stripe", "国外", "老外", "海外市场"]),
    ("idea-validation", ["想法", "方向", "需求", "验证", "有没有", "会不会", "值不值得", "idea", "validat",
                         "求建议", "请教", "帮忙看"]),
    ("complaint", ["坑", "踩坑", "问题", "失败", "放弃", "倒闭", "教训", "后悔", "太难", "protip",
                   "经验", "反思"]),
]

# 非商业内容过滤词
NON_BUSINESS_FILTER = [
    "政治", "翻墙", "VPN", "科学上网", "色情", "赌博", "盗版", "破解",
    "telegram", "tg", "tg群", "tg频道",  # Telegram 推广多数是非商业引流
    "源码", "陪玩", "游戏", "棋牌",  # 非独立开发者方向
]


def _html_to_text(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html).strip()


def _classify(title: str, desc: str) -> str:
    text = f"{title} {desc}".lower()
    for category, keywords in CATEGORY_PATTERNS:
        if any(kw.lower() in text for kw in keywords):
            return category
    return "discussion"


def _is_signal(title: str, desc: str) -> bool:
    text = f"{title} {desc}".lower()
    return not any(kw.lower() in text for kw in NON_BUSINESS_FILTER)


def _extract_engagement(desc: str) -> dict:
    # 从描述中估算互动量
    likes = 0
    text = desc.lower()
    if "赞" in text:
        m = re.search(r"(\d+)\s*赞", text)
        if m:
            likes = int(m.group(1))
    replies = 0
    if "回复" in text or "评论" in text:
        m = re.search(r"(\d+)\s*(?:回复|评论)", text)
        if m:
            replies = int(m.group(1))
    return {
        "likes": likes,
        "replies": replies,
        "total": likes + replies * 2 + 1,
    }


def collect(date_str: str | None = None) -> list[dict]:
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")

    signals: list[dict] = []
    try:
        resp = requests.get(W2SOLO_RSS, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
    except Exception as e:
        print(f"[w2solo] RSS 获取失败: {e}")
        return signals

    for entry in feed.entries:
        title = entry.get("title", "")
        link = entry.get("link", "")
        desc_html = entry.get("description", "")
        desc = _html_to_text(desc_html)[:500]
        author = entry.get("author", "")

        if not _is_signal(title, desc):
            continue

        topic_id = link.split("/")[-1] if "/" in link else title[:20]
        signal_type = _classify(title, desc)
        engagement = _extract_engagement(desc)

        signals.append({
            "id": f"w2solo-{topic_id}",
            "title": title,
            "url": link,
            "source": "w2solo",
            "source_key": "w2solo",
            "signal_type": signal_type,
            "discussion_count": engagement["replies"],
            "engagement": engagement,
            "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
            "summary": f"[w2solo / {author}] {desc[:200]}",
            "tags": [signal_type, "indie-dev"],
            "author": author,
        })

    signals.sort(key=lambda s: s["engagement"]["total"], reverse=True)
    print(f"[w2solo] {len(signals)} 条信号 (RSS)")

    return signals[:40]


def save_raw(signals: list[dict], date_str: str) -> None:
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "w2solo",
        "count": len(signals),
        "signals": signals,
    }
    path = dir_path / "w2solo.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[w2solo] {len(signals)} 条信号 → {path}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
