"""
Substack Newsletter 信号采集 (v1.0)
数据源: Substack RSS feeds (https://{publication}.substack.com/feed)
采集内容: AI/创业/技术类头部 newsletter 最新文章标题和摘要

价值: 独立分析师和行业专家在 Substack 发布付费级深度内容。
很多趋势在被 HN/Reddit 讨论之前，先出现在这些 newsletter 中。
这是"专家预判"信号的最佳来源。
"""
import json
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"

TZ_SHANGHAI = timezone(timedelta(hours=8))

# ── UA 轮换池 ──
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0",
]

# ── 限速配置 ──
FEED_DELAY_S = 3           # 订阅源间基础间隔
MAX_RETRIES = 2             # 最大重试次数
RETRY_DELAY = 10            # 重试等待 (秒)

# ── 精选 Substack 信源列表 ──
# 选源标准: (1) 有独立观点 (2) 关注 AI/创业/技术趋势 (3) 更新频率稳定
PUBLICATIONS = [
    # ── 技术/AI 趋势 ──
    "thepragmaticengineer",     # 实用工程师 — 技术趋势、工程文化
    "aigrant",                  # AI Grant — AI 创业公司分析
    "every",                    # Every.to — AI + 商业策略
    "aisupremacy",             # AI Supremacy — AI 行业深度分析
    "bigtechnology",           # Big Technology — 科技大公司动态
    "platformer",              # Platformer — 科技与社会交叉
    # ── 创业/独立开发者 ──
    "lenny",                  # Lenny's Newsletter — 产品/增长/创业圣经
    "first1000",              # First 1000 — 用户增长策略
    "indiehackers",           # Indie Hackers — 独立开发者故事（已有独立采集，此为 newsletter）
    "startuppirate",          # Startup Pirate — 创业数据洞察
    # ── 技术深度 ──
    "bytebytego",             # ByteByteGo — 系统设计
    "engineercode",           # High Growth Engineer — 高增长工程实践
    # ── 经济/市场 ──
    # ── 经济/市场 ──
    "notboring",              # Not Boring — 科技 + 策略
    "chartr",                 # Chartr — 数据可视化 + 趋势
]


def _random_ua() -> str:
    import random
    return random.choice(_USER_AGENTS)


def _clean_xml(raw: bytes) -> bytes:
    """移除 XML 中的非法 surrogate 字符 (U+D800-U+DFFF)."""
    cleaned = bytearray()
    i = 0
    while i < len(raw):
        if i + 2 < len(raw):
            if raw[i] == 0xED and (raw[i + 1] & 0xF0) == 0xA0:
                i += 3
                continue
        cleaned.append(raw[i])
        i += 1
    return bytes(cleaned)


