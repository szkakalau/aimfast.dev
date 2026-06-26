"""
小红书 C 端信号采集 (v2.1 — 中文 C 端趋势第一来源)
数据源: 小红书公开页面 + (可选) 认证 Cookie
采集内容:
  - 小红书探索页热门笔记 — 消费趋势/产品种草/生活方式
  - 搜索热门关键词的笔记 — 垂直品类趋势

信号价值: 小红书是中文互联网最大的消费决策平台, 月活 3 亿+。
         用户发笔记分享购物/穿搭/家居/旅行/护肤/数码/母婴等所有消费品类。
         一个产品在小红书上"火"了, 通常意味着 1-2 周后会在电商平台爆发。

限制:
  - 不登录: 只能抓取探索页 (约 20 条/次), 无法搜索
  - 登录后: 可搜索、可翻页、数据量大 10x
  - 反爬严格: 需要浏览器级别的 Cookie + 签名参数

认证设置:
  1. 在浏览器中登录 xiaohongshu.com
  2. 打开 DevTools → Application → Cookies
  3. 复制 a1, web_session, webId 到 ~/.config/aimfast/xhs_cookies.json
  4. 格式: {"a1": "...", "web_session": "...", "webId": "..."}
"""
import json
import re
import time
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"

TZ_SHANGHAI = timezone(timedelta(hours=8))

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Origin": "https://www.xiaohongshu.com",
    "Referer": "https://www.xiaohongshu.com/explore",
}

# 小红书 API 端点
XHS_API = {
    "homefeed": "https://edith.xiaohongshu.com/api/sns/web/v1/homefeed",
    "search_notes": "https://edith.xiaohongshu.com/api/sns/web/v1/search/notes",
    "note_detail": "https://edith.xiaohongshu.com/api/sns/web/v1/feed",
}

# 消费趋势相关搜索关键词
CONSUMER_SEARCH_KEYWORDS = [
    "好物推荐", "新入", "开箱", "测评", "值得买",
    "神器", "提升幸福感", "居家好物", "数码好物",
    "小众品牌", "新品牌", "平替", "宝藏",
    "旅行必备", "办公桌搭", "租房改造", "桌面好物",
]


def _load_cookies() -> dict[str, str]:
    """加载小红书认证 Cookie。"""
    cookie_paths = [
        Path.home() / ".config" / "aimfast" / "xhs_cookies.json",
        ROOT / ".xhs_cookies.json",
    ]
    for p in cookie_paths:
        if p.exists():
            try:
                cookies = json.loads(p.read_text(encoding="utf-8"))
                if cookies.get("web_session") or cookies.get("a1"):
                    print(f"[小红书] 已加载认证 Cookie: {p}")
                    return cookies
            except (json.JSONDecodeError, KeyError):
                pass
    return {}


def _make_cookie_string(cookies: dict[str, str]) -> str:
    """将 cookie dict 转为 header 字符串。"""
    parts = []
    for k, v in cookies.items():
        parts.append(f"{k}={v}")
    return "; ".join(parts)


