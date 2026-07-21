"""
招聘市场趋势信号采集 (v1.0)
数据源: Hacker News "Who is Hiring" + hiring-related posts (Algolia API)
采集内容: 技术岗位招聘趋势 — 从 HN 招聘帖中提取热门技术栈和薪资信号

价值: HN "Who is Hiring" 是每月一次的技术招聘元数据。
每个帖子包含数千条带有明确技术栈和薪资信息的招聘评论。
这是目前所有竞品（Exploding Topics, Trends.vc, EarlyTerms）都没有系统化使用的信号维度。

方法: 搜索 3 类 HN 帖子 —
  1. "Who is Hiring" — 月度集中招聘帖（最佳信号，含薪资和技术栈）
  2. "Freelancer? Seeking Freelancer?" — 自由职业市场趋势
  3. Ask HN 中的招聘/求职/薪资讨论
"""
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"

TZ_SHANGHAI = timezone(timedelta(hours=8))
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AimFast-Dev/2.3; +https://aimfast.dev)"}

HN_ALGOLIA = "https://hn.algolia.com/api/v1"

# ── 热门技术关键词 — 用于从招聘帖标题中提取信号 ──
TRENDING_TECH = [
    "AI", "LLM", "ML", "Rust", "Go", "TypeScript", "React", "Python",
    "Kubernetes", "Docker", "Terraform", "DevOps", "MLOps", "Data Engineer",
    "Platform Engineer", "Security", "Full Stack", "Backend", "Frontend",
    "iOS", "Android", "Flutter", "Svelte", "Next.js", "Remix",
    "WebAssembly", "WASM", "Edge", "Serverless", "Blockchain", "Web3",
]


