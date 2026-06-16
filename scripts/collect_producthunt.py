"""
Product Hunt 信号采集
数据源: Product Hunt API v2 (GraphQL, 开发者 Token)
采集内容: 当日热门新品 + 投票数 + 评论数
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"
CONFIG_PATH = ROOT / "config.json"

TZ_SHANGHAI = timezone(timedelta(hours=8))
PH_API = "https://api.producthunt.com/v2/api/graphql"
PH_TOKEN_URL = "https://api.producthunt.com/v2/oauth/token"


def _get_ph_credentials() -> tuple[str, str]:
    """从 config.json 读取 PH API 凭证。"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    keys = cfg.get("api_keys", {}).get("producthunt", {})
    return keys.get("client_id", ""), keys.get("client_secret", "")

# 缓存 token (运行时)
_token_cache: dict = {}


def _get_access_token() -> str | None:
    """通过 client_credentials OAuth 获取 access token。"""
    expires = _token_cache.get("expires_at", 0)
    if isinstance(expires, (int, float)) and expires > datetime.now().timestamp():
        return _token_cache.get("token")

    cid, csecret = _get_ph_credentials()
    if not cid:
        print("[PH] config.json 中未配置 api_keys.producthunt")
        return None

    try:
        resp = requests.post(
            PH_TOKEN_URL,
            json={
                "client_id": cid,
                "client_secret": csecret,
                "grant_type": "client_credentials",
            },
            headers={"User-Agent": "AimFast-Dev/2.0"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        token = data.get("access_token")
        expires_in = data.get("expires_in", 7200)
        _token_cache["token"] = token
        _token_cache["expires_at"] = datetime.now().timestamp() + expires_in - 60  # 提前 1 分钟刷新
        print(f"[PH] OAuth token 获取成功 (有效期 {expires_in}s)")
        return token
    except requests.RequestException as e:
        print(f"[PH] OAuth token 获取失败: {e}")
        return None

# GraphQL: 获取今日热门帖子 (带投票和评论数)
QUERY = """
query($postedAfter: DateTime!, $first: Int!) {
  posts(postedAfter: $postedAfter, first: $first, order: VOTES) {
    edges {
      node {
        id
        name
        tagline
        description
        url
        votesCount
        commentsCount
        website
        topics { edges { node { name } } }
        user { name username }
        createdAt
      }
    }
  }
}
"""


def collect(date_str: str | None = None) -> list[dict]:
    """采集 Product Hunt 今日热门产品 (最多 40 条)。"""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    # PH 按太平洋时间发布 — 取最近 2 天确保覆盖
    two_days_ago = (datetime.now(TZ_SHANGHAI) - timedelta(days=2)).strftime("%Y-%m-%d")
    posted_after = f"{two_days_ago}T00:00:00Z"

    token = _get_access_token()
    if not token:
        return []

    try:
        resp = requests.post(
            PH_API,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": "AimFast-Dev/2.0",
            },
            json={"query": QUERY, "variables": {"postedAfter": posted_after, "first": 40}},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        print(f"[PH] API 请求失败: {e}")
        return []
    except json.JSONDecodeError:
        print(f"[PH] API 返回非 JSON")
        return []

    edges = data.get("data", {}).get("posts", {}).get("edges", [])
    if not edges:
        print(f"[PH] 近 2 天暂无新品数据")
        return []

    signals = []
    for edge in edges:
        node = edge.get("node", {})
        if not node:
            continue

        ph_id = node.get("id", "")
        name = node.get("name", "")
        tagline = node.get("tagline", "") or ""
        description = node.get("description", "") or ""

        votes = node.get("votesCount", 0)
        comments = node.get("commentsCount", 0)
        url = node.get("url") or node.get("website", "") or f"https://www.producthunt.com/posts/{node.get('slug', ph_id)}"

        user = node.get("user", {}) or {}
        author = user.get("name") or user.get("username", "")

        topics = []
        for t_edge in (node.get("topics", {}) or {}).get("edges", []):
            t_node = t_edge.get("node", {}) if t_edge else {}
            t_name = t_node.get("name", "")
            if t_name:
                topics.append(t_name)

        title = f"{name}: {tagline}" if tagline else name

        signals.append({
            "id": f"ph-{ph_id}",
            "title": title.strip()[:120],
            "url": url,
            "source": "Product Hunt",
            "source_key": "producthunt",
            "signal_type": "product-launch",
            "discussion_count": comments,
            "engagement": {
                "votes": votes,
                "comments": comments,
                "total": votes + comments * 3,  # 真实互动数据
            },
            "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
            "raw_created_at": node.get("createdAt", ""),
            "summary": f"[Product Hunt] {name}: {tagline[:100]}（{votes} 票 / {comments} 评论）",
            "tags": ["product-launch"] + topics[:5],
            "author": author,
        })

    # 按互动量排序
    signals.sort(key=lambda s: s["engagement"]["total"], reverse=True)
    signals = signals[:40]

    print(f"[PH] API 采集 {len(signals)} 条产品 (含投票/评论数据)")
    return signals


def save_raw(signals: list[dict], date_str: str) -> None:
    """保存到 ./raw/YYYY-MM-DD/producthunt.json"""
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "producthunt",
        "api": "GraphQL v2 (developer token)",
        "count": len(signals),
        "signals": signals,
    }
    path = dir_path / "producthunt.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[PH] {len(signals)} 条信号 → {path}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
