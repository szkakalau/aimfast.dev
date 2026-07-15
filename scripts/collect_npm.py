"""
npm 信号采集
数据源: npm 官方 API (免费公开, 无需认证) + GitHub npm trending mirror
采集内容: 热门 npm 包 — 下载量增长 + 新包发现
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

# npm 生态中值得关注的趋势关键词 (搜索 API 按 popularity 排序)
TREND_KEYWORDS = [
    "ai agent",
    "llm",
    "mcp",
    "vector database",
    "rag",
    "langchain",
    "webassembly",
    "edge computing",
    "serverless framework",
    "cli tool",
    "developer tool",
    "browser automation",
    "state management",
    "orm",
    "api framework",
]

# 还有一个静态列表 —— 过去 30 天 npm 下载量 top 包，用于发现 "静默增长" 的趋势
# (这些包可能没有上 HN/Reddit，但下载量巨大 → 代表真实的开发者采用)
TRENDING_PACKAGES = [
    "@anthropic/sdk",
    "@modelcontextprotocol/sdk",
    "langchain",
    "llamaindex",
    "chromadb",
    "pinecone",
    "ollama",
    "transformers",
    "vLLM",
    "openai",
    "zod",
    "drizzle-orm",
    "prisma",
    "hono",
    "elysia",
    "bun",
    "bun-type",
    "vitest",
    "biome",
    "oxc",
    "oxlint",
    "rolldown",
    "rslib",
    "rspack",
    "turborepo",
    "nx",
    "effect",
    "zod",
    "arktype",
    "valibot",
    "trigger.dev",
    "inngest",
    "temporal",
    "upstash",
    "resend",
    "novu",
    "payloadcms",
    "directus",
    "pocketbase",
    "n8n",
    "flowise",
    "langflow",
    "copilotkit",
    "Vercel AI SDK",
    "ai",
    "assistant-ui",
    "shadcn-ui",
    "aceternity-ui",
    "magic-ui",
    "motion",
    "gsap",
    "three",
    "react-three-fiber",
    "tldraw",
    "excalidraw",
    "tiptap",
    "plate",
    "lexical",
    "novel",
    "blocknote",
    "liveblocks",
    "yjs",
    "partyKit",
    "replicache",
    "drizzle",
    "better-auth",
    "lucia-auth",
    "clerk",
    "kinde",
    "logto",
    "supertokens",
    "next-auth",
    "authjs",
    "uploadthing",
    "vercel-blob",
    "bun-s3",
    "minio",
    "turso",
    "neon",
    "planetscale",
    "tidb",
    "singlestore",
    "clickhouse",
    "duckdb",
    "sqlite",
    "libsql",
    "electric-sql",
    "convex",
    "instantdb",
    "triplit",
    "tinybase",
    "pglite",
    "op-sqlite",
    "wa-sqlite",
    "absurd-sql",
]


def _fetch_search(keyword: str) -> list[dict]:
    """通过 npm 搜索 API 获取与关键词相关的高人气包。"""
    url = "https://registry.npmjs.org/-/v1/search"
    params = {
        "text": keyword,
        "popularity": "1.0",
        "quality": "0.3",
        "maintenance": "0.3",
        "size": 8,
    }
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("objects", [])
    except requests.RequestException as e:
        print(f"[npm] search '{keyword}' 失败: {e}")
        return []


def _fetch_downloads(package_name: str) -> int | None:
    """获取包过去一周的下载量。"""
    url = f"https://api.npmjs.org/downloads/point/last-week/{package_name}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
        return data.get("downloads", 0)
    except requests.RequestException as e:
        # 静默失败 — 下载量是辅助信号
        return None


def _to_signal(pkg_obj: dict, downloads: int | None = None) -> dict | None:
    """将 npm 包转为标准信号格式。"""
    pkg = pkg_obj.get("package", pkg_obj)
    name = pkg.get("name", "")
    if not name or len(name) < 2:
        return None

    description = pkg.get("description", "")
    version = pkg.get("version", "")
    keywords = pkg.get("keywords", []) or []
    npm_url = pkg.get("links", {}).get("npm", f"https://www.npmjs.com/package/{name}")
    github_url = pkg.get("links", {}).get("repository", "")

    title = name
    if description:
        title = f"{name} — {description[:100]}"

    # 用下载量作为 engagement 信号
    dls = downloads or 0
    engagement_total = min(dls // 100, 200) + len(keywords) * 2 + 1  # normalize to 1-200 range

    return {
        "id": f"npm-{name}",
        "title": title,
        "url": npm_url,
        "source": "npm",
        "source_key": "npm",
        "signal_type": "package",
        "discussion_count": 0,
        "engagement": {
            "downloads_last_week": dls,
            "version": version,
            "total": engagement_total,
        },
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "raw_created_at": "",
        "summary": f"[npm] {name} v{version} — 周下载 {dls:,}" if dls else f"[npm] {name} v{version}",
        "tags": [k for k in keywords if isinstance(k, str)][:5],
        "author": pkg.get("publisher", {}).get("username", "") if pkg.get("publisher") else "",
        "extra": {
            "github_url": github_url,
            "description": description,
        },
    }


def _fetch_and_score_trending() -> list[dict]:
    """批量获取 TRENDING_PACKAGES 的下载量, 找出增长信号。"""
    signals = []
    seen = set()

    for name in TRENDING_PACKAGES:
        dls = _fetch_downloads(name)
        if dls and dls > 1000:  # 至少周下载 1k 才记录
            s = _to_signal({"package": {"name": name, "description": "", "version": "", "keywords": []}}, dls)
            if s and s["id"] not in seen:
                seen.add(s["id"])
                signals.append(s)
        time.sleep(0.15)  # npm API 限速友好

    return signals


def collect(date_str: str | None = None) -> list[dict]:
    """采集 npm 生态信号: 关键词搜索 + 追踪包下载量。"""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    seen: set[str] = set()
    signals: list[dict] = []

    # Phase 1: 关键词搜索 — 发现新包
    for kw in TREND_KEYWORDS:
        results = _fetch_search(kw)
        count = 0
        for obj in results:
            s = _to_signal(obj)
            if s and s["id"] not in seen:
                seen.add(s["id"])
                signals.append(s)
                count += 1
        if count > 0:
            print(f"[npm] search '{kw}': {count} 个包")
        time.sleep(0.3)

    # Phase 2: 追踪包下载量 — 静默增长信号
    print("[npm] 正在查询追踪包下载量...")
    trending = _fetch_and_score_trending()
    for s in trending:
        if s["id"] not in seen:
            seen.add(s["id"])
            signals.append(s)
    print(f"[npm] 追踪包: {len(trending)} 个活跃包 (≥1k 周下载)")

    signals.sort(key=lambda s: s["engagement"]["total"], reverse=True)
    signals = signals[:40]

    print(f"[npm] 总计: {len(signals)} 条信号")
    return signals


def save_raw(signals: list[dict], date_str: str) -> None:
    """保存到 ./raw/YYYY-MM-DD/npm.json"""
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "npm",
        "count": len(signals),
        "signals": signals,
    }
    path = dir_path / "npm.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[npm] → {path}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