def _fetch_feed(pub: str) -> list[dict]:
    """获取一个 Substack 发布的 RSS feed 并提取文章。"""
    url = f"https://{pub}.substack.com/feed"
    entries = []

    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": _random_ua()},
                timeout=20,
            )
            if resp.status_code == 404:
                return []  # publication 不存在
            resp.raise_for_status()

            raw = _clean_xml(resp.content)
            root = ET.fromstring(raw)

            # Substack RSS 使用多种命名空间
            # 检测实际命名空间
            ns = ""
            for prefix, uri in root.nsmap.items() if hasattr(root, 'nsmap') else {}:
                if "rss" in str(uri).lower() or "atom" in str(uri).lower():
                    ns = f"{{{uri}}}"
                    break
            if not ns:
                ns = ""

            for item in root.findall(f".//item"):
                title_el = item.find("title")
                link_el = item.find("link")
                desc_el = item.find("description")
                pubdate_el = item.find("pubDate")

                title = title_el.text.strip() if title_el is not None and title_el.text else ""
                link = link_el.text.strip() if link_el is not None and link_el.text else ""
                description = desc_el.text.strip() if desc_el is not None and desc_el.text else ""
                pubdate = pubdate_el.text.strip() if pubdate_el is not None and pubdate_el.text else ""

                if len(title) < 5:
                    continue

                # 清理 HTML 标签
                clean_desc = re.sub(r"<[^>]+>", "", description)[:200]

                entries.append({
                    "title": title,
                    "url": link,
                    "description": clean_desc,
                    "pubdate": pubdate,
                    "publication": pub,
                })

            break  # 成功则跳出重试循环

        except requests.HTTPError as e:
            status = e.response.status_code if hasattr(e, 'response') else 0
            if status == 429 and attempt < MAX_RETRIES:
                print(f"  [Substack] {pub} 429 rate limited, waiting {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
                continue
            print(f"  [Substack] {pub} HTTP {status}: {e}")
            return []
        except (requests.RequestException, ET.ParseError) as e:
            if attempt < MAX_RETRIES:
                print(f"  [Substack] {pub} {type(e).__name__}, retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
                continue
            print(f"  [Substack] {pub} 最终失败: {e}")
            return []

    return entries


def _extract_tags(title: str, description: str) -> list[str]:
    """从标题和描述中提取主题标签。"""
    text = f"{title} {description}".lower()
    tags = []

    keyword_map = {
        "ai": ["ai-agent", "llm", "gpt", "claude", "gemini", "copilot"],
        "startup": ["startup", "saas", "funding", "yc", "venture"],
        "devtools": ["api", "sdk", "cli", "developer", "opensource", "open-source"],
        "infra": ["cloud", "kubernetes", "database", "serverless", "edge"],
        "trend": ["trend", "prediction", "forecast", "future", "2026", "2027"],
        "monetization": ["pricing", "subscription", "monetize", "revenue"],
    }

    for category, terms in keyword_map.items():
        for term in terms:
            if term in text:
                tags.append(category)
                break

    return list(set(tags))[:5]


def _to_signal(entry: dict) -> dict | None:
    """将 Substack entry 转为标准信号格式。"""
    title = entry.get("title", "")
    if len(title) < 10:
        return None

    pub = entry.get("publication", "")
    url = entry.get("url", "")
    description = entry.get("description", "")

    tags = _extract_tags(title, description)
    tags.append("newsletter")

    signal_id = f"substack-{pub}-{abs(hash(title)) % 10_000_000:07d}"

    return {
        "id": signal_id,
        "title": title[:200],
        "url": url,
        "source": f"Substack/{pub}",
        "source_key": "substack",
        "signal_type": "newsletter",
        "discussion_count": 0,
        "engagement": {
            "total": 5 + len(tags) * 2,  # newsletter 的 engagement 基于标签丰富度
        },
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "raw_created_at": entry.get("pubdate", ""),
        "summary": f"[Substack/{pub}] {title[:120]}" + (f" — {description[:80]}" if description else ""),
        "tags": tags[:6],
        "author": pub,
        "extra": {
            "publication": pub,
            "description": description[:300],
        },
    }


def collect(date_str: str | None = None) -> list[dict]:
    """采集 Substack newsletter 最新文章。"""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    seen: set[str] = set()
    signals: list[dict] = []

    for i, pub in enumerate(PUBLICATIONS):
        if i > 0:
            time.sleep(FEED_DELAY_S)

        entries = _fetch_feed(pub)
        count = 0
        for entry in entries:
            s = _to_signal(entry)
            if s and s["id"] not in seen:
                seen.add(s["id"])
                signals.append(s)
                count += 1

        if count > 0:
            print(f"[Substack] {pub}: {count} 篇")
        else:
            print(f"[Substack] {pub}: 0 篇 (未获取到)")

    # 按发布日期降序（最新的在前）
    signals.sort(key=lambda s: s.get("raw_created_at", ""), reverse=True)
    signals = signals[:50]

    # 统计 publication 分布
    pub_counts: dict[str, int] = {}
    for s in signals:
        pub = s.get("extra", {}).get("publication", "unknown")
        pub_counts[pub] = pub_counts.get(pub, 0) + 1

    print(f"[Substack] 总计: {len(signals)} 篇文章 (来自 {len(pub_counts)} 个 newsletter)")
    return signals


def save_raw(signals: list[dict], date_str: str) -> None:
    """保存到 ./raw/YYYY-MM-DD/substack.json"""
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "substack (RSS feeds)",
        "publications_monitored": len(PUBLICATIONS),
        "count": len(signals),
        "signals": signals,
    }
    path = dir_path / "substack.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[Substack] {len(signals)} 条信号 → {path}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
