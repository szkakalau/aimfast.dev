"""
PyPI 信号采集
数据源: PyPI RSS feeds (免费公开, 无需认证) + 热门项目库
采集内容: Python 生态新包发布 + 热门包下载趋势
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

# PyPI RSS: 最新包更新
PYPI_RSS_URLS = [
    "https://pypi.org/rss/packages.xml",           # 最新包
    "https://pypi.org/rss/updates.xml",             # 包更新
]

# 值得追踪的 Python AI/工具库 — 获取下载量作为增长信号
TRENDING_PYPI_PACKAGES = [
    # AI / LLM
    "langchain", "llama-index", "chromadb", "ollama", "openai",
    "anthropic", "transformers", "datasets", "accelerate", "peft",
    "trl", "vllm", "sglang", "mlc-llm", "mistral", "guidance",
    "dspy", "instructor", "outlines", "lm-format-enforcer",
    # Agent / MCP
    "mcp", "fastmcp", "langgraph", "autogen", "crewai",
    "agno", "pydantic-ai", "smolagents",
    # Data / DB
    "duckdb", "lancedb", "qdrant-client", "weaviate-client",
    "pgvector", "sqlalchemy", "prisma", "tortoise-orm",
    # Web / API
    "fastapi", "litestar", "blacksheep", "flask", "django",
    "strawberry-graphql", "ariadne", "starlite",
    # Tools
    "typer", "rich", "textual", "pydantic", "pydantic-settings",
    "ruff", "mypy", "pre-commit", "coverage",
    "pytest", "nox", "tox", "hatch", "poetry", "uv",
    "mkdocs", "sphinx", "jupyter", "marimo",
    "modal", "bentoml", "ray", "prefect", "dagster",
]


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


def _fetch_rss(url: str) -> list[dict]:
    """解析 PyPI RSS feed 为信号。"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()

        raw = _clean_xml(resp.content)
        root = ET.fromstring(raw)

        signals = []
        for item in root.findall(".//item"):
            title_el = item.find("title")
            link_el = item.find("link")
            desc_el = item.find("description")
            pubdate_el = item.find("pubDate")

            title = title_el.text.strip() if title_el is not None and title_el.text else ""
            link = link_el.text.strip() if link_el is not None and link_el.text else ""
            desc = desc_el.text.strip() if desc_el is not None and desc_el.text else ""

            if not title or len(title) < 3:
                continue

            pkg_name = title.split()[0] if title else title  # e.g. "langchain 0.3.0"
            pub_date = pubdate_el.text.strip() if pubdate_el is not None and pubdate_el.text else ""

            signals.append({
                "id": f"pypi-{pkg_name.replace('.', '-')}",
                "title": title,
                "url": link,
                "source": "PyPI",
                "source_key": "pypi",
                "signal_type": "package_release",
                "discussion_count": 0,
                "engagement": {
                    "description": desc[:200],
                    "total": 5,  # base signal strength
                },
                "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
                "raw_created_at": pub_date,
                "summary": f"[PyPI] {title[:80]}",
                "tags": [],
                "author": "",
            })

        return signals
    except (requests.RequestException, ET.ParseError) as e:
        print(f"[PyPI] RSS 获取失败 ({url}): {e}")
        return []


def _fetch_package_info(package_name: str) -> dict | None:
    """通过 PyPI JSON API 获取包的元数据。"""
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


def _to_signal_from_info(pkg_name: str, info: dict) -> dict | None:
    """将 PyPI JSON API 数据转为标准信号格式。"""
    pkg_info = info.get("info", {})
    name = pkg_info.get("name", pkg_name)
    summary = pkg_info.get("summary", "")
    version = pkg_info.get("version", "")
    home_page = pkg_info.get("home_page", "")
    package_url = pkg_info.get("package_url", f"https://pypi.org/project/{name}/")
    keywords = pkg_info.get("keywords", "") or ""
    author = pkg_info.get("author", "")

    title = name
    if summary:
        title = f"{name} — {summary[:100]}"

    keyword_list = [k.strip() for k in keywords.split(",") if k.strip()][:5]

    # 用 version 数量作为活跃度代理信号
    releases = info.get("releases", {})
    release_count = len(releases) if releases else 1

    engagement_total = min(release_count * 3 + len(keyword_list) * 2, 200) + 1

    return {
        "id": f"pypi-{name.replace('.', '-')}",
        "title": title,
        "url": package_url or home_page or f"https://pypi.org/project/{name}/",
        "source": "PyPI",
        "source_key": "pypi",
        "signal_type": "package",
        "discussion_count": 0,
        "engagement": {
            "version": version,
            "release_count": release_count,
            "total": engagement_total,
        },
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "raw_created_at": "",
        "summary": f"[PyPI] {name} v{version} — {summary[:60]}" if summary else f"[PyPI] {name} v{version}",
        "tags": keyword_list,
        "author": author,
        "extra": {
            "home_page": home_page,
            "summary": summary,
        },
    }


def collect(date_str: str | None = None) -> list[dict]:
    """采集 PyPI 生态信号: RSS 新包 + 追踪包活跃度。"""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    seen: set[str] = set()
    signals: list[dict] = []

    # Phase 1: RSS feeds — 最新发布/更新
    for url in PYPI_RSS_URLS:
        rss_signals = _fetch_rss(url)
        for s in rss_signals:
            if s["id"] not in seen:
                seen.add(s["id"])
                signals.append(s)
        print(f"[PyPI] RSS ({url.split('/')[-1]}): {len(rss_signals)} 条")

    # Phase 2: 追踪包活跃度检查
    print(f"[PyPI] 正在检查 {len(TRENDING_PYPI_PACKAGES)} 个追踪包...")
    count = 0
    for pkg_name in TRENDING_PYPI_PACKAGES:
        info = _fetch_package_info(pkg_name)
        if info:
            s = _to_signal_from_info(pkg_name, info)
            if s and s["id"] not in seen:
                seen.add(s["id"])
                signals.append(s)
                count += 1
        time.sleep(0.2)  # PyPI API 限速友好

    print(f"[PyPI] 追踪包: {count} 个活跃包")

    signals.sort(key=lambda s: s["engagement"]["total"], reverse=True)
    signals = signals[:40]

    print(f"[PyPI] 总计: {len(signals)} 条信号")
    return signals


def save_raw(signals: list[dict], date_str: str) -> None:
    """保存到 ./raw/YYYY-MM-DD/pypi.json"""
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "pypi",
        "count": len(signals),
        "signals": signals,
    }
    path = dir_path / "pypi.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[PyPI] → {path}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
