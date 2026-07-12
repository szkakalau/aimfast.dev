"""
与 BuilderPulse 方法论文本对比脚本
每天自动拉取 BuilderPulse 当日内容，与 KAKAOPC 输出进行结构化对比。

用法:
  python scripts/compare_with_builderpulse.py                          # 对比今天
  python scripts/compare_with_builderpulse.py --date 2026-05-27        # 对比指定日期
  python scripts/compare_with_builderpulse.py --from 2026-05-27 --to 2026-06-03  # 批量对比
  python scripts/compare_with_builderpulse.py --from 2026-05-27        # 从指定日期到今天的批量对比

输出:
  compare/YYYY-MM-DD.md  — 单日对比报告
  compare/SUMMARY.md     — 累计方法论差异总结（自动更新）
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
COMPARE_DIR = ROOT / "compare"
COMPARE_DIR.mkdir(exist_ok=True)

# ── BuilderPulse 仓库配置 ──────────────────────────────────
BP_RAW_BASE = "https://raw.githubusercontent.com/BuilderPulse/BuilderPulse/main"
BP_LANGS = ("zh", "en")

# ── 对比维度权重（用于差异显著性判断） ──────────────────────
COMPARE_DIMENSIONS = [
    "build_idea",       # 核心构建建议
    "why_now",          # 时机理由
    "signal_sources",   # 信号来源
    "signal_strength",  # 信号强度评估
    "pricing",          # 定价模型
    "buyer_target",     # 目标买家
    "validation",       # 验证路径
    "risk_view",        # 风险/反方视角
]


# ══════════════════════════════════════════════════════════════
# 工具函数
# ══════════════════════════════════════════════════════════════

def fetch_url(url: str, retries: int = 2) -> Optional[str]:
    """拉取 URL 内容，带重试"""
    for attempt in range(retries + 1):
        try:
            req = Request(url, headers={"User-Agent": "AimFast-Compare/1.0"})
            with urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8")
        except HTTPError as e:
            if e.code == 404:
                return None
            if attempt < retries:
                time.sleep(1)
        except Exception:
            if attempt < retries:
                time.sleep(1)
    return None


def builderpulse_exists(date_str: str) -> bool:
    """检查 BuilderPulse 某天是否有内容"""
    url = f"{BP_RAW_BASE}/zh/{date_str[:4]}/{date_str}.md"
    return fetch_url(url) is not None


def list_existing_dates_from_bp(start_date: str, end_date: str) -> list[str]:
    """列出 BuilderPulse 在日期范围内存在内容的日期"""
    existing = []
    d = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    while d <= end:
        ds = d.strftime("%Y-%m-%d")
        if builderpulse_exists(ds):
            existing.append(ds)
        d += timedelta(days=1)
    return existing


# ══════════════════════════════════════════════════════════════
# 内容提取
# ══════════════════════════════════════════════════════════════

def extract_bp_sections(md: str) -> dict:
    """从 BuilderPulse Markdown 中提取结构化信息

    BuilderPulse 有两个版本格式：
    - 中文版 (zh/): ## 🎯 今日 2 小时构建 + **Build Idea** 格式
    - 英文版 (en/): ## 🏗️ The Build Idea: **Title** 格式
    """
    sections = {
        "build_idea": "",
        "why_now": "",
        "signal_strength": "",
        "pricing": "",
        "buyer_target": "",
        "validation": "",
        "risk_view": "",
        "sourced_links": [],
        "alternative_ideas": [],
    }

    # ── 提取 Build Idea 标题 ──
    # 中文版格式: ## 🎯 今日 2 小时构建\n\n**AI Review Ledger**
    zh_build = re.search(
        r'##\s*🎯\s*今日.*?构建.*?\n\n\*?\*?(.+?)\*?\*?(?:\s*—|\s*–|\s*\n)',
        md, re.M
    )
    if zh_build:
        sections["build_idea"] = zh_build.group(1).strip()

    # 英文版格式: ## 🏗️ (The|Core)? Build Idea: **Title**
    if not sections["build_idea"]:
        en_build = re.search(
            r'##\s*(?:🏗️\s*)?(?:The\s+)?(?:Core\s+)?Build(?:\s+Idea)?[：:]\s*\*?\*?(.+?)\*?\*?',
            md, re.M | re.I
        )
        if en_build:
            sections["build_idea"] = en_build.group(1).strip()

    # 备用: ## The Build: **Title**
    if not sections["build_idea"]:
        alt_build = re.search(
            r'##\s*The\s+Build[：:]\s*\*?\*?(.+?)\*?\*?',
            md, re.M | re.I
        )
        if alt_build:
            sections["build_idea"] = alt_build.group(1).strip()

    # ── 中文版专用提取 ──
    # "谁会最先付钱？"
    buyer_zh = re.search(r'谁会最先付钱[？?](.+?)(?:\n\n|\n#{1,3}\s)', md, re.S)
    if buyer_zh:
        sections["buyer_target"] = buyer_zh.group(1).strip()[:300]

    # "为什么是这周？"
    why_zh = re.search(r'为什么是这周[？?](.+?)(?:\n\n|\n#{1,3}\s)', md, re.S)
    if why_zh:
        sections["why_now"] = why_zh.group(1).strip()[:500]

    # ── 提取所有二级标题作为段落标记（英文版 fallback） ──
    current_section = None
    section_content = {}
    for line in md.split("\n"):
        h2 = re.match(r'^##\s+(.+)$', line)
        if h2:
            current_section = h2.group(1).strip()
            section_content[current_section] = []
        elif current_section:
            section_content[current_section].append(line)

    for key, lines in section_content.items():
        content = "\n".join(lines).strip()
        lower_key = key.lower()

        if not sections["why_now"] and "why now" in lower_key:
            sections["why_now"] = content[:500]
        elif "signal" in lower_key and "strength" in lower_key:
            sections["signal_strength"] = content[:500]
        elif "pric" in lower_key:
            sections["pricing"] = content[:300]
        elif not sections["buyer_target"] and any(
            w in content.lower() for w in ["buyer", "target", "customer", "who pay"]
        ):
            sections["buyer_target"] = content[:300]
        elif "valid" in lower_key or "test" in lower_key:
            sections["validation"] = content[:300]
        elif "risk" in lower_key or "counter" in lower_key or "reverse" in lower_key:
            sections["risk_view"] = content[:300]

    # ── 快取 ──
    price_matches = re.findall(
        r'\$(\d+(?:[.,]\d+)?)\s*(?:[-–/]\s*\$?(\d+(?:[.,]\d+)?))?\s*(?:/|per\s+)?(month|mo|one-shot|report|audit|year|yr|月|年)',
        md, re.I
    )
    sections["extracted_prices"] = price_matches

    links = re.findall(r'\[([^\]]+)\]\(((?:https?://|/)[^\)]+)\)', md)
    sections["sourced_links"] = [{"text": t, "url": u} for t, u in links[:50]]

    platforms = ["Hacker News", "Reddit", "Product Hunt", "GitHub", "HuggingFace",
                 "Indie Hackers", "Lobsters", "DEV Community", "Google Trends",
                 "V2EX", "w2solo"]
    sections["mentioned_platforms"] = [p for p in platforms if p.lower() in md.lower()]

    discussion_numbers = re.findall(
        r'(\d{1,3}(?:,\d{3})*)\s*(?:comments?|条评论|条讨论|discussions?|comments?\s+threads?)',
        md, re.I
    )
    sections["discussion_volumes"] = [int(n.replace(",", "")) for n in discussion_numbers]

    return sections


def extract_kp_sections(date_str: str) -> dict:
    """从 KAKAOPC 当日输出中提取结构化信息

    KAKAOPC 有两个版本格式：
    - v1 (May 27): # AimFast.Dev日报 + ## 🎯 今日一击 + ### 信号：
    - v2 (May 28+): # 📝 主编说 + # 🎯 今日 2 小时构建 + ## Product:
    """
    sections = {
        "build_idea": "",
        "why_now": "",
        "signal_strength": "",
        "pricing": "",
        "buyer_target": "",
        "validation": "",
        "risk_view": "",
        "sourced_links": [],
        "alternative_ideas": [],
        "total_raw_signals": 0,
        "top_signals": [],
        "article_topic": "",
    }

    # 读 signals.json
    signals_path = ROOT / "daily" / date_str / "signals.json"
    if signals_path.exists():
        try:
            data = json.loads(signals_path.read_text(encoding="utf-8"))
            sections["total_raw_signals"] = data.get("total_raw", 0)
            for s in data.get("signals", [])[:5]:
                sections["top_signals"].append({
                    "title": s.get("title", ""),
                    "source": s.get("source", ""),
                    "score": s.get("score", 0),
                    "cross_platform": s.get("cross_platform_count", 0),
                    "discussion_count": s.get("discussion_count", 0),
                })
        except Exception:
            pass

    # 读 report.md
    report_path = ROOT / "daily" / date_str / "report.md"
    if report_path.exists():
        try:
            md = report_path.read_text(encoding="utf-8")

            # ── v1 格式: ### 信号：Title (May 27) ──
            m = re.search(r'###\s*信号[：:]\s*(.+?)(?:\n|$)', md)
            if m:
                sections["build_idea"] = m.group(1).strip()

            # ── v1 格式: 备选——从 ## 🎯 今日一击 段落提取 ──
            if not sections["build_idea"]:
                block = re.search(r'##\s*🎯\s*今日一击\n\n(.+?)(?=\n##|\n---|\Z)', md, re.S)
                if block:
                    first_line = block.group(1).strip().split("\n")[0]
                    sections["build_idea"] = first_line[:200]

            # ── v2 格式: # 🎯 今日 2 小时构建 → ## Product: Name ──
            if not sections["build_idea"]:
                product = re.search(r'##\s*Product[：:]\s*(.+?)(?:\n|$)', md)
                if product:
                    sections["build_idea"] = product.group(1).strip()

            # ── v2 备选: **一句话描述** ──
            if not sections["build_idea"]:
                desc = re.search(r'\*\*一句话描述\*\*[：:]\s*(.+?)(?:\n|$)', md)
                if desc:
                    sections["build_idea"] = desc.group(1).strip()[:200]

            # ── v2 备选: # 📝 主编说 段落中的加粗标题 ──
            if not sections["build_idea"]:
                editor_note = re.search(
                    r'真正可构建的信号是[：:]\s*\*?\*?(.+?)\*?\*?(?：|。|\n)',
                    md
                )
                if editor_note:
                    sections["build_idea"] = editor_note.group(1).strip()[:200]

            # ── 提取 Why Now / 主编说 ──
            editor = re.search(r'#\s*📝\s*主编说\n\n(.+?)(?=\n---|\n#)', md, re.S)
            if editor:
                sections["why_now"] = editor.group(1).strip()[:500]
            else:
                # v1 fallback
                core = re.search(r'##\s*今日核心判断\n\n(.+?)(?=\n---|\n##)', md, re.S)
                if core:
                    sections["why_now"] = core.group(1).strip()[:500]

            # ── 提取谁会先付钱 ──
            buyer = re.search(r'谁会先付钱[？?]\*?\*?(.+?)(?：|。|\n)', md)
            if buyer:
                sections["buyer_target"] = buyer.group(1).strip()[:200]
            elif not sections["buyer_target"]:
                # v1 fallback: "谁会付钱"
                buyer2 = re.search(r'\*\*谁会付钱[？?]\*?\*?\s*(.+?)(?:\n|$)', md)
                if buyer2:
                    sections["buyer_target"] = buyer2.group(1).strip()[:200]

            # ── 提取定价 ──
            pricing_block = re.search(r'##\s*定价\n\n(.+?)(?=\n##|\n---|\Z)', md, re.S)
            if pricing_block:
                sections["pricing"] = pricing_block.group(1).strip()[:300]

            # ── 提取验证路径 ──
            validation = re.search(r'##\s*最快验证路径\n\n(.+?)(?=\n##|\n---|\Z)', md, re.S)
            if validation:
                sections["validation"] = validation.group(1).strip()[:400]

            # ── v1: 提取 Counter-view ──
            cv = re.search(r'\*?\*?Counter-view[：:]\*?\*?\s*(.+?)(?=\n\n|\n---|\Z)', md, re.S | re.I)
            if cv:
                sections["risk_view"] = cv.group(1).strip()[:500]

            # ── 通用提取 ──
            prices = re.findall(
                r'\$(\d+(?:[.,]\d+)?)\s*(?:[-–/]\s*\$?(\d+(?:[.,]\d+)?))?\s*(?:/|per\s+)?(月|年|month|mo|年|yr)',
                md
            )
            sections["extracted_prices"] = prices

            links = re.findall(r'\[([^\]]+)\]\(((?:https?://|/)[^\)]+)\)', md)
            sections["sourced_links"] = [{"text": t, "url": u} for t, u in links[:50]]

            platforms = ["Hacker News", "Reddit", "Product Hunt", "GitHub", "HuggingFace",
                         "Indie Hackers", "Lobsters", "DEV Community", "Google Trends",
                         "V2EX", "w2solo"]
            sections["mentioned_platforms"] = [p for p in platforms if p.lower() in md.lower()]

            discussion_numbers = re.findall(
                r'(\d{1,3}(?:,\d{3})*)\s*(?:评论|条评论|条讨论|讨论|comments?)',
                md, re.I
            )
            sections["discussion_volumes"] = [int(n.replace(",", "")) for n in discussion_numbers]

        except Exception:
            pass

    return sections


# ══════════════════════════════════════════════════════════════
# 对比逻辑
# ══════════════════════════════════════════════════════════════

def compare_build_ideas(bp: dict, kp: dict) -> str:
    """对比核心 Build Idea"""
    bp_idea = bp.get("build_idea", "")
    kp_idea = kp.get("build_idea", "")

    if not bp_idea and not kp_idea:
        return "⚠️ 双方均无明确的 Build Idea"
    if not bp_idea:
        return f"🔴 **BuilderPulse 无数据** — KAKAOPC 识别到: _{kp_idea[:200]}_"
    if not kp_idea:
        return f"🟡 **KAKAOPC 报告缺失** — BuilderPulse 建议: _{bp_idea[:200]}_"

    # 做简单的语义重叠判断（基于关键词交集）
    def keywords(text: str) -> set:
        stop = {"the", "a", "an", "is", "are", "was", "were", "to", "of", "in", "for",
                "on", "and", "or", "not", "with", "that", "this", "it", "as", "at",
                "be", "by", "from", "has", "have", "had", "can", "will", "would"}
        words = set(re.findall(r'[a-zA-Z一-鿿]{2,}', text.lower()))
        return words - stop

    k1 = keywords(bp_idea)
    k2 = keywords(kp_idea)
    overlap = k1 & k2
    union = k1 | k2
    similarity = len(overlap) / len(union) if union else 0

    if similarity > 0.4:
        return f"🟢 **高度一致** (关键词重叠 {similarity:.0%})\n- BuilderPulse: _{bp_idea[:200]}_\n- KAKAOPC: _{kp_idea[:200]}_"
    elif similarity > 0.15:
        return f"🟡 **部分重叠** (关键词重叠 {similarity:.0%})\n- BuilderPulse: _{bp_idea[:200]}_\n- KAKAOPC: _{kp_idea[:200]}_"
    else:
        return f"🔴 **方向不同** (关键词重叠 {similarity:.0%})\n- BuilderPulse: _{bp_idea[:200]}_\n- KAKAOPC: _{kp_idea[:200]}_"


def compare_platforms(bp: dict, kp: dict) -> str:
    """对比信号来源平台覆盖"""
    bp_platforms = set(bp.get("mentioned_platforms", []))
    kp_platforms = set(kp.get("mentioned_platforms", []))

    if not bp_platforms:
        return "⚠️ BuilderPulse 无平台数据"

    overlap = bp_platforms & kp_platforms
    bp_only = bp_platforms - kp_platforms
    kp_only = kp_platforms - bp_platforms

    lines = [f"- 共同覆盖: **{len(overlap)}** 平台 ({', '.join(sorted(overlap)) if overlap else '无'})"]
    if bp_only:
        lines.append(f"- BuilderPulse 独有: {', '.join(sorted(bp_only))}")
    if kp_only:
        lines.append(f"- KAKAOPC 独有: {', '.join(sorted(kp_only))}")
    return "\n".join(lines)


def compare_discussion_volume(bp: dict, kp: dict) -> str:
    """对比讨论量"""
    bp_vol = bp.get("discussion_volumes", [])
    kp_vol = kp.get("discussion_volumes", [])

    bp_max = max(bp_vol) if bp_vol else 0
    kp_max = max(kp_vol) if kp_vol else 0

    lines = [
        f"- BuilderPulse 引用最高讨论量: **{bp_max:,}**",
        f"- KAKAOPC 引用最高讨论量: **{kp_max:,}**",
        f"- BuilderPulse 总信号数: N/A (纯内容仓库)",
        f"- KAKAOPC 原始信号数: **{kp.get('total_raw_signals', 'N/A')}**",
    ]
    return "\n".join(lines)


def compare_pricing(bp: dict, kp: dict) -> str:
    """对比定价模型"""
    bp_prices = bp.get("extracted_prices", [])
    kp_prices = kp.get("extracted_prices", [])

    lines = []
    if bp_prices:
        lines.append(f"- BuilderPulse 建议定价: {bp_prices[:3]}")
    else:
        lines.append("- BuilderPulse: 未提取到定价信息")
    if kp_prices:
        lines.append(f"- KAKAOPC 建议定价: {kp_prices[:3]}")
    else:
        lines.append("- KAKAOPC: 未提取到定价信息")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# 方法论差异（累计）
# ══════════════════════════════════════════════════════════════

METHODOLOGY_DIFFS = """
## 方法论差异总结

