"""
GitHub Trending 信号采集 (v2.0 — 深度分析增强)
数据源: GitHub Search API + REST API
采集内容: 热门 repo + star 增长 + issue/PR 活跃度 + 话题趋势

v2.0 新增:
  1. Issue/PR Velocity — 前 15 个热门 repo 的 issue/open/pr 活跃度
  2. Topic-Based Discovery — 按技术话题发现新兴项目
  3. Star Growth Tracking — 对比前一天数据计算日增长
"""
import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"

TZ_SHANGHAI = timezone(timedelta(hours=8))
GITHUB_API = "https://api.github.com"
HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "AimFast-Dev/2.0",
}

# ── 技术话题发现 — 按生态关键词搜索新兴项目 ──
DISCOVERY_TOPICS = [
    "ai-agent",
    "mcp-server",
    "llm-tool",
    "browser-automation",
    "local-first",
    "edge-ai",
    "vector-database",
    "agent-framework",
]


def _search_repos(query: str, per_page: int = 30) -> list[dict]:
    """调用 GitHub Search API。"""
    url = f"{GITHUB_API}/search/repositories"
    params = {"q": query, "sort": "stars", "order": "desc", "per_page": per_page}
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json().get("items", [])
    except requests.RequestException as e:
        print(f"[GitHub] API 请求失败: {e}")
        return []


def _repo_age_days(repo: dict) -> int | None:
    """计算仓库年龄（天）。"""
    created = repo.get("created_at", "")
    if not created:
        return None
    try:
        created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return (now - created_dt).days
    except (ValueError, TypeError):
        return None


def _is_spam(repo: dict) -> bool:
    """过滤明显的 spam 仓库。"""
    name = repo.get("full_name", "")
    desc = repo.get("description") or ""
    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)

    # forks 远超 stars → 可能是 fork 农场
    if forks > stars * 3 and stars < 50:
        return True
    # 无描述 + 低 star → 可能是模板/spam
    if not desc and stars < 30:
        return True
    # 名称可疑模式
    suspicious_patterns = [
        "-Latest-", "stake-", "trading-bot", "airdrop", "claim-",
        "crypto-", "token-", "nft-", "free-", "hack-",
    ]
    for p in suspicious_patterns:
        if p.lower() in name.lower():
            return True
    return False


def _is_stale(repo: dict) -> bool:
    """
    过滤过老的仓库（超过 2 年 + 非异常增长）。
    真正的 trending 应该是新兴项目，不是 freeCodeCamp 这种老牌项目。
    """
    age = _repo_age_days(repo)
    if age is None:
        return False  # 无法判断时保留

    stars = repo.get("stargazers_count", 0)
    # 老仓库但近期有爆发性增长 → 保留（例如某老项目突然翻红）
    # 用星速判断: stars/day > 50 说明有关注度异常
    star_velocity = stars / max(age, 1)
    if age > 730 and star_velocity < 50:
        return True
    return False


def _to_signal(repo: dict, query_label: str) -> dict:
    """将 GitHub repo 转为标准信号格式。"""
    full_name = repo.get("full_name", "")
    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)
    watchers = repo.get("watchers_count", 0)
    age = _repo_age_days(repo) or 0
    velocity = stars / max(age, 1)

    return {
        "id": f"github-{repo.get('id', '')}",
        "title": full_name,
        "url": repo.get("html_url", ""),
        "source": "GitHub Trending",
        "source_key": "github",
        "signal_type": "repo",
        "discussion_count": forks + watchers,
        "engagement": {
            "stars": stars,
            "forks": forks,
            "watchers": watchers,
            "star_velocity": round(velocity, 1),
            "repo_age_days": age,
            "total": stars * 2 + forks + int(velocity * 50),
        },
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "raw_created_at": repo.get("created_at", ""),
        "raw_updated_at": repo.get("updated_at", ""),
        "summary": f"{full_name}：{repo.get('description', '') or '(无描述)'}（{stars} star / {forks} fork / {age}天）",
        "tags": [repo.get("language", ""), query_label],
        "author": repo.get("owner", {}).get("login", ""),
        "language": repo.get("language", ""),
        "topics": repo.get("topics", []),
    }