def _search_hn(query: str, tags: str = "story", min_points: int = 20, max_hits: int = 20) -> list[dict]:
    """通过 HN Algolia API 搜索帖子。"""
    url = f"{HN_ALGOLIA}/search"
    params = {
        "query": query,
        "tags": tags,
        "numericFilters": f"points>{min_points}",
        "hitsPerPage": max_hits,
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json().get("hits", [])
    except requests.RequestException as e:
        print(f"  [Jobs] HN search '{query[:30]}' 失败: {e}")
        return []


def _search_hn_by_date(query: str, min_points: int = 10, max_hits: int = 15) -> list[dict]:
    """搜索 HN 帖子，按日期降序排列。"""
    url = f"{HN_ALGOLIA}/search_by_date"
    params = {
        "query": query,
        "tags": "story",
        "numericFilters": f"points>{min_points}",
        "hitsPerPage": max_hits,
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json().get("hits", [])
    except requests.RequestException as e:
        print(f"  [Jobs] HN search_by_date '{query[:30]}' 失败: {e}")
        return []


def _extract_tech_keywords(title: str) -> list[str]:
    """从招聘帖标题中提取技术关键词。"""
    found = []
    title_upper = title.upper()
    for tech in TRENDING_TECH:
        if tech.upper() in title_upper:
            found.append(tech)
    return found


def _to_hn_hiring_signal(hit: dict, signal_type: str) -> dict | None:
    """将 HN 招聘相关帖转为标准信号格式。"""
    title = hit.get("title", "")
    if len(title) < 8:
        return None

    points = hit.get("points", 0) or 0
    num_comments = hit.get("num_comments", 0) or 0
    obj_id = hit.get("objectID", "")
    created = hit.get("created_at", "")

    # 提取技术关键词作为标签
    tech_tags = _extract_tech_keywords(title)

    if signal_type == "hiring_thread":
        source_label = "HN Hiring"
        tag_prefix = "hiring"
    elif signal_type == "freelance_thread":
        source_label = "HN Freelance"
        tag_prefix = "freelance"
    else:
        source_label = "HN Job Discussion"
        tag_prefix = "job-discussion"

    return {
        "id": f"hn-jobs-{obj_id}",
        "title": title,
        "url": f"https://news.ycombinator.com/item?id={obj_id}" if obj_id else "",
        "source": source_label,
        "source_key": "job_trends",
        "signal_type": signal_type,
        "discussion_count": num_comments,
        "engagement": {
            "points": points,
            "comments": num_comments,
            "total": points + num_comments * 3,
        },
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "raw_created_at": created,
        "summary": f"[{source_label}] {title} — {points} pts / {num_comments} comments"
                   + (f" | 技术栈: {', '.join(tech_tags[:5])}" if tech_tags else ""),
        "tags": [tag_prefix, "job-market", "hackernews"] + [t.lower() for t in tech_tags[:4]],
        "author": hit.get("author", ""),
        "extra": {
            "tech_keywords": tech_tags,
        },
    }


def _fetch_whos_hiring() -> list[dict]:
    """搜索 HN 'Who is Hiring' 帖 — 最重要的招聘信号。

    每月 1 号左右会有官方自动发的 'Who is Hiring?' 帖，
    通常由 whoishiring 账号发布，包含数千条评论。
    使用 search_by_date 获取最近月份的帖子。"""
    hits = _search_hn_by_date("Who is Hiring", min_points=50, max_hits=10)
    results = []
    for hit in hits:
        title = hit.get("title", "")
        author = hit.get("author", "")
        # 只取 Ask HN "Who is hiring?" 近期的帖子
        if re.search(r"(who is hiring|hiring thread)", title, re.IGNORECASE):
            # 过滤掉非月度主帖（非 Ask HN 的、非 whoishiring 的旧帖）
            if "who is hiring" in title.lower() and author:
                s = _to_hn_hiring_signal(hit, "hiring_thread")
                if s:
                    results.append(s)
    return results[:4]  # 只保留最近的 4 个月


def _fetch_freelance_threads() -> list[dict]:
    """搜索 HN 'Freelancer? Seeking Freelancer?' — 自由职业市场趋势。"""
    hits = _search_hn_by_date("Seeking Freelancer", min_points=30, max_hits=6)
    results = []
    for hit in hits:
        title = hit.get("title", "")
        if re.search(r"(freelancer|seeking freelancer|freelance)", title, re.IGNORECASE):
            s = _to_hn_hiring_signal(hit, "freelance_thread")
            if s:
                results.append(s)
    return results[:4]  # 只保留最近的 4 个月


def _fetch_job_discussions() -> list[dict]:
    """搜索 HN 中关于招聘市场、薪资、RTO 等话题的讨论帖。
    排除 'Who is Hiring' 帖（已在 _fetch_whos_hiring 中处理）。"""
    queries = [
        ("hiring trend OR job market", 15),
        ("salary OR compensation engineer", 15),
        ("remote work OR RTO", 10),
        ("layoff OR hiring freeze", 10),
    ]
    results = []
    for query, min_pts in queries:
        hits = _search_hn_by_date(query, min_points=min_pts, max_hits=5)
        for hit in hits:
            title = hit.get("title", "")
            # 跳过 "Who is Hiring" 帖（已在上面处理）
            if re.search(r"who is hiring", title, re.IGNORECASE):
                continue
            s = _to_hn_hiring_signal(hit, "job_discussion")
            if s:
                results.append(s)
    return results


def collect(date_str: str | None = None) -> list[dict]:
    """采集招聘市场趋势信号。

    三个维度：
    1. HN "Who is Hiring" — 月度招聘主帖（含薪资和技术栈）
    2. HN "Seeking Freelancer" — 自由职业市场趋势
    3. HN 招聘/薪资/RTO 讨论帖 — 市场情绪信号
    """
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    seen: set[str] = set()
    signals: list[dict] = []

    # ── Dimension 1: Who is Hiring ──
    print("[Jobs] 搜索 HN 'Who is Hiring' 帖...")
    hiring = _fetch_whos_hiring()
    for s in hiring:
        if s["id"] not in seen:
            seen.add(s["id"])
            signals.append(s)
            techs = s.get("extra", {}).get("tech_keywords", [])
            print(f"  [Jobs] Hiring: {s['title'][:60]} — {s['engagement']['points']} pts / {s['engagement']['comments']} comments"
                  + (f" | {', '.join(techs[:4])}" if techs else ""))

    # ── Dimension 2: Freelance ──
    print("[Jobs] 搜索 HN 'Seeking Freelancer' 帖...")
    freelance = _fetch_freelance_threads()
    for s in freelance:
        if s["id"] not in seen:
            seen.add(s["id"])
            signals.append(s)
            print(f"  [Jobs] Freelance: {s['title'][:60]} — {s['engagement']['points']} pts")

    # ── Dimension 3: Job Market Discussions ──
    print("[Jobs] 搜索 HN 招聘/薪资讨论帖...")
    discussions = _fetch_job_discussions()
    for s in discussions:
        if s["id"] not in seen:
            seen.add(s["id"])
            signals.append(s)
            print(f"  [Jobs] Discussion: {s['title'][:60]} — {s['engagement']['points']} pts")

    # ── 汇总统计 ──
    hiring_count = sum(1 for s in signals if s["signal_type"] == "hiring_thread")
    freelance_count = sum(1 for s in signals if s["signal_type"] == "freelance_thread")
    discussion_count = sum(1 for s in signals if s["signal_type"] == "job_discussion")

    # 按 engagement 降序
    signals.sort(key=lambda s: s["engagement"]["total"], reverse=True)
    signals = signals[:25]

    print(f"[Jobs] 总计: {len(signals)} 条 ({hiring_count} hiring + {freelance_count} freelance + {discussion_count} discussion)")
    return signals


def save_raw(signals: list[dict], date_str: str) -> None:
    """保存到 ./raw/YYYY-MM-DD/job_trends.json"""
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "job_trends (HN Algolia API — Who is Hiring + Freelance + Job Discussions)",
        "method": "HN Algolia search across 3 query dimensions",
        "count": len(signals),
        "signals": signals,
    }
    path = dir_path / "job_trends.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[Jobs] {len(signals)} 条信号 → {path}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