> 以下差异基于从 2026-05-27 起的逐日对比。每次运行 `--from 2026-05-27` 时自动更新。

### 架构层差异

| 维度 | BuilderPulse | AimFast.Dev |
|------|-------------|---------------|
| **定位** | 每日一条 Build Idea 的纯内容简报 | 完整情报管线：采集→评分→生成→验证→部署 |
| **仓库性质** | 纯 Markdown 内容仓库 | Next.js 全栈应用 + Python 数据管道 |
| **输出格式** | 1 条 Build Idea + Why Now + 信号链接 | 5 层日报 + 深度文章 + 落地页 |
| **信号源数量** | ~9 个（全英文） | 14 个（9 海外 + 5 中国） |
| **中国信号** | ❌ 无 | ✅ V2EX / w2solo |
| **LLM 集成** | 不透明（推测后端使用） | 透明：DeepSeek API，月预算 $20 |
| **发布渠道** | GitHub + builderpulse.ai | aimfast.dev（Vercel 静态站点） |

### 方法论层差异

| 维度 | BuilderPulse | AimFast.Dev |
|------|-------------|---------------|
| **评分系统** | 无公开评分公式 | E-P-A 加权公式：cross×3 + vol×2 + fresh×2 + act×2 + buyer×1 |
| **行动阈值** | 无 | Score ≥ 15 + cross_platform ≥ 2 触发落地页 |
| **验证管线** | ❌ 无 | 7 天验证：落地页 → 社区投放 → 数据判断 |
| **经验库** | ❌ 无 | tracking/lessons.json 记录失败模式 |
| **信号衰减** | 有（7 天滚动窗口） | 有（3 天降权 50%，5 天归档） |
| **反方视角** | 内置在 Why Now 中（Antithesis/Risk） | 独立 Counter-view + 反方观点制度化 |
| **文章体系** | ❌ 无 | 5 类轮换（机会深挖 40%、反直觉 25% 等） |
| **SEO/分发** | ❌ 无 | sitemap.xml + RSS + OG 图片 + hreflang |
| **双语** | en ↔ zh 完全镜像 | zh 主站 + en 翻译版 |

