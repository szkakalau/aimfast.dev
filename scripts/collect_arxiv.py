"""
ArXiv 论文采集
数据源: arxiv.org API (免费公开, 无需认证)
采集内容: AI/ML 最新论文
"""
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"

TZ_SHANGHAI = timezone(timedelta(hours=8))
ARXIV_API = "http://export.arxiv.org/api/query"

HEADERS = {"User-Agent": "AimFast-Dev/2.0 (+https://aimfast.dev)"}

CATEGORIES = [
    "cs.AI",
    "cs.CL",     # Computation & Language
    "cs.LG",     # Machine Learning
    "cs.SE",     # Software Engineering
    "cs.HC",     # Human-Computer Interaction
]

SEARCH_TERMS = [
    "large language model",
    "AI agent",
    "retrieval augmented generation",
    "LLM evaluation",
    "agent workflow",
    "prompt engineering",
    "AI memory",
    "multi-agent system",
]


def _build_query() -> str:
    """构建搜索查询: 按 AI 类别 + 关键词, 最近 7 天, 按提交日期降序, 最多 50 条。"""
    cat_part = "+OR+".join(f"cat:{c}" for c in CATEGORIES)
    term_part = "+OR+".join(f'all:"{t}"' for t in SEARCH_TERMS)
    query = f"({cat_part})+AND+({term_part})"
    return f"{ARXIV_API}?search_query={query}&sortBy=submittedDate&sortOrder=descending&max_results=50"


def _parse_entry(entry: ET.Element) -> dict | None:
    """将 ArXiv Atom entry 转为标准信号格式。"""
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }

    def _text(tag: str, default: str = "") -> str:
        el = entry.find(f"atom:{tag}", ns)
        return el.text.strip() if el is not None and el.text else default

    def _arx_text(tag: str, default: str = "") -> str:
        el = entry.find(f"arxiv:{tag}", ns)
        return el.text.strip() if el is not None and el.text else default

    title = _text("title")
    if len(title) < 10:
        return None

    arxiv_id = _text("id").split("/abs/")[-1]
    summary = _text("summary", "")[:120]

    # 提取类别
    categories = []
    for cat_el in entry.findall("arxiv:primary_category|atom:category", ns) or entry.findall("category"):
        term = cat_el.get("term", "")
        if term and term not in categories:
            categories.append(term)

    authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)
               if a.find("atom:name", ns) is not None]

    return {
        "id": f"arxiv-{arxiv_id}",
        "title": title.strip(),
        "url": _text("id"),
        "source": "ArXiv",
        "source_key": "arxiv",
        "signal_type": "paper",
        "discussion_count": 0,
        "engagement": {
            "total": 5 + len(authors) * 2,  # 粗略权重: 作者越多 = 越重要
        },
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "raw_created_at": _text("published"),
        "summary": f"[{', '.join(categories[:3])}] {title[:70]} ({', '.join(authors[:3])})",
        "tags": categories,
        "author": authors[0] if authors else "",
    }


def collect(date_str: str | None = None) -> list[dict]:
    """采集 ArXiv 最新 AI 论文, 取 top 40。"""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    url = _build_query()
    print(f"[ArXiv] 查询: {url[:120]}...")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entries = root.findall("atom:entry", ns)

        signals = []
        for entry in entries:
            s = _parse_entry(entry)
            if s:
                signals.append(s)

        signals.sort(key=lambda s: s["engagement"]["total"], reverse=True)
        signals = signals[:40]

        print(f"[ArXiv] 采集 {len(signals)} 条论文信号")
        return signals
    except requests.RequestException as e:
        print(f"[ArXiv] 请求失败: {e}")
        return []
    except ET.ParseError as e:
        print(f"[ArXiv] XML 解析失败: {e}")
        return []


def save_raw(signals: list[dict], date_str: str) -> None:
    """保存到 ./raw/YYYY-MM-DD/arxiv.json"""
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "arxiv",
        "count": len(signals),
        "signals": signals,
    }
    path = dir_path / "arxiv.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ArXiv] → {path}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
