"""
Stack Overflow 信号采集
数据源: Stack Overflow RSS feeds (免费公开, 无需认证)
采集内容: 热门技术标签的最新/热门问题 — 开发者真正在踩坑的信号
"""
import json
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"

TZ_SHANGHAI = timezone(timedelta(hours=8))

HEADERS = {"User-Agent": "AimFast-Dev/2.0 (+https://aimfast.dev)"}

ATOM_NS = "http://www.w3.org/2005/Atom"

# 追踪的技术标签 — 覆盖 AI、Web、Infra、DevTools 热点
TRACKED_TAGS = [
    # AI / LLM
    "langchain", "llama-index", "openai-api", "anthropic", "chromadb",
    "huggingface", "ollama", "large-language-model", "agent",
    "retrieval-augmented-generation", "vector-database",
    # Web / Fullstack
    "next.js", "reactjs", "svelte", "astrojs", "htmx",
    "bun", "prisma", "drizzle", "trpc", "tailwind-css",
    # Backend / API
    "fastapi", "hono", "graphql", "grpc", "websocket",
    # Infra / DevOps
    "docker", "kubernetes", "terraform", "supabase", "planetscale",
    "cloudflare-workers", "vercel", "edge-computing",
    # Languages (trending subsets)
    "rust", "zig", "mojo", "gleam", "typescript",
    # DevTools
    "vite", "turborepo", "biome", "bun.sh", "playwright",
    # Databases
    "duckdb", "sqlite", "clickhouse", "neo4j",
]

# 额外按热度排名取 RSS（不同排序维度）
# Stack Overflow 的 RSS 格式: https://stackoverflow.com/feeds/tag?tagnames={tag}&sort={sort}
RSS_SORTS = ["newest", "featured", "votes"]


def _clean_xml(raw: bytes) -> bytes:
    """移除 XML 中的非法 surrogate 字符。"""
    cleaned = bytearray()
    i = 0
    while i < len(raw):
        if i + 2 < len(raw):
            if raw[i] == 0xED and (raw[i+1] & 0xF0) == 0xA0:
                i += 3
                continue
        cleaned.append(raw[i])
        i += 1
    return bytes(cleaned)


def _fetch_tag_feed(tag: str, sort: str = "newest") -> list[dict]:
    """获取特定标签的 Stack Overflow RSS feed。"""
    url = f"https://stackoverflow.com/feeds/tag?tagnames={tag}&sort={sort}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 404:
            return []
        resp.raise_for_status()

        raw = _clean_xml(resp.content)
        root = ET.fromstring(raw)

        signals = []
        for entry in root.findall(f"{{{ATOM_NS}}}entry"):
            title_el = entry.find(f"{{{ATOM_NS}}}title")
            link_el = entry.find(f"{{{ATOM_NS}}}link")
            author_el = entry.find(f"{{{ATOM_NS}}}author")
            updated_el = entry.find(f"{{{ATOM_NS}}}updated")
            summary_el = entry.find(f"{{{ATOM_NS}}}summary")

            title = title_el.text.strip() if title_el is not None and title_el.text else ""
            link = link_el.get("href", "") if link_el is not None else ""
            author_name = ""
            if author_el is not None:
                name_el = author_el.find(f"{{{ATOM_NS}}}name")
                author_name = name_el.text.strip() if name_el is not None and name_el.text else ""
            updated = updated_el.text.strip() if updated_el is not None and updated_el.text else ""
            # Extract answer count and score from the summary
            summary_text = summary_el.text.strip() if summary_el is not None and summary_el.text else ""

            if not title:
                continue

            # Parse engagement: SO 的 summary 通常包含 "answers" 和 "votes"
            import re
            answer_count = 0
            vote_count = 0
            ans_match = re.search(r'answer[s]?\s*[：:]\s*(\d+)', summary_text, re.IGNORECASE)
            vote_match = re.search(r'(?:score|votes?)[s]?\s*[：:]\s*(\d+)', summary_text, re.IGNORECASE)
            if ans_match:
                answer_count = int(ans_match.group(1))
            if vote_match:
                vote_count = int(vote_match.group(1))

            # 用 title 做更简单的解析
            # Stack Overflow RSS 的 title 通常是 "Question Title" (不带数字)
            # 用 summary 中的数字信息

            post_id = link.split("/")[-2] if link else ""

            signals.append({
                "id": f"so-{post_id}" if post_id else f"so-{hash(title) & 0xFFFFFFFF:08x}",
                "title": title,
                "url": link,
                "source": "Stack Overflow",
                "source_key": "stackoverflow",
                "signal_type": "question",
                "discussion_count": answer_count,
                "engagement": {
                    "answers": answer_count,
                    "votes": vote_count,
                    "total": answer_count * 3 + vote_count + 1,
                },
                "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
                "raw_created_at": updated,
                "summary": f"[SO] {title[:80]}（{answer_count} 回答 / {vote_count} 票）",
                "tags": [tag],
                "author": author_name,
            })

        return signals
    except (requests.RequestException, ET.ParseError) as e:
        print(f"[SO] tag={tag} 请求失败: {e}")
        return []


def collect(date_str: str | None = None) -> list[dict]:
    """采集 Stack Overflow 热门技术标签的问题。"""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    seen: set[str] = set()
    signals: list[dict] = []

    tags_to_fetch = TRACKED_TAGS
    for i, tag in enumerate(tags_to_fetch):
        if i > 0:
            time.sleep(3)  # SO RSS 限速严格 — 需要较长间隔

        # 带重试的请求
        questions = []
        for retry in range(3):
            questions = _fetch_tag_feed(tag, sort="newest")
            if questions:
                break
            if retry < 2:
                print(f"[SO] #{tag} 限速, 等待 {5 * (retry + 1)}s 后重试...")
                time.sleep(5 * (retry + 1))
        count = 0
        for q in questions:
            if q["id"] not in seen:
                seen.add(q["id"])
                signals.append(q)
                count += 1

        if count > 0:
            print(f"[SO] #{tag}: {count} 个问题")

    signals.sort(key=lambda s: s["engagement"]["total"], reverse=True)
    signals = signals[:40]

    print(f"[SO] 总计: {len(signals)} 条信号 (来自 {len(tags_to_fetch)} 个标签)")
    return signals


def save_raw(signals: list[dict], date_str: str) -> None:
    """保存到 ./raw/YYYY-MM-DD/stackoverflow.json"""
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "stackoverflow",
        "count": len(signals),
        "tags_tracked": TRACKED_TAGS,
        "signals": signals,
    }
    path = dir_path / "stackoverflow.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SO] → {path}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