### 产品哲学差异

| 维度 | BuilderPulse | AimFast.Dev |
|------|-------------|---------------|
| **核心隐喻** | "狙击手，不是扫射者" | "狙击手，不是扫射者"（同源） |
| **从信号到行动** | 提供方向，Builder 自己行动 | 提供方向 + 2h MVP 方案 + 定价 + 验证路径 |
| **定价定位** | 推荐固定 $19/$29 one-shot | 推荐 $19-$49/月 订阅 |
| **目标读者** | 全球独立开发者 | 中国独立开发者 + 全球 Builder |
| **差异化壁垒** | 内容质量 + 多源交叉验证 | 中国信号 + 落地页验证 + 经验闭环 |

### 内容风格差异

| 维度 | BuilderPulse | AimFast.Dev |
|------|-------------|---------------|
| **文章长度** | 每条 ~800-1500 字（英文为主） | 日报 1500-3000 字 + 文章 2000-4000 字 |
| **叙事风格** | 直接、精炼、英文 blog 风格 | 结构化的 5 层日报 + 白话翻译 + 角色映射 |
| **行动粒度** | 给方向，具体执行留给 Builder | 给方向 + 2h 交付物 + 定价锚点 + 验证步骤 |
| **数据密度** | 高（每条引用具体讨论量） | 高（E-P-A 评分 + 信号衰减 + 跨平台验证） |
| **风险偏好** | 中等，有 Antithesis 但偏乐观 | 中等偏低，每个推荐必配 Counter-view |
"""


def generate_summary(compared_dates: list[str]) -> str:
    """生成累计方法论差异总结"""
    lines = [
        "# KAKAOPC vs BuilderPulse — 方法论差异报告",
        f"\n> 最后更新: {date.today().isoformat()}",
        f"> 已对比天数: {len(compared_dates)} 天",
        f"> 覆盖范围: {compared_dates[0]} ~ {compared_dates[-1]}" if compared_dates else "",
        "\n---\n",
        METHODOLOGY_DIFFS,
        "\n---\n",
        "## 逐日 Build Idea 对比\n",
    ]

    if compared_dates:
        lines.append("| 日期 | BuilderPulse | KAKAOPC | 一致性 |")
        lines.append("|------|-------------|---------|--------|")
        for ds in compared_dates:
            cmp_path = COMPARE_DIR / f"{ds}.md"
            if cmp_path.exists():
                content = cmp_path.read_text(encoding="utf-8")
                # 提取 Build Idea 对比结果
                bp_idea = ""
                kp_idea = ""
                alignment = "—"
                m_bp = re.search(r'BuilderPulse:\s*_(.+?)_', content)
                m_kp = re.search(r'KAKAOPC:\s*_(.+?)_', content)
                if m_bp:
                    bp_idea = m_bp.group(1)[:60]
                if m_kp:
                    kp_idea = m_kp.group(1)[:60]
                if "🟢" in content[:500]:
                    alignment = "🟢 一致"
                elif "🟡" in content[:500]:
                    alignment = "🟡 部分"
                elif "🔴" in content[:500]:
                    alignment = "🔴 不同"
                lines.append(f"| {ds} | {bp_idea} | {kp_idea} | {alignment} |")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# 主流程
# ══════════════════════════════════════════════════════════════

def compare_single_date(date_str: str) -> str:
    """对比单日，返回 Markdown 报告"""
    bp_zh = fetch_url(f"{BP_RAW_BASE}/zh/{date_str[:4]}/{date_str}.md")
    bp_en = fetch_url(f"{BP_RAW_BASE}/en/{date_str[:4]}/{date_str}.md")

    if not bp_zh and not bp_en:
        report = f"""# BuilderPulse vs KAKAOPC 对比 — {date_str}

