"""
GitHub Releases 信号采集器
数据源: GitHub Releases API（配置驱动的仓库列表）
采集内容: 关键项目的 release notes — 版本更新、breaking changes、新功能
"""
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"
CONFIG_PATH = ROOT / "config.json"

TZ_SHANGHAI = timezone(timedelta(hours=8))
GITHUB_API = "https://api.github.com"
HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "AimFast-Dev/2.3",
}

_REPO_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$")


def _is_valid_repo(repo: str) -> bool:
    """验证仓库名格式: owner/repo。拒绝路径遍历和特殊字符。"""
    return bool(_REPO_PATTERN.match(repo))


def _load_repos() -> list[str]:
    """从 config.json 读取目标仓库列表，不可用时回退到共享默认值。只返回格式有效的仓库名。"""
    repos = []
    try:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        repos = cfg.get("github_release_repos", [])
    except (json.JSONDecodeError, OSError):
        pass
    if not repos:
        try:
            from scripts.defaults import DEFAULT_GITHUB_RELEASE_REPOS
            repos = DEFAULT_GITHUB_RELEASE_REPOS
        except ImportError:
            pass
    return [r for r in repos if _is_valid_repo(r)]


def _to_signal(release: dict, repo: str, repo_info: dict | None) -> dict | None:
    """将 GitHub release 转为标准信号。"""
    tag = release.get("tag_name", "")
    name = release.get("name") or tag
    body = release.get("body") or ""
    url = release.get("html_url", "")

    if not name:
        return None

    # 摘要：取 release body 前 200 字符
    summary = body[:200].replace("\n", " ").strip()

    published_at = release.get("published_at") or release.get("created_at", "")
    stars = (repo_info or {}).get("stargazers_count", 0) if repo_info else 0

    # 判断是否是 breaking/pre-release
    prerelease = release.get("prerelease", False)
    is_breaking = any(kw in (name + body).lower() for kw in
                      ["breaking", "deprecated", "removed", "major"])

    tags = ["github-release", "release"]
    if prerelease:
        tags.append("prerelease")
    if is_breaking:
        tags.append("breaking-change")

    signal_id = f"ghr-{abs(hash(url or f'{repo}@{tag}')) % 10_000_000:07d}"

    return {
        "id": signal_id,
        "title": f"[{repo}] {name[:180]}",
        "url": url,
        "source": "GitHub Releases",
        "source_key": "github-releases",
        "signal_type": "release",
        "discussion_count": 0,
        "engagement": {
            "stars": stars,
            "prerelease": prerelease,
            "is_breaking": is_breaking,
            "total": stars + (20 if is_breaking else 0),
        },
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "raw_created_at": published_at,
        "summary": f"{repo} {tag}: {summary[:180]}",
        "tags": tags[:6],
        "author": repo.split("/")[0] if "/" in repo else "",
        "repo": repo,
        "tag_name": tag,
    }


def _fetch_releases(repo: str, per_page: int = 5) -> tuple[list[dict], dict | None]:
    """获取仓库的 releases 和 repo info。"""
    releases: list[dict] = []
    repo_info: dict | None = None

    # 获取 repo info (stars)
    try:
        resp = requests.get(f"{GITHUB_API}/repos/{repo}", headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            repo_info = resp.json()
    except requests.RequestException:
        pass

    # 获取 releases
    try:
        resp = requests.get(
            f"{GITHUB_API}/repos/{repo}/releases",
            headers=HEADERS,
            params={"per_page": per_page},
            timeout=15,
        )
        resp.raise_for_status()
        releases = resp.json()
    except requests.RequestException as e:
        print(f"  [GHR] {repo}: 请求失败: {e}")

    return releases, repo_info


def _days_ago(iso_str: str) -> int | None:
    """推算距今多少天。"""
    if not iso_str:
        return None
    try:
        pub_dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return (now - pub_dt).days
    except (ValueError, TypeError):
        return None


def collect(date_str: str | None = None) -> list[dict]:
    """采集所有配置仓库的近期 releases，去重取 top 40。"""
    repos = _load_repos()
    seen_urls: set[str] = set()
    signals: list[dict] = []

    for repo in repos:
        releases, repo_info = _fetch_releases(repo)
        count = 0
        for rel in releases:
            pub_at = rel.get("published_at") or rel.get("created_at", "")
            age = _days_ago(pub_at)
            if age is not None and age > 3:
                continue  # 超过 3 天的忽略

            sig = _to_signal(rel, repo, repo_info)
            if sig is None:
                continue
            url = sig["url"]
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)
            signals.append(sig)
            count += 1
        print(f"[GHR] {repo}: {count} releases (近 3 天)")
        if len(signals) >= 40:
            break

    # 按 breaking change 和 star 数排序
    signals.sort(
        key=lambda s: (s["engagement"].get("is_breaking", False),
                        s["engagement"].get("stars", 0)),
        reverse=True,
    )
    signals = signals[:40]

    print(f"[GHR] 总计: {len(signals)} 条（去重后）")
    return signals


def save_raw(signals: list[dict], date_str: str) -> None:
    """保存到 ./raw/YYYY-MM-DD/github_releases.json"""
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "github-releases",
        "count": len(signals),
        "signals": signals,
    }
    path = dir_path / "github_releases.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[GHR] {len(signals)} 条信号 → {path}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
