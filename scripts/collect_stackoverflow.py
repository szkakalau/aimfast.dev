"""
Stack Overflow 信号采集 (v2.0)
数据源: Stack Exchange API v2.3 (免费配额 300 req/day，带 key 10,000)
采集内容: 热门技术标签的最新活跃问题 — 开发者真正在踩坑的信号

v2.0 变更: 从 RSS feed 迁移到 Stack Exchange API。
  RSS 端点 (feeds/tag) 自 2026-08 起对非浏览器 UA 返回 403。
  Stack Exchange API 是官方支持的 JSON API，含速率控制和配额管理。
"""
import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"

TZ_SHANGHAI = timezone(timedelta(hours=8))

HEADERS = {"User-Agent": "AimFast-Dev/2.0 (+https://aimfast.dev)"}

SE_API = "https://api.stackexchange.com/2.3"

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


def _fetch_tag_questions(tag: str, pagesize: int = 10) -> list[dict]:
    """通过 Stack Exchange API 获取单个标签的最新活跃问题。

    Stack Exchange API 的 tagged 参数限制：OR 查询超过 3 个标签时
    后端会超时返回空结果。因此逐标签请求是最可靠的方式。

    使用 /questions 端点，按 activity 降序排列。
    文档: https://api.stackexchange.com/docs/questions
    """
    url = (
        f"{SE_API}/questions"
        f"?order=desc"
        f"&sort=activity"
        f"&tagged={tag}"
        f"&site=stackoverflow"
        f"&pagesize={pagesize}"
    )

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        print(f"[SO-API] tag={tag} 请求失败: {e}")
        return []
    except ValueError:
        print(f"[SO-API] tag={tag} 返回非 JSON")
        return []

    # 速率控制: Stack Exchange API 在需要限速时返回 backoff 字段（秒）
    backoff = data.get("backoff", 0)
    if backoff:
        print(f"[SO-API] 限速 backoff={backoff}s，等待中...")
        time.sleep(backoff + 1)

    return data.get("items", [])


def _item_to_signal(item: dict) -> dict | None:
    """将 Stack Exchange API question item 转为标准信号格式。"""
    question_id = item.get("question_id")
    title = item.get("title", "")
    link = item.get("link", "")
    tags = item.get("tags", [])
    owner = item.get("owner", {}) or {}
    score = item.get("score", 0)
    answer_count = item.get("answer_count", 0)
    view_count = item.get("view_count", 0)
    creation_date = item.get("creation_date", 0)
    body = item.get("body", "")[:300] if item.get("body") else ""

    if not title:
        return None

    # 将 Unix timestamp 转为 ISO
    created_at = ""
    if creation_date:
        created_at = datetime.fromtimestamp(creation_date, tz=TZ_SHANGHAI).isoformat()

    author = owner.get("display_name", "")

    return {
        "id": f"so-{question_id}",
        "title": title,
        "url": link,
        "source": "Stack Overflow",
        "source_key": "stackoverflow",
        "signal_type": "question",
        "discussion_count": answer_count,
        "engagement": {
            "answers": answer_count,
            "votes": score,
            "views": view_count,
            "total": answer_count * 3 + max(score, 0) + min(view_count // 100, 10),
        },
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "raw_created_at": created_at,
        "summary": f"[SO] {title[:80]}（{answer_count} 回答 / {score} 票）",
        "tags": tags[:8],
        "author": author,
        "extra": {
            "score": score,
            "view_count": view_count,
            "question_id": question_id,
            "body_preview": body,
        },
    }


def collect(date_str: str | None = None) -> list[dict]:
    """采集 Stack Overflow 热门技术标签的问题。

    Stack Exchange API 逐标签请求（10 条/标签），按 engagement 排序取 Top 40。
    46 标签 × 1 请求 = 46 req，远低于 300/天免费配额。
    """
    date_str = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    seen: set[str] = set()
    signals: list[dict] = []

    total_tags = len(TRACKED_TAGS)
    for i, tag in enumerate(TRACKED_TAGS):
        items = _fetch_tag_questions(tag, pagesize=10)

        count = 0
        for item in items:
            s = _item_to_signal(item)
            if s and s["id"] not in seen:
                seen.add(s["id"])
                signals.append(s)
                count += 1

        if count > 0:
            print(f"[SO] #{tag}: {count} 个问题")
        else:
            print(f"[SO] #{tag}: 0 个问题")

        # 标签间短暂等待，避免触发 backoff
        if i < total_tags - 1:
            time.sleep(0.3)

    # 按互动量排序，取 Top 40
    signals.sort(key=lambda s: s["engagement"]["total"], reverse=True)
    signals = signals[:40]

    print(f"[SO] 总计: {len(signals)} 条信号 (来自 {total_tags} 个标签)")
    return signals


def save_raw(signals: list[dict], date_str: str) -> None:
    """保存到 ./raw/YYYY-MM-DD/stackoverflow.json"""
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "stackoverflow",
        "api": "Stack Exchange API v2.3",
        "count": len(signals),
        "tags_tracked": TRACKED_TAGS,
        "signals": signals,
    }
    path = dir_path / "stackoverflow.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SO] {len(signals)} 条信号 → {path}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