def _search_topic(topic: str, per_page: int = 15) -> list[dict]:
    """按技术话题搜索仓库 — 发现新兴生态中的项目。"""
    url = f"{GITHUB_API}/search/repositories"
    params = {
        "q": f"topic:{topic}",
        "sort": "updated",
        "order": "desc",
        "per_page": per_page,
    }
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json().get("items", [])
    except requests.RequestException as e:
        print(f"[GitHub] topic '{topic}' 查询失败: {e}")
        return []


def _enrich_with_activity(signals: list[dict], top_n: int = 15) -> None:
    """为前 top_n 个 repo 查询 issue/PR 活跃度数据。
    使用 GitHub Search API 批量查询，避免 per-repo API 调用。"""
    for idx, s in enumerate(signals[:top_n]):
        full_name = s.get("title", "")
        if not full_name or "/" not in full_name:
            continue

        # 查询 open issues 数量（排除 PR）
        try:
            url = f"{GITHUB_API}/search/issues"
            params = {
                "q": f"repo:{full_name} is:issue is:open",
                "per_page": 1,
            }
            resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
            resp.raise_for_status()
            open_issues = resp.json().get("total_count", 0)
            time.sleep(0.3)  # GitHub API 限速友好
        except requests.RequestException:
            open_issues = 0

        # 查询 open PRs 数量
        try:
            params["q"] = f"repo:{full_name} is:pr is:open"
            resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
            resp.raise_for_status()
            open_prs = resp.json().get("total_count", 0)
            time.sleep(0.3)
        except requests.RequestException:
            open_prs = 0

        # 更新 signal 的 engagement
        stars = s["engagement"].get("stars", 0)
        s["engagement"]["open_issues"] = open_issues
        s["engagement"]["open_prs"] = open_prs
        # 活跃度分数: issue/PR 多且 star 在增长 = 健康项目
        activity_score = min(open_issues // 5, 30) + min(open_prs * 2, 20)
        s["engagement"]["activity_score"] = activity_score
        # 更新 total engagement
        s["engagement"]["total"] = s["engagement"]["total"] + activity_score

        # 更新 summary 加入活跃度信息
        s["summary"] = f"{full_name}：{s.get('summary', '').split('（')[0] if '（' in s.get('summary', '') else s.get('summary', '')}（{stars}★ / {open_issues} issues / {open_prs} PRs）"


def _load_previous_stars() -> dict[str, int]:
    """加载前一天的 GitHub 数据以获得 star 增长对比。"""
    yesterday = (datetime.now(TZ_SHANGHAI) - timedelta(days=1)).strftime("%Y-%m-%d")
    prev_path = RAW_DIR / yesterday / "github.json"
    if not prev_path.exists():
        # 尝试前天（跨周末）
        two_days = (datetime.now(TZ_SHANGHAI) - timedelta(days=2)).strftime("%Y-%m-%d")
        prev_path = RAW_DIR / two_days / "github.json"
        if not prev_path.exists():
            return {}

    try:
        prev_data = json.loads(prev_path.read_text(encoding="utf-8"))
        prev_signals = prev_data.get("signals", [])
        return {
            s["title"]: s.get("engagement", {}).get("stars", 0)
            for s in prev_signals
            if s.get("title")
        }
    except (json.JSONDecodeError, OSError):
        return {}


def _add_growth_delta(signals: list[dict], prev_stars: dict[str, int]) -> None:
    """对比前一天 star 数，添加每日增长量。"""
    for s in signals:
        full_name = s.get("title", "")
        prev = prev_stars.get(full_name, 0)
        current = s["engagement"].get("stars", 0)
        if prev > 0 and current > prev:
            delta = current - prev
            s["engagement"]["star_growth_24h"] = delta
            # 在 summary 末尾追加增长信息
            s["summary"] = s.get("summary", "") + f" ↑+{delta}★/24h"


def collect(date_str: str | None = None) -> list[dict]:
    """
    采集 GitHub 热门仓库（v2.0 — 5 维深度分析）。

    五个维度：
    1. 近 7 天创建的高 star 仓库 → "rising stars"
    2. 近 30 天创建的中等 star 仓库 → "fresh projects"
    3. 近 3 天有推送 + 1 年内创建 + stars > 100 → "actively maintained"
    4. 按技术话题发现的仓库 → "topic: {topic}" (v2.0 新增)
    5. Issue/PR 活跃度 + Star 日增长量 (v2.0 新增)
    """
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    today = datetime.now(TZ_SHANGHAI)
    seen: set[str] = set()
    signals: list[dict] = []

    # Query 1: 近 7 天创建，stars > 10 的仓库（真正的 "rising stars"）
    seven_days_ago = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    q1 = f"created:>={seven_days_ago} stars:>10"
    repos1 = _search_repos(q1, per_page=40)
    for r in repos1:
        if not _is_spam(r):
            signal = _to_signal(r, "rising")
            if signal["id"] not in seen:
                seen.add(signal["id"])
                signals.append(signal)
    print(f"[GitHub] rising: {len([s for s in signals if 'rising' in s.get('tags', [])])} 条有效")

    # Query 2: 近 30 天创建，stars > 30（新兴活跃项目）
    thirty_days_ago = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    q2 = f"created:>={thirty_days_ago} stars:>30"
    repos2 = _search_repos(q2, per_page=40)
    fresh_count = 0
    for r in repos2:
        if not _is_spam(r):
            signal = _to_signal(r, "fresh")
            if signal["id"] not in seen:
                seen.add(signal["id"])
                signals.append(signal)
                fresh_count += 1
    print(f"[GitHub] fresh: {fresh_count} 条有效（去重后）")

    # Query 3: 近 3 天有推送 + stars > 100 + 1 年内创建（活跃 + 新兴）
    three_days_ago = (today - timedelta(days=3)).strftime("%Y-%m-%d")
    one_year_ago = (today - timedelta(days=365)).strftime("%Y-%m-%d")
    q3 = f"pushed:>={three_days_ago} created:>={one_year_ago} stars:>100"
    repos3 = _search_repos(q3, per_page=30)
    active_count = 0
    for r in repos3:
        if not _is_spam(r) and not _is_stale(r):
            signal = _to_signal(r, "active")
            if signal["id"] not in seen:
                seen.add(signal["id"])
                signals.append(signal)
                active_count += 1
    print(f"[GitHub] active: {active_count} 条有效（去重后）")

    # Query 4 (v2.0 新增): 按技术话题发现 — 发现新兴生态中的项目
    topic_count = 0
    for topic in DISCOVERY_TOPICS:
        repos_topic = _search_topic(topic, per_page=12)
        for r in repos_topic:
            if not _is_spam(r):
                signal = _to_signal(r, f"topic:{topic}")
                if signal["id"] not in seen:
                    seen.add(signal["id"])
                    signals.append(signal)
                    topic_count += 1
    print(f"[GitHub] topic-discovery: {topic_count} 条有效（来自 {len(DISCOVERY_TOPICS)} 个话题）")

    # 按 star 降序
    signals.sort(key=lambda s: s["engagement"]["stars"], reverse=True)
    signals = signals[:50]  # v2.0: 40 → 50（增加话题发现维度）

    # v2.0 新增: Issue/PR 活跃度
    print("[GitHub] 查询 repo 活跃度 (issues/PRs)...")
    _enrich_with_activity(signals, top_n=15)

    # v2.0 新增: Star 日增长对比
    prev_stars = _load_previous_stars()
    if prev_stars:
        _add_growth_delta(signals, prev_stars)
        growth_count = sum(1 for s in signals if s["engagement"].get("star_growth_24h", 0) > 0)
        print(f"[GitHub] 增长追踪: {growth_count} 个 repo 有 24h star 增长数据")

    print(f"[GitHub] 总计: {len(signals)} 条 (rising+fresh+active+topic)")
    return signals


def save_raw(signals: list[dict], date_str: str) -> None:
    """保存原始采集数据到 ./raw/YYYY-MM-DD/github.json"""
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "github",
        "count": len(signals),
        "signals": signals,
    }
    path = dir_path / "github.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[GitHub] {len(signals)} 条信号 → {path}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
