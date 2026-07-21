"""
OSChina 开源中国信号采集 (v1.0)
数据源: OSChina RSS (oschina.net/news/rss)
采集内容: 中文开源技术社区最新新闻 — 含安全漏洞、开源动态、技术趋势

OSChina 是中文最大的开源技术社区之一。
RSS 输出分类新闻（综合新闻、软件更新、行业资讯、安全漏洞等），
是中文开发者生态的重要补充信源。
"""
import json
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"

TZ_SHANGHAI = timezone(timedelta(hours=8))

OSCHINA_RSS = "https://www.oschina.net/news/rss"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AimFast-Dev/2.3; +https://aimfast.dev)"}

MAX_SIGNALS = 30


def _extract_tags(title: str, description: str, category: str) -> list[str]:
    """从标题、描述和分类中提取标签。"""
    text = f"{title} {description} {category}".lower()
    tags = []

    keyword_map = {
        "AI/大模型": ["ai", "大模型", "llm", "gpt", "claude", "深度学习", "机器学习", "模型", "智能"],
        "安全": ["漏洞", "安全", "攻击", "cve", "加密", "注入"],
        "开源": ["开源", "open source", "apache", "mit", "gpl", "linux"],
        "数据库": ["数据库", "sql", "mysql", "postgresql", "redis", "向量"],
        "前端": ["前端", "react", "vue", "typescript", "javascript", "css"],
        "后端": ["后端", "go", "rust", "java", "api", "微服务", "k8s"],
        "编程语言": ["python", "java", "golang", "rust", "php", "c++"],
        "云原生": ["云原生", "容器", "docker", "kubernetes", "devops", "serverless"],
    }

    for category_name, keywords in keyword_map.items():
        for kw in keywords:
            if kw in text:
                tags.append(category_name)
                break

    return list(set(tags))[:5]


def _to_signal(item: ET.Element) -> dict | None:
    """将 RSS item 转为标准信号格式。"""
    title_el = item.find("title")
    link_el = item.find("link")
    desc_el = item.find("description")
    cat_el = item.find("category")
    pubdate_el = item.find("pubDate")

    title = title_el.text.strip() if title_el is not None and title_el.text else ""
    link = link_el.text.strip() if link_el is not None and link_el.text else ""
    description = desc_el.text.strip() if desc_el is not None and desc_el.text else ""
    category = cat_el.text.strip() if cat_el is not None and cat_el.text else ""
    pubdate = pubdate_el.text.strip() if pubdate_el is not None and pubdate_el.text else ""

    if len(title) < 5:
        return None

    # 清理 HTML 标签
    clean_desc = re.sub(r"<[^>]+>", "", description)[:200]

    # 提取标签
    tags = _extract_tags(title, clean_desc, category)
    tags.append("oschina")

    # 估算热度
    is_security = "安全" in tags
    is_ai = "AI/大模型" in tags
    heat_score = 5 + (10 if is_security else 0) + (8 if is_ai else 0) + len(tags) * 2

    news_id = re.search(r"/news/(\d+)", link)
    signal_id = f"oschina-{news_id.group(1)}" if news_id else f"oschina-{abs(hash(title)) % 10_000_000:07d}"

    return {
        "id": signal_id,
        "title": title[:200],
        "url": link,
        "source": "OSChina",
        "source_key": "oschina",
        "signal_type": "news",
        "discussion_count": 0,
        "engagement": {
            "category": category,
            "total": max(1, heat_score),
        },
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "raw_created_at": pubdate,
        "summary": f"[OSChina/{category}] {title[:100]}" + (f" — {clean_desc[:80]}" if clean_desc else ""),
        "tags": tags[:6],
        "author": "",
        "extra": {
            "category": category,
            "description": clean_desc[:300],
        },
    }


def collect(date_str: str | None = None) -> list[dict]:
    """采集 OSChina 最新开源技术新闻。"""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    signals: list[dict] = []

    try:
        resp = requests.get(OSCHINA_RSS, headers=HEADERS, timeout=20)
        resp.raise_for_status()

        # XML 解析
        root = ET.fromstring(resp.content)
        items = root.findall(".//item")

        for item in items:
            s = _to_signal(item)
            if s:
                signals.append(s)

        # 按分类统计
        cat_counts: dict[str, int] = {}
        for s in signals:
            cat = s.get("extra", {}).get("category", "未知")
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
        for cat, count in sorted(cat_counts.items()):
            print(f"[OSChina] {cat}: {count} 条")

    except (requests.RequestException, ET.ParseError) as e:
        print(f"[OSChina] RSS 获取失败: {e}")
        return []

    signals = signals[:MAX_SIGNALS]

    tag_counts: dict[str, int] = {}
    for s in signals:
        for t in s.get("tags", []):
            if t != "oschina":
                tag_counts[t] = tag_counts.get(t, 0) + 1

    print(f"[OSChina] 总计: {len(signals)} 条 | 热门标签: {', '.join(f'{t}({c})' for t,c in sorted(tag_counts.items(), key=lambda x:x[1], reverse=True)[:6])}")
    return signals


def save_raw(signals: list[dict], date_str: str) -> None:
    """保存到 ./raw/YYYY-MM-DD/oschina.json"""
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "oschina (RSS)",
        "count": len(signals),
        "signals": signals,
    }
    path = dir_path / "oschina.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OSChina] {len(signals)} 条信号 → {path}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