## ⚠️ BuilderPulse 当日无内容

BuilderPulse 在 {date_str} 没有发布日报（可能周末休息或未更新）。

### KAKAOPC 当日动态

"""
        kp = extract_kp_sections(date_str)
        if kp["build_idea"]:
            report += f"- **核心信号**: {kp['build_idea'][:200]}\n"
        if kp["top_signals"]:
            report += f"- **Top 信号数**: {len(kp['top_signals'])} 个\n"
            for ts in kp["top_signals"][:3]:
                report += f"  - {ts['title'][:80]} (得分: {ts['score']}, 跨平台: {ts['cross_platform']})\n"
        if kp["total_raw_signals"]:
            report += f"- **原始信号总量**: {kp['total_raw_signals']}\n"
        report += f"\n> 💡 BuilderPulse 周末和节假日通常不更新，KAKAOPC 保持每日运行。这是两个项目的内容节奏差异。\n"
        return report

    # 使用中文版为主，英文版为补充
    bp_md = bp_zh or bp_en
    bp = extract_bp_sections(bp_md)
    kp = extract_kp_sections(date_str)

    # 生成报告
    report = f"""# BuilderPulse vs KAKAOPC 对比 — {date_str}

> 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')} CST

---

## 🎯 Build Idea 对比

{compare_build_ideas(bp, kp)}

