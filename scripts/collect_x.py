"""
X/Twitter 信号采集器 v2.2
数据源层级 (自动降级):
  1. last30days/bird (Firefox cookie 自动提取 → X GraphQL API) — 质量最高
  2. X API v2 Free (Bearer Token) — 需要开发者账号, 官方接口
  3. 零认证兜底 (公开 trends + syndication) — 无任何配置要求

认证: last30days 引擎会自动从 Firefox 提取 auth_token + ct0
      也支持手动设置: ~/.config/last30days/.env 中的 AUTH_TOKEN + CT0
      或 X_API_BEARER_TOKEN (X API v2)
"""
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"
CONFIG_PATH = ROOT / "config.json"

TZ_SHANGHAI = timezone(timedelta(hours=8))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AimFast-Dev/2.2; +https://aimfast.dev)"
}

# X API v2 搜索端点 (需要 Bearer Token)
X_API_V2_SEARCH = "https://api.x.com/2/tweets/search/recent"

# XTapDown trends API (公开, 无需认证)
XTAPDOWN_TRENDS = "https://xtapdown.com/api/trends"

# X 公开 syndication 端点 (获取单条推文详情, 无需认证)
SYNDICATION_API = "https://cdn.syndication.twimg.com/tweet-result"

# Node.js 代理引导脚本 — 让 undici fetch 走 HTTP_PROXY/HTTPS_PROXY
_NODE_PROXY_SETUP_MJS = ROOT / "scripts" / "node_proxy_setup.mjs"

# 每日搜索话题
DAILY_QUERIES = [
    "AI agent developer tool launch",
    "open source dev tool shipping",
    "indie hacker SaaS launch",
    "YC startup launch product",
    "Claude Code AI coding",
]

# ── last30days 引擎路径解析 ──


def _find_last30days_engine() -> tuple[Path | None, str]:
    """查找 last30days 引擎路径和 Python 解释器。"""
    cache_base = Path.home() / ".claude" / "plugins" / "cache" / "last30days-skill" / "last30days"
    engine = None
    if cache_base.exists():
        for ver_dir in sorted(
            [d for d in cache_base.iterdir() if d.is_dir()], reverse=True
        ):
            candidate = ver_dir / "skills" / "last30days" / "scripts" / "last30days.py"
            if candidate.exists():
                engine = candidate
                break
    return engine, sys.executable


# ── 认证预检 ──


def _check_x_auth_available(engine_path: Path | None) -> tuple[bool, bool, dict]:
    """快速检查 X 认证是否可用, 避免无谓的全量查询 (~50s 浪费)。

    直接尝试从 Firefox cookies.sqlite 提取 auth_token + ct0,
    绕过 bird_x.is_bird_authenticated() 的静态检查（它只检查已注入的凭证）。

    Returns:
        (bird_ok, api_v2_ok, extracted_creds)
    """
    bird_ok = False
    api_v2_ok = False
    extracted_creds: dict = {}

    # 1. 从环境变量检查
    if os.environ.get("AUTH_TOKEN") and os.environ.get("CT0"):
        bird_ok = True

    # 2. 从 Firefox cookie 自动提取
    if not bird_ok and engine_path is not None:
        try:
            import importlib.util

            cookie_extract_path = engine_path.parent / "lib" / "cookie_extract.py"
            if cookie_extract_path.exists():
                spec = importlib.util.spec_from_file_location(
                    "cookie_extract", str(cookie_extract_path)
                )
                cookie_extract = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(cookie_extract)

                result = cookie_extract.extract_cookies_with_source(
                    "firefox", ".x.com", ["auth_token", "ct0"]
                )
                if result:
                    cookies, source = result
                    if cookies.get("auth_token") and cookies.get("ct0"):
                        bird_ok = True
                        extracted_creds = {
                            "AUTH_TOKEN": cookies["auth_token"],
                            "CT0": cookies["ct0"],
                        }
        except Exception:
            pass

    # 3. 检查 X API v2
    if _get_x_api_bearer_token():
        api_v2_ok = True

    return bird_ok, api_v2_ok, extracted_creds


# ── Tier 1: last30days / bird 搜索 ──


