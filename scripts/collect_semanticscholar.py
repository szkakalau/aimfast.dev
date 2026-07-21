"""
Semantic Scholar 学术信号采集 (v1.0)
数据源: Semantic Scholar Academic Graph API (api.semanticscholar.org)
采集内容: AI/CS 领域高引论文 — 学术影响力的真实温度计

价值: 当前 ArXiv 采集器只有论文标题，缺少引用深度。
Semantic Scholar 提供引用次数 + 高影响力引用（influential citations），
能区分"刚发布的新论文"和"已被学术界严肃对待的论文"。

免费额度: 1 req/s 无 API key，100 req/5min 有 key。
对每日管线的 15 个查询来说完全够用。
"""
import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"

TZ_SHANGHAI = timezone(timedelta(hours=8))

S2_API = "https://api.semanticscholar.org/graph/v1/paper/search"
HEADERS = {"User-Agent": "AimFast-Dev/2.3 (+https://aimfast.dev)"}

# ── 查询话题 — AI/CS 前沿方向 ──
SEARCH_TOPICS = [
    # AI 核心
    "AI agent framework",
    "large language model alignment",
    "retrieval augmented generation",
    "multi-agent reinforcement learning",
    # 代码/工具
    "code generation large language model",
    "program synthesis neural",
    "automated machine learning",
    # 基础设施
    "vector database approximate nearest neighbor",
    "edge computing inference optimization",
    "federated learning privacy",
    # 新兴方向
    "AI code review automation",
    "prompt optimization automated",
    "LLM evaluation benchmark",
    "agentic workflow orchestration",
    "small language model efficient inference",
]

# ── 限速配置 ──
DELAY_S = 2.0            # 请求间隔（远低于 1 req/s 限制）
PAPERS_PER_TOPIC = 5     # 每个话题取前 N 篇
MIN_CITATIONS = 5        # 最少引用数（过滤噪声）
MAX_SIGNALS = 40         # 最终输出上限


def _search_papers(query: str, limit: int = PAPERS_PER_TOPIC) -> list[dict]:
    """搜索论文，返回含引用数据的论文列表。"""
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,citationCount,influentialCitationCount,year,venue,publicationDate,externalIds,url,abstract",
    }
    try:
        resp = requests.get(S2_API, headers=HEADERS, params=params, timeout=20)
        if resp.status_code == 429:
            print(f"  [S2] 429 rate limited, 等待 30s...")
            time.sleep(30)
            resp = requests.get(S2_API, headers=HEADERS, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])
    except requests.RequestException as e:
        print(f"  [S2] '{query[:30]}' 请求失败: {e}")
        return []


def _to_signal(paper: dict, topic: str) -> dict | None:
    """将论文转为标准信号格式。"""
    title = paper.get("title", "")
    if len(title) < 10:
        return None

    citations = paper.get("citationCount", 0) or 0
    influential = paper.get("influentialCitationCount", 0) or 0
    year = paper.get("year", 0) or 0
    venue = paper.get("venue", "") or ""
    paper_id = paper.get("paperId", "")
    external_ids = paper.get("externalIds", {}) or {}
    arxiv_id = external_ids.get("ArXiv", "")
    doi = external_ids.get("DOI", "")

    # 论文 URL: 优先 ArXiv, 其次 DOI, 最后 Semantic Scholar
    if arxiv_id:
        url = f"https://arxiv.org/abs/{arxiv_id}"
    elif doi:
        url = f"https://doi.org/{doi}"
    else:
        url = f"https://api.semanticscholar.org/paper/{paper_id}" if paper_id else ""

    # 影响力评分: 引用数 + 高影响力引用加权
    influence_score = min(citations // 10, 60) + min(influential * 3, 40)

    abstract = paper.get("abstract", "") or ""
    summary_text = f"[S2] {title[:120]}"
    if citations > 0:
        summary_text += f" — 被引 {citations} 次"
        if influential > 0:
            summary_text += f"（{influential} 高影响力引用）"
    if venue:
        summary_text += f" | {venue}"

    return {
        "id": f"s2-{paper_id}" if paper_id else f"s2-{abs(hash(title)) % 10_000_000:07d}",
        "title": title,
        "url": url,
        "source": "Semantic Scholar",
        "source_key": "semanticscholar",
        "signal_type": "paper",
        "discussion_count": citations,
        "engagement": {
            "citations": citations,
            "influential_citations": influential,
            "year": year,
            "total": max(1, influence_score),
        },
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "raw_created_at": paper.get("publicationDate", ""),
        "summary": summary_text,
        "tags": ["academic", "paper", topic.replace(" ", "-")[:30]],
        "author": "",
        "extra": {
            "topic": topic,
            "venue": venue,
            "arxiv_id": arxiv_id,
            "abstract": abstract[:300],
        },
    }


def collect(date_str: str | None = None) -> list[dict]:
    """采集 Semantic Scholar 高引论文。

    对 15 个前沿 AI/CS 话题搜索，去重，按引用数降序取 top 40。
    """
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    seen: set[str] = set()
    signals: list[dict] = []

    for i, topic in enumerate(SEARCH_TOPICS):
        if i > 0:
            time.sleep(DELAY_S)

        papers = _search_papers(topic, limit=PAPERS_PER_TOPIC)
        count = 0
        for paper in papers:
            # 过滤低引用噪声
            if (paper.get("citationCount", 0) or 0) < MIN_CITATIONS:
                continue
            s = _to_signal(paper, topic)
            if s and s["id"] not in seen:
                seen.add(s["id"])
                signals.append(s)
                count += 1

        if count > 0:
            top_cite = max((p.get("citationCount", 0) or 0) for p in papers) if papers else 0
            print(f"[S2] '{topic[:40]}': {count} 篇 (最高引用: {top_cite})")

    # 按引用数降序
    signals.sort(key=lambda s: s["engagement"]["citations"], reverse=True)
    signals = signals[:MAX_SIGNALS]

    # 统计
    total_cites = sum(s["engagement"]["citations"] for s in signals)
    total_influential = sum(s["engagement"]["influential_citations"] for s in signals)
    avg_year = sum(s["engagement"]["year"] for s in signals) / max(len(signals), 1)

    print(f"[S2] 总计: {len(signals)} 篇 | 总引用 {total_cites} | 高影响力引用 {total_influential} | 平均年份 {avg_year:.0f}")
    return signals


def save_raw(signals: list[dict], date_str: str) -> None:
    """保存到 ./raw/YYYY-MM-DD/semanticscholar.json"""
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "semanticscholar (Academic Graph API)",
        "topics_searched": len(SEARCH_TOPICS),
        "count": len(signals),
        "signals": signals,
    }
    path = dir_path / "semanticscholar.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[S2] {len(signals)} 条信号 → {path}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