---

## ⏰ Why Now（时机判断）

### BuilderPulse
{bp.get('why_now', '未提取到')[:600]}

### KAKAOPC
{kp.get('why_now', '未提取到（KAKAOPC 日报格式不同，见 report.md 的 Plain-English Brief 段落）')[:600]}

---

## 📡 信号来源对比

{compare_platforms(bp, kp)}

---

## 📊 讨论量与信号规模

{compare_discussion_volume(bp, kp)}

---

## 💰 定价模型

{compare_pricing(bp, kp)}

---

## 🛡️ 风险/反方视角

### BuilderPulse
{bp.get('risk_view', '未提取到独立风险段落（可能内嵌在 Why Now 中）')[:400]}

### KAKAOPC
{kp.get('risk_view', '未提取到 Counter-view（见 report.md）')[:400]}

---

## 🔗 BuilderPulse 关键链接

"""
    for link in bp.get("sourced_links", [])[:15]:
        report += f"- [{link['text'][:60]}]({link['url']})\n"

    report += f"""
---

## 📋 KAKAOPC Top 5 信号

| 排名 | 信号 | 来源 | 得分 | 跨平台 | 讨论量 |
|------|------|------|------|--------|--------|
"""
    for i, ts in enumerate(kp.get("top_signals", []), 1):
        report += f"| {i} | {ts['title'][:60]} | {ts['source']} | {ts['score']} | {ts['cross_platform']} | {ts['discussion_count']} |\n"

    if not kp.get("top_signals"):
        report += "| — | 当日无信号数据 | — | — | — | — |\n"

    report += f"""