def _search_via_last30days(
    topic: str,
    engine_path: Path,
    python_path: str,
    timeout_s: int = 120,
    extra_env: dict | None = None,
) -> list[dict]:
    """用 last30days 引擎搜索 X。

    认证来源（优先级）：
    1. extra_env 中注入的 AUTH_TOKEN/CT0（已从 Firefox 提取）
    2. 引擎内部 get_config() → Firefox cookie 自动提取
    3. ~/.config/last30days/.env 手动配置

    返回原始信号列表 (last30days compact 格式解析后)。
    """
    start = time.time()
    env = dict(os.environ)

    # 检测系统代理 — Node.js 的 undici fetch 不会自动读取 HTTP_PROXY，
    # 需要通过 NODE_OPTIONS=--import 注入代理引导脚本
    proxy_url = (
        env.get("HTTPS_PROXY") or env.get("https_proxy")
        or env.get("HTTP_PROXY") or env.get("http_proxy")
    )
    if proxy_url and _NODE_PROXY_SETUP_MJS.exists():
        existing_opts = env.get("NODE_OPTIONS", "")
        # Node.js 24 --import 需要 file:// URL（自动处理路径空格等特殊字符）
        import_url = _NODE_PROXY_SETUP_MJS.resolve().as_uri()
        import_flag = f"--import={import_url}"
        if import_flag not in existing_opts:
            env["NODE_OPTIONS"] = f"{existing_opts} {import_flag}".strip()

    env["LAST30DAYS_NATIVE_SEARCH"] = "0"
    # 注入预先提取的 cookie (跳过引擎内部的浏览器 cookie 提取)
    if extra_env:
        env.update(extra_env)

    cmd = [
        python_path,
        str(engine_path),
        topic,
        "--emit=compact",
        "--search=x",
        "--auto-resolve",
        "--max-items",
        "20",
        "--save-suffix=",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
            env=env,
        )
        stdout = result.stdout or ""
        stderr = result.stderr or ""
    except subprocess.TimeoutExpired:
        print(f"[X] L30D timeout searching '{topic}'")
        return []
    except Exception as e:
        print(f"[X] L30D engine error: {e}")
        return []

    elapsed = time.time() - start

    # 检查是否有认证错误
    if "no working X auth" in stderr.lower() or "auth" in stderr.lower():
        print(f"[X] L30D auth not available: {stderr.strip()[:120]}")

    signals = _parse_compact_output(stdout, topic)
    print(f"[X] L30D '{topic}' → {len(signals)} items ({elapsed:.1f}s)")
    return signals


def _parse_compact_output(output: str, query: str) -> list[dict]:
    """解析 last30days --emit=compact 输出中的 X 条目为 pipeline 信号。

    实际输出格式 (v3.7.0):
        ### N. Title (score N, M items, sources: X)   ← cluster header
        N. [x] Title                                    ← item line
           - YYYY-MM-DD | @handle | [Nlikes, Nrt] | score:N
           - URL: https://x.com/handle/status/ID
           - Evidence: ...
    """
    signals = []
    current_item: dict = {}
    current_cluster_score = 0

    for line in output.split("\n"):
        line_stripped = line.strip()

        # Cluster header: "### N. Title (score N, ...sources: X)"
        cluster_m = re.match(
            r"^###\s+\d+\.\s+(.+?)\s+\(score\s+(\d+).*sources:.*\bX\b",
            line_stripped,
        )
        if cluster_m:
            current_cluster_score = int(cluster_m.group(2))
            continue

        # Item line: "N. [x] Title ..."
        item_m = re.match(r"^\d+\.\s+\[x\]\s+(.+)", line_stripped)
        if item_m:
            if current_item and current_item.get("title"):
                signals.append(_to_signal(current_item, query, "last30days"))
            current_item = {
                "title": item_m.group(1).strip(),
                "score": current_cluster_score,
            }
            continue

        if not current_item:
            continue

        # 日期 + 互动: "- YYYY-MM-DD | @handle | [Nlikes, Nrt] | score:N"
        eng_m = re.match(
            r"-\s+(\d{4}-\d{2}-\d{2})\s*\|\s*@(\w+)\s*\|\s*\[(\d+)\s*(?:likes|like)",
            line_stripped,
        )
        if eng_m:
            current_item["raw_created_at"] = eng_m.group(1)
            current_item["author"] = eng_m.group(2)
            try:
                likes = int(eng_m.group(3))
                current_item["engagement"] = {"likes": likes, "total": likes}
            except (ValueError, IndexError):
                pass
            continue

        # URL: "- URL: https://x.com/handle/status/ID"
        url_m = re.match(
            r"-\s*URL:\s*(https?://(?:x\.com|twitter\.com)/\S+)", line_stripped
        )
        if url_m:
            current_item["url"] = url_m.group(1).strip()
            continue

        # Evidence: "- Evidence: ..."
        if line_stripped.startswith("- Evidence:") and "summary" not in current_item:
            current_item["summary"] = line_stripped.replace("- Evidence:", "").strip()[:200]
            continue

        # @handle fallback (from item title or elsewhere)
        if "author" not in current_item:
            handle_m = re.match(r"^\s*-\s*\d{4}-\d{2}-\d{2}\s*\|\s*@(\w+)", line_stripped)
            if handle_m:
                current_item["author"] = handle_m.group(1)

    # 保存最后一个
    if current_item and current_item.get("title"):
        signals.append(_to_signal(current_item, query, "last30days"))

    return signals


