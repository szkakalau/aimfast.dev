"""
SegmentFault 信号采集 (v1.0)
数据源: SegmentFault Atom RSS (segmentfault.com/feeds/questions)
采集内容: 中文开发者最新技术问答 — 真实需求和痛点的直接信号

SegmentFault 是中文 Stack Overflow，问题内容直接反映开发者当前遇到的真实问题。
相比知乎（全站封锁），SegmentFault 提供标准 Atom RSS，完全免费且无需认证。

价值: 开发者提出的问题 = 市场未被满足的需求。
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

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AimFast-Dev/2.3; +https://aimfast.dev)"}

# ── SegmentFault RSS 端点 ──
SF_QUESTIONS_RSS = "https://segmentfault.com/feeds/questions"
SF_BLOGS_RSS = "https://segmentfault.com/feeds/blogs"

ATOM_NS = "http://www.w3.org/2005/Atom"

# ── 技术关键词 — 用于从问题标题中提取标签 ──
TECH_KEYWORDS_ZH = [
    ("AI", ["ai", "人工智能", "大模型", "llm", "gpt", "claude", "copilot", "agent", "智能体", "机器学习", "深度学习"]),
    ("前端", ["前端", "react", "vue", "next.js", "typescript", "javascript", "css", "组件", "ui", "svelte"]),
    ("后端", ["后端", "go", "rust", "python", "java", "api", "微服务", "数据库", "sql", "redis", "kafka"]),
    ("运维/基础设施", ["k8s", "kubernetes", "docker", "devops", "ci/cd", "云原生", "terraform", "服务器"]),
    ("移动端", ["ios", "android", "flutter", "react native", "小程序", "app"]),
    ("创业/产品", ["创业", "独立开发", "副业", "saas", "变现", "产品", "用户", "增长"]),
    ("工具/效率", ["工具", "效率", "自动化", "vscode", "插件", "脚本", "workflow"]),
    ("安全", ["安全", "漏洞", "加密", "认证", "权限", "ddos"]),
]


def _extract_tags(title: str) -> list[str]:
    """从问题标题中提取中文技术标签。"""
    title_lower = title.lower()
    found = []
    for category, keywords in TECH_KEYWORDS_ZH:
        for kw in keywords:
            if kw in title_lower:
                found.append(category)
                break
    return list(set(found))[:5]


def _parse_atom_entry(entry: ET.Element) -> dict | None:
    """解析 Atom entry 为标准信号格式。"""
    def _text(tag: str) -> str:
        el = entry.find(f"{{{ATOM_NS}}}{tag}")
        return el.text.strip() if el is not None and el.text else ""

    title = _text("title")
    if len(title) < 5:
        return None

    link_el = entry.find(f"{{{ATOM_NS}}}link")
    url = link_el.get("href", "") if link_el is not None else ""

    updated = _text("updated")
    published = _text("published")
    post_id = _text("id").split("/")[-1] if _text("id") else ""

    author_el = entry.find(f"{{{ATOM_NS}}}author")
    author = ""
    if author_el is not None:
        name_el = author_el.find(f"{{{ATOM_NS}}}name")
        author = name_el.text.strip() if name_el is not None and name_el.text else ""

    summary_el = entry.find(f"{{{ATOM_NS}}}summary")
    summary = summary_el.text.strip() if summary_el is not None and summary_el.text else ""
    # 清理 HTML 标签
    clean_summary = re.sub(r"<[^>]+>", "", summary)[:200] if summary else ""

    tags = _extract_tags(title)
    tags.append("segmentfault")

    date_str = published or updated

    return {
        "id": f"sf-{post_id}" if post_id else f"sf-{abs(hash(title)) % 10_000_000:07d}",
        "title": title,
        "url": url,
        "source": "SegmentFault",
        "source_key": "segmentfault",
        "signal_type": "question",
        "discussion_count": 0,
        "engagement": {
            "total": 5 + len(tags) * 2,
        },
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "raw_created_at": date_str,
        "summary": f"[SegmentFault] {title[:120]}" + (f" — {clean_summary[:80]}" if clean_summary else ""),
        "tags": tags[:6],
        "author": author,
        "extra": {
            "summary_text": clean_summary[:200],
        },
    }


def _fetch_feed(url: str) -> list[dict]:
    """获取并解析 Atom RSS feed。"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()

        # 清理 XML 中的非法字符
        raw = resp.content
        cleaned = bytearray()
        i = 0
        while i < len(raw):
            if i + 2 < len(raw):
                if raw[i] == 0xED and (raw[i + 1] & 0xF0) == 0xA0:
                    i += 3
                    continue
            cleaned.append(raw[i])
            i += 1

        root = ET.fromstring(bytes(cleaned))
        entries = root.findall(f"{{{ATOM_NS}}}entry")

        signals = []
        for entry in entries:
            s = _parse_atom_entry(entry)
            if s:
                signals.append(s)
        return signals
    except requests.RequestException as e:
        print(f"  [SF] 请求失败: {e}")
        return []
    except ET.ParseError as e:
        print(f"  [SF] XML 解析失败: {e}")
        return []


def collect(date_str: str | None = None) -> list[dict]:
    """采集 SegmentFault 最新技术问答。

    两个维度：
    1. 最新问题 (questions RSS) — 开发者当前遇到的真实问题
    2. 博客文章 (blogs RSS) — 技术分享和趋势讨论
    """
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    seen: set[str] = set()
    signals: list[dict] = []

    # ── Questions RSS ──
    print("[SF] 获取 SegmentFault 最新问题...")
    questions = _fetch_feed(SF_QUESTIONS_RSS)
    for s in questions:
        if s["id"] not in seen:
            seen.add(s["id"])
            signals.append(s)
    print(f"[SF] 问题: {len(questions)} 条")

    # ── Blogs RSS (可能被限流，非阻塞) ──
    time.sleep(1)
    print("[SF] 获取 SegmentFault 博客...")
    blogs = _fetch_feed(SF_BLOGS_RSS)
    blog_count = 0
    for s in blogs:
        if s["id"] not in seen:
            seen.add(s["id"])
            signals.append(s)
            blog_count += 1
    print(f"[SF] 博客: {blog_count} 条（去重后）")

    # 按发布日期降序
    signals.sort(key=lambda s: s.get("raw_created_at", ""), reverse=True)
    signals = signals[:30]

    # 统计标签分布
    tag_counts: dict[str, int] = {}
    for s in signals:
        for t in s.get("tags", []):
            tag_counts[t] = tag_counts.get(t, 0) + 1

    print(f"[SF] 总计: {len(signals)} 条 | 标签: {', '.join(f'{t}({c})' for t,c in sorted(tag_counts.items(), key=lambda x:x[1], reverse=True)[:6])}")
    return signals


def save_raw(signals: list[dict], date_str: str) -> None:
    """保存到 ./raw/YYYY-MM-DD/segmentfault.json"""
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "segmentfault (Atom RSS: questions + blogs)",
        "count": len(signals),
        "signals": signals,
    }
    path = dir_path / "segmentfault.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SF] {len(signals)} 条信号 → {path}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