---

## 🔍 关键差异分析

### 方向一致性
"""
    bp_idea = bp.get("build_idea", "")
    kp_idea = kp.get("build_idea", "")
    if bp_idea and kp_idea:
        report += f"- BuilderPulse 和 KAKAOPC 对当日最强信号的判断**{'一致' if '🟢' in compare_build_ideas(bp, kp) else '存在差异'}**\n"
    else:
        report += "- 无法比较（一方数据缺失）\n"

    bp_plats = set(bp.get("mentioned_platforms", []))
    kp_plats = set(kp.get("mentioned_platforms", []))
    kp_only = kp_plats - bp_plats

    report += f"- 信号源覆盖: BuilderPulse **{len(bp_plats)}** 平台, KAKAOPC **{len(kp_plats)}** 平台\n"
    if kp_only:
        report += f"- KAKAOPC 独有的中国信号源: {', '.join(sorted(kp_only))}\n"

    report += f"""
---

*本报告由 `scripts/compare_with_builderpulse.py` 自动生成*
"""
    return report


def main():
    parser = argparse.ArgumentParser(description="与 BuilderPulse 方法论文本对比")
    parser.add_argument("--date", help="指定日期 YYYY-MM-DD（默认今天）")
    parser.add_argument("--from", dest="from_date", help="起始日期 YYYY-MM-DD")
    parser.add_argument("--to", dest="to_date", help="结束日期 YYYY-MM-DD（默认今天）")
    parser.add_argument("--summary-only", action="store_true", help="仅更新 SUMMARY.md，不生成单日报告")
    args = parser.parse_args()

    # 确定日期范围
    today = date.today().isoformat()

    if args.date:
        dates = [args.date]
    elif args.from_date:
        start = args.from_date
        end = args.to_date or today
        dates = []
        d = datetime.strptime(start, "%Y-%m-%d")
        end_d = datetime.strptime(end, "%Y-%m-%d")
        while d <= end_d:
            dates.append(d.strftime("%Y-%m-%d"))
            d += timedelta(days=1)
    else:
        dates = [today]

    print(f"[对比] 对比日期范围: {dates[0]} ~ {dates[-1]} ({len(dates)} 天)")

    # 生成单日报告
    generated = []
    bp_missing = []
    for ds in dates:
        out_path = COMPARE_DIR / f"{ds}.md"

        # 检查是否已存在且是今天的（今天允许覆盖）
        is_today = ds == today
        if out_path.exists() and not is_today:
            print(f"  ⏭️  {ds} — 已存在，跳过")
            generated.append(ds)
            continue

        print(f"  [生成] {ds} — 生成对比报告...")
        report = compare_single_date(ds)
        out_path.write_text(report, encoding="utf-8")
        print(f"     → {out_path}")

        if "当日无内容" in report[:100]:
            bp_missing.append(ds)
        generated.append(ds)

    # 生成/更新总结
    all_existing = sorted([f.stem for f in COMPARE_DIR.glob("*.md") if f.stem != "SUMMARY"])
    summary = generate_summary(all_existing)
    (COMPARE_DIR / "SUMMARY.md").write_text(summary, encoding="utf-8")
    print(f"\n[总结] 总结已更新: {COMPARE_DIR / 'SUMMARY.md'}")

    # 输出统计
    print(f"\n{'='*50}")
    print(f"[OK] 共对比 {len(generated)} 天")
    if bp_missing:
        print(f"⚠️  BuilderPulse 缺失 {len(bp_missing)} 天: {', '.join(bp_missing)}")
    print(f"📂 报告目录: {COMPARE_DIR}")


if __name__ == "__main__":
    main()