def _fetch_explore_feed(cookies: dict[str, str]) -> list[dict]:
    """
    获取小红书首页推荐流 (探索页)。

    无认证时: 可能返回空或有限数据
    有认证时: 返回个性化推荐, 数据量大
    """
    signals: list[dict] = []
    seen_ids: set[str] = set()

    headers = {**HEADERS}
    if cookies:
        headers["Cookie"] = _make_cookie_string(cookies)

    # X-S 签名 (简化版 — 完整的需要逆向 WASM, 这里用固定值尝试)
    # 注意: 小红书需要 X-S, X-S-Common, X-T 等签名参数。
    # 不登录时这些参数可能不需要。登录后必须签名。
    # 当前实现: 尝试不带签名的请求 (未登录模式)
    try:
        payload = {
            "page_size": 20,
            "sort": "general",
        }
        resp = requests.post(
            XHS_API["homefeed"],
            headers=headers,
            json=payload,
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                items = data.get("data", {}).get("items", [])
                for item in items:
                    note_card = item.get("note_card", {})
                    note_id = note_card.get("note_id", "")
                    if note_id in seen_ids:
                        continue
                    seen_ids.add(note_id)

                    title = note_card.get("display_title", "")
                    desc = note_card.get("desc", "")
                    if not title and not desc:
                        continue

                    # 互动数据
                    interact = note_card.get("interact_info", {})
                    likes = interact.get("liked_count", 0)
                    comments = interact.get("comment_count", 0)
                    collects = interact.get("collected_count", 0)
                    shares = interact.get("share_count", 0)

                    # 作者
                    author_info = note_card.get("user", {})
                    author = author_info.get("nickname", "")

                    # 标签 (消费趋势信号)
                    tags = []
                    tag_list = note_card.get("tag_list", [])
                    for t in tag_list:
                        t_name = t.get("name", "")
                        if t_name:
                            tags.append(t_name)

                    engagement_total = likes + comments * 5 + collects * 3 + shares * 2

                    signals.append({
                        "id": f"xhs-{note_id}",
                        "title": title[:100] if title else desc[:100],
                        "url": f"https://www.xiaohongshu.com/explore/{note_id}",
                        "source": "小红书-探索",
                        "source_key": "xiaohongshu",
                        "signal_type": "consumer_trend",
                        "discussion_count": comments,
                        "engagement": {
                            "likes": likes,
                            "comments": comments,
                            "collects": collects,
                            "shares": shares,
                            "total": engagement_total,
                        },
                        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
                        "raw_created_at": "",
                        "summary": f"[小红书] {title[:80] if title else desc[:80]}（{likes} 赞 / {collects} 收藏）",
                        "tags": ["xiaohongshu", "consumer"] + tags[:5],
                        "author": author,
                    })
                print(f"[小红书] 探索页: {len(items)} 条笔记 → {len(signals)} 条有效信号")
            else:
                msg = data.get("msg", "unknown error")
                print(f"[小红书] 探索页 API 返回失败: {msg}")
        elif resp.status_code == 471:
            print("[小红书] 探索页需要签名验证 (X-S header) — 当前为未登录模式, 数据量有限")
        else:
            print(f"[小红书] 探索页 HTTP {resp.status_code}")
    except requests.RequestException as e:
        print(f"[小红书] 探索页请求失败: {e}")
    except json.JSONDecodeError:
        print("[小红书] 探索页返回非 JSON")

    return signals


def _fetch_search_notes(keyword: str, cookies: dict[str, str]) -> list[dict]:
    """
    搜索小红书笔记 (需要认证 Cookie + 签名)。

    未认证时通常返回空或 471 (需要签名验证)。
    """
    if not cookies:
        return []  # 搜索需要认证

    signals: list[dict] = []
    seen_ids: set[str] = set()

    headers = {**HEADERS}
    if cookies:
        headers["Cookie"] = _make_cookie_string(cookies)

    try:
        payload = {
            "keyword": keyword,
            "page": 1,
            "page_size": 10,
            "sort": "general",
            "note_type": 0,  # 全部类型
        }
        resp = requests.post(
            XHS_API["search_notes"],
            headers=headers,
            json=payload,
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                items = data.get("data", {}).get("items", [])
                for item in items:
                    note_card = item.get("note_card", {})
                    note_id = note_card.get("note_id", "")
                    if note_id in seen_ids:
                        continue
                    seen_ids.add(note_id)

                    title = note_card.get("display_title", "")
                    desc = note_card.get("desc", "")
                    interact = note_card.get("interact_info", {})
                    likes = interact.get("liked_count", 0)
                    collects = interact.get("collected_count", 0)
                    comments = interact.get("comment_count", 0)

                    signals.append({
                        "id": f"xhs-search-{note_id}",
                        "title": f"小红书搜索「{keyword}」: {title[:60]}",
                        "url": f"https://www.xiaohongshu.com/explore/{note_id}",
                        "source": f"小红书-搜索-{keyword}",
                        "source_key": "xiaohongshu",
                        "signal_type": "consumer_trend",
                        "discussion_count": comments,
                        "engagement": {
                            "likes": likes,
                            "collects": collects,
                            "comments": comments,
                            "total": likes + collects * 3 + comments * 5,
                        },
                        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
                        "raw_created_at": "",
                        "summary": f"[小红书·{keyword}] {title[:80] if title else desc[:80]}（{likes} 赞 / {collects} 收藏）",
                        "tags": ["xiaohongshu", "consumer", keyword],
                        "author": note_card.get("user", {}).get("nickname", ""),
                    })
        elif resp.status_code == 471:
            print(f"[小红书] 搜索 '{keyword}' 需要签名验证")
        else:
            print(f"[小红书] 搜索 '{keyword}' HTTP {resp.status_code}")
    except requests.RequestException as e:
        print(f"[小红书] 搜索 '{keyword}' 请求失败: {e}")

    return signals


def _print_auth_help():
    """打印认证设置帮助。"""
    print("""
[小红书] ⚠️  未检测到认证 Cookie。将以「未登录模式」运行。
[小红书] 未登录模式只能抓取探索页约 20 条笔记, 无法搜索。
[小红书]
[小红书] 如何获取完整数据:
[小红书]   1. 浏览器打开 xiaohongshu.com 并登录
[小红书]   2. F12 → Application → Cookies → xiaohongshu.com
[小红书]   3. 复制 a1, web_session, webId 的值
[小红书]   4. 保存到 ~/.config/aimfast/xhs_cookies.json:
[小红书]      {"a1": "复制的值", "web_session": "复制的值", "webId": "复制的值"}
[小红书]
[小红书] 继续以未登录模式运行...
""")


def collect(date_str: str | None = None) -> list[dict]:
    """采集小红书 C 端消费趋势信号。"""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")

    cookies = _load_cookies()
    if not cookies:
        _print_auth_help()

    print(f"\n[小红书] 开始采集 C 端信号...")
    signals: list[dict] = []

    # 探索页热门
    explore_signals = _fetch_explore_feed(cookies)
    signals.extend(explore_signals)

    # 搜索消费趋势关键词 (需要认证)
    if cookies:
        for kw in CONSUMER_SEARCH_KEYWORDS[:5]:  # 限 5 个关键词避免限速
            time.sleep(3)
            search_signals = _fetch_search_notes(kw, cookies)
            signals.extend(search_signals)
    else:
        print("[小红书] 跳过搜索 (需要认证 Cookie)")

    # 去重 + 排序
    seen: set[str] = set()
    unique: list[dict] = []
    for s in signals:
        if s["id"] not in seen:
            seen.add(s["id"])
            unique.append(s)
    unique.sort(key=lambda s: s["engagement"]["total"], reverse=True)
    unique = unique[:40]

    authed = "已认证" if cookies else "未登录"
    print(f"[小红书] 总计: {len(unique)} 条 C 端信号 (模式: {authed})")

    if not cookies:
        print("[小红书] 💡 设置认证 Cookie 后数据量可提升 5-10x, 并可获取搜索趋势")

    return unique


def save_raw(signals: list[dict], date_str: str) -> None:
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    cookies = _load_cookies()
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "xiaohongshu (API)",
        "authenticated": bool(cookies),
        "count": len(signals),
        "signals": signals,
    }
    path = dir_path / "xiaohongshu.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[小红书] {len(signals)} 条信号 → {path}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
