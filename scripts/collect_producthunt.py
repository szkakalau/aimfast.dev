"""
Product Hunt 信号采集
数据源: Product Hunt RSS Feed (Atom XML)
采集内容: 当日新品 + 描述 + 链接
"""
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"

TZ_SHANGHAI = timezone(timedelta(hours=8))
PH_FEED_URL = "https://www.producthunt.com/feed"


def _parse_atom_feed(xml_text: str) -> list[dict]:
    """解析 Atom XML feed 为条目列表。"""
    entries = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        print(f"[PH] XML 解析失败: {e}")
        return entries

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for entry in root.findall("atom:entry", ns):
        title_el = entry.find("atom:title", ns)
        link_el = entry.find("atom:link", ns)
        published_el = entry.find("atom:published", ns)
        content_el = entry.find("atom:content", ns)
        author_el = entry.find("atom:author", ns)

        title = title_el.text.strip() if title_el is not None and title_el.text else ""
        link = link_el.get("href", "") if link_el is not None else ""
        published = published_el.text.strip() if published_el is not None and published_el.text else ""
        description = ""
        if content_el is not None and content_el.text:
            # 提取纯文本描述（去掉 HTML 标签）
            import re
            desc_text = re.sub(r"<[^>]+>", " ", content_el.text)
            desc_text = re.sub(r"\s+", " ", desc_text).strip()
            description = desc_text[:300]

        author = ""
        if author_el is not None:
            name_el = author_el.find("atom:name", ns)
            author = name_el.text.strip() if name_el is not None and name_el.text else ""

        entries.append({
            "title": title,
            "url": link,
            "published": published,
            "description": description,
            "author": author,
        })

    return entries


def _to_signal(entry: dict) -> dict:
    """将 PH feed 条目转为标准信号格式。"""
    title = entry.get("title", "")
    url = entry.get("url", "")
    product_slug = url.rstrip("/").split("/")[-1] if url else ""

    return {
        "id": f"ph-{product_slug}",
        "title": title,
        "url": url,
        "source": "Product Hunt",
        "source_key": "producthunt",
        "signal_type": "product",
        "discussion_count": 0,  # RSS 不包含评论数
        "engagement": {
            "total": 5,  # PH 新品默认基础权重
        },
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "raw_published": entry.get("published", ""),
        "summary": f"[Product Hunt] {title}: {entry.get('description', '')[:120]}",
        "tags": ["product-launch"],
        "author": entry.get("author", ""),
    }


def collect(date_str: str | None = None) -> list[dict]:
    """
    采集 Product Hunt 当日新品（通过 RSS Feed）。
    筛选今日发布的产品，去重后取 top 40。
    """
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")

    try:
        resp = requests.get(PH_FEED_URL, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[PH] RSS Feed 请求失败: {e}")
        return []

    entries = _parse_atom_feed(resp.text)
    print(f"[PH] RSS 获取 {len(entries)} 条产品")

    signals = []
    for entry in entries:
        published = entry.get("published", "")
        # 只取今天的发布
        if published.startswith(today):
            signal = _to_signal(entry)
            signals.append(signal)

    # 若今天新品不足，放宽到近 3 天
    if len(signals) < 10:
        print(f"[PH] 今日新品仅 {len(signals)} 条，扩展至近 3 天")
        three_days = (datetime.now(TZ_SHANGHAI) - timedelta(days=3)).strftime("%Y-%m-%d")
        for entry in entries:
            published = entry.get("published", "")
            if published >= three_days and published < today:
                signal = _to_signal(entry)
                signals.append(signal)

    signals = signals[:40]

    print(f"[PH] 采集完成: {len(signals)} 条")
    return signals


def save_raw(signals: list[dict], date_str: str) -> None:
    """保存原始采集数据到 ./raw/YYYY-MM-DD/producthunt.json"""
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "producthunt",
        "count": len(signals),
        "signals": signals,
    }
    path = dir_path / "producthunt.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[PH] {len(signals)} 条信号 → {path}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