# ── Tier 2: X API v2 (Bearer Token) ──


def _search_via_x_api_v2(
    topic: str, bearer_token: str, max_results: int = 15
) -> list[dict]:
    """用 X API v2 搜索 (需要 Bearer Token, Free tier: 1500 tweets/月)。"""
    headers = {
        **HEADERS,
        "Authorization": f"Bearer {bearer_token}",
    }
    # 最近 2 天的推文
    since = (datetime.now(TZ_SHANGHAI) - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    params = {
        "query": f"{topic} -is:retweet lang:en",
        "max_results": max_results,
        "start_time": since,
        "tweet.fields": "created_at,public_metrics,author_id",
        "expansions": "author_id",
        "user.fields": "username",
    }

    try:
        resp = requests.get(X_API_V2_SEARCH, headers=headers, params=params, timeout=15)
        if resp.status_code != 200:
            print(f"[X] API v2 error {resp.status_code}: {resp.text[:120]}")
            return []
        data = resp.json()
    except requests.RequestException as e:
        print(f"[X] API v2 request failed: {e}")
        return []

    # 构建 user lookup
    users = {}
    for u in data.get("includes", {}).get("users", []):
        users[u["id"]] = u.get("username", "")

    signals = []
    for tweet in data.get("data", []):
        metrics = tweet.get("public_metrics", {})
        author = users.get(tweet.get("author_id", ""), "")
        tweet_id = tweet["id"]
        url = f"https://x.com/{author}/status/{tweet_id}" if author else ""

        signals.append(
            _to_signal(
                {
                    "title": tweet.get("text", topic)[:200],
                    "url": url,
                    "raw_created_at": tweet.get("created_at", ""),
                    "engagement": {
                        "likes": metrics.get("like_count", 0),
                        "reposts": metrics.get("retweet_count", 0),
                        "replies": metrics.get("reply_count", 0),
                        "total": sum(metrics.values()),
                    },
                    "author": author,
                    "summary": tweet.get("text", "")[:200],
                },
                topic,
                "x_api_v2",
            )
        )

    return signals


# ── Tier 3: 零认证兜底 (公开 trends + syndication) ──


def _fetch_trends(country: str = "US") -> list[dict]:
    """从 XTapDown 获取 X 趋势 (公开 API, 无需认证)。"""
    try:
        resp = requests.get(
            f"{XTAPDOWN_TRENDS}?country={country}",
            headers={"User-Agent": "AimFast-Dev/2.2"},
            timeout=10,
        )
        if resp.status_code != 200:
            print(f"[X] Trends API error {resp.status_code}")
            return []
        data = resp.json()
        return data.get("trends", [])
    except requests.RequestException as e:
        print(f"[X] Trends API request failed: {e}")
        return []


def _enrich_tweet(tweet_id: str) -> dict | None:
    """用 X 公开 syndication 端点获取单条推文详情 (无需认证)。"""
    # syndication token = (id / 1e15 * pi).toString(36) 去掉 0 和 .
    try:
        token = format(int(float(tweet_id) / 1e15 * 3.1415926535), ".20f")
        token = "".join(c for c in token.split(".")[-1] if c not in ("0", "."))
        # 取足够长度的 token
        token = token[:12] if len(token) >= 12 else token
    except (ValueError, OverflowError):
        return None

    url = f"{SYNDICATION_API}?id={tweet_id}&token={token}&lang=en"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return None
        return resp.json()
    except requests.RequestException:
        return None


def _extract_tweet_id(url_or_id: str) -> str:
    """从 URL 或纯 ID 中提取推文 ID。"""
    m = re.search(r"/status(?:es)?/(\d+)", url_or_id)
    if m:
        return m.group(1)
    if url_or_id.isdigit():
        return url_or_id
    return ""


def _collect_trends_as_signals() -> list[dict]:
    """将 X 趋势转为信号格式 (零认证模式)。"""
    trends = _fetch_trends("US")
    if not trends:
        print("[X] No trends available")
        return []

    signals = []
    for t in trends[:15]:  # 取 top 15 趋势
        name = t.get("name", "").lstrip("#")
        if not name or len(name) < 3:
            continue

        query = t.get("query", name)
        url = t.get("url", f"https://x.com/search?q={query}&src=trend")
        rank = t.get("rank", 0)
        is_hashtag = t.get("isHashtag", False)

        # 趋势没有推文级别的互动数据, 用排名估算
        estimated_volume = max(1, 50 - rank * 3)

        signal_id = f"x-trend-{abs(hash(name)) % 10_000_000:07d}"

        signals.append(
            {
                "id": signal_id,
                "title": f"#{name}" if is_hashtag else name,
                "url": url,
                "source": "X/Twitter Trends",
                "source_key": "x-trends",
                "signal_type": "trend",
                "discussion_count": estimated_volume,
                "engagement": {
                    "likes": 0,
                    "reposts": 0,
                    "replies": 0,
                    "total": estimated_volume,
                    "trend_rank": rank,
                },
                "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
                "raw_created_at": datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d"),
                "summary": f"X 趋势 #{rank}: {name} (约 {estimated_volume}K 讨论)",
                "tags": ["x", "trend", "tech"] if is_hashtag else ["x", "trend"],
                "author": "",
                "trend_rank": rank,
                "tier": "trends_fallback",
            }
        )

    print(f"[X] Trends → {len(signals)} signals (zero-auth)")
    return signals


# ── 信号格式转换 ──


def _to_signal(item: dict, query: str, tier: str) -> dict:
    """将 raw item 转为标准 pipeline 信号格式。"""
    title = item.get("title", query)[:200]
    url = item.get("url", "")
    engagement = item.get("engagement", {"likes": 0, "total": 0})
    likes = engagement.get("likes", 0)

    signal_id = f"x-{abs(hash(url or title)) % 10_000_000:07d}"

    return {
        "id": signal_id,
        "title": title,
        "url": url,
        "source": "X/Twitter",
        "source_key": "x",
        "signal_type": "post",
        "discussion_count": likes,
        "engagement": engagement,
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "raw_created_at": item.get("raw_created_at", ""),
        "summary": item.get("summary", title)[:200],
        "tags": ["x", "tech"],
        "author": item.get("author", ""),
        "tier": tier,
    }


# ── 主采集逻辑 ──


def _get_x_api_bearer_token() -> str | None:
    """从多个可能的位置读取 X API v2 Bearer Token。"""
    # 1. 环境变量
    token = os.environ.get("X_API_BEARER_TOKEN") or os.environ.get("TWITTER_BEARER_TOKEN")
    if token:
        return token

    # 2. config.json
    try:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        x_cfg = cfg.get("signals", {}).get("x", {})
        token = x_cfg.get("bearer_token") or x_cfg.get("api_key")
        if token:
            return token
    except (json.JSONDecodeError, OSError):
        pass

    # 3. last30days .env
    env_path = Path.home() / ".config" / "last30days" / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("X_API_BEARER_TOKEN="):
                return line.split("=", 1)[1].strip().strip("\"'")

    return None


def collect(date_str: str | None = None) -> list[dict]:
    """采集 X 当日信号 (按数据源层级自动降级)。

    返回标准信号列表。
    """
    # 加载配置
    cfg = {}
    try:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pass
    x_cfg = cfg.get("signals", {}).get("x", {})
    queries = x_cfg.get("queries", DAILY_QUERIES)
    max_total = x_cfg.get("max_total_items", 40)

    engine_path, python_path = _find_last30days_engine()
    bearer_token = _get_x_api_bearer_token()

    all_signals: list[dict] = []
    seen_urls: set[str] = set()
    tier_used = "none"

    # ── 认证预检 (直接提取 Firefox cookies, 避免无认证时浪费 ~50s) ──
    bird_ok, api_v2_ok, extracted_creds = _check_x_auth_available(engine_path)
    print(
        f"[X] Auth pre-check: bird={'OK' if bird_ok else 'N/A'}, "
        f"api_v2={'OK' if api_v2_ok else 'N/A'}"
    )

    # ── Tier 1: last30days (含 Firefox cookie 自动提取) ──
    if bird_ok and engine_path is not None:
        # 将提取到的 cookie 注入子进程环境变量
        search_env: dict = {}
        if extracted_creds:
            search_env = {
                "AUTH_TOKEN": extracted_creds["AUTH_TOKEN"],
                "CT0": extracted_creds["CT0"],
            }
            print("[X] Tier 1: probing X GraphQL API (30s timeout)...")

            # 快速探测：用第一个 query 测试连通性（30s 超时）
            # X API 在中国大陆可能被墙，不通则跳过避免浪费 10 分钟
            probe_results = _search_via_last30days(
                queries[0], engine_path, python_path, timeout_s=30, extra_env=search_env
            )
            if probe_results:
                print("[X] Tier 1 probe OK — searching all queries...")
                all_signals.extend(probe_results)
                for sig in probe_results:
                    url = sig.get("url", "")
                    if url:
                        seen_urls.add(url)

                # 继续搜剩余 query
                for query in queries[1:]:
                    if len(all_signals) >= max_total:
                        break
                    results = _search_via_last30days(
                        query, engine_path, python_path, timeout_s=45, extra_env=search_env
                    )
                    for sig in results:
                        url = sig.get("url", "")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            all_signals.append(sig)
            else:
                print(
                    "[X] Tier 1 probe failed (X API unreachable from CN — "
                    "use VPN/proxy or set X_API_BEARER_TOKEN with proxy)"
                )
        else:
            print("[X] Tier 1: searching via last30days/bird...")
            for query in queries:
                results = _search_via_last30days(
                    query, engine_path, python_path, extra_env=search_env
                )
                for sig in results:
                    url = sig.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_signals.append(sig)
                if len(all_signals) >= max_total:
                    break

        if all_signals:
            tier_used = "last30days"
            print(f"[X] Tier 1 success: {len(all_signals)} signals via last30days")
        else:
            print("[X] Tier 1 returned 0 signals (X API may be blocked in CN)")

    elif engine_path is not None:
        print("[X] Tier 1 skipped (no X auth detected — log into Firefox X or set AUTH_TOKEN)")

    # ── Tier 2: X API v2 ──
    if not all_signals and api_v2_ok and bearer_token:
        print("[X] Tier 2: searching via X API v2...")
        for query in queries:
            results = _search_via_x_api_v2(query, bearer_token)
            for sig in results:
                url = sig.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_signals.append(sig)
            if len(all_signals) >= max_total:
                break

        if all_signals:
            tier_used = "x_api_v2"
            print(f"[X] Tier 2 success: {len(all_signals)} signals via X API v2")
        else:
            print("[X] Tier 2 returned 0 signals")

    elif bearer_token:
        print("[X] Tier 2 returned 0 signals")

    # ── Tier 3: 零认证兜底 (公开 trends) ──
    if not all_signals:
        print("[X] Tier 3: falling back to public trends (zero-auth)...")
        all_signals = _collect_trends_as_signals()
        if all_signals:
            tier_used = "trends_fallback"

    # 去重 + 排序 (按互动量)
    all_signals.sort(
        key=lambda s: s.get("engagement", {}).get("total", 0), reverse=True
    )
    all_signals = all_signals[:max_total]

    if all_signals:
        print(
            f"[X] collected {len(all_signals)} signals total "
            f"(tier={tier_used}, de-duplicated)"
        )
    else:
        print(
            "[X] WARNING: No signals collected. "
            "To enable X search: log into X on Firefox, or set X_API_BEARER_TOKEN in config."
        )

    return all_signals


# ── CLI ──


def run():
    """CLI 入口 — 采集并保存到 raw/ 目录。"""
    date_str = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    print(f"[X] X/Twitter 信号采集 v2.2 — {date_str}")

    signals = collect(date_str)
    if not signals:
        print("[X] no signals collected — skip save")
        return

    # 统计 tier 分布
    tier_counts: dict[str, int] = {}
    for s in signals:
        t = s.get("tier", "unknown")
        tier_counts[t] = tier_counts.get(t, 0) + 1
    print(f"[X] tier distribution: {tier_counts}")

    # 保存到 raw/{date}/x.json
    output_dir = RAW_DIR / date_str
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "x.json"
    output_path.write_text(
        json.dumps(
            {
                "signals": signals,
                "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
                "tier_distribution": tier_counts,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[X] saved {len(signals)} signals → {output_path}")


if __name__ == "__main__":
    run()
