"""
信号处理引擎
负责: 加载 → 去重 → 聚类 → 跨域检测 → E-P-A 打分 → 衰减 → 排序
输入: ./raw/YYYY-MM-DD/*.json
输出: ./daily/YYYY-MM-DD/signals.json
"""
import json
import re
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"
DAILY_DIR = ROOT / "daily"
CONFIG_PATH = ROOT / "config.json"

TZ_SHANGHAI = timezone(timedelta(hours=8))

# 停用词（聚类时忽略）
STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "in", "on", "at", "to", "for", "of", "with", "by", "from",
    "and", "or", "but", "not", "this", "that", "it", "its",
    "i", "you", "he", "she", "we", "they", "my", "your",
    "has", "have", "had", "do", "does", "did", "will", "would",
    "can", "could", "should", "may", "might", "about", "just",
    "how", "what", "why", "when", "where", "who", "which",
    "v2ex", "reddit", "hacker", "news", "github", "trending",
    "new", "using", "use", "make", "made", "get", "got", "one",
    "like", "now", "also", "still", "need", "way", "really",
    # v2.2: C-end 中文停用词 — 防豆瓣/小红书过聚类
    "豆瓣图书", "豆瓣电影", "豆瓣音乐", "豆瓣小组", "人评价", "人看过",
    "人想读", "人读过", "人在读", "人讨论", "笔记", "评论",
    "buyitforlife", "goodvalue", "digitalnomad", "solotravel",
    "onebag", "minimalism", "homeautomation", "homekit",
    "gadgets", "mechanicalkeyboards", "headphones", "macapps",
    "iosapps", "androidapps", "internetisbeautiful", "selfhosted",
    "personalfinance", "frugal", "subreddit",
}


def load_config() -> dict:
    """加载配置文件。"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_raw_signals(date_str: str) -> list[dict]:
    """加载当日所有原始信号。"""
    raw_path = RAW_DIR / date_str
    if not raw_path.exists():
        print(f"[处理] {raw_path} 不存在，无原始数据")
        return []

    all_signals: list[dict] = []
    for f in sorted(raw_path.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            source_signals = data.get("signals", [])
            all_signals.extend(source_signals)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[处理] 读取 {f.name} 失败: {e}")

    print(f"[处理] 加载 {len(all_signals)} 条原始信号（来自 {raw_path}）")
    return all_signals


# ─── 去重 ───────────────────────────────────────────

def _title_similarity(a: str, b: str) -> float:
    """计算两个标题的相似度（0-1）。"""
    a_clean = re.sub(r"[^\w\s]", "", a.lower()).strip()
    b_clean = re.sub(r"[^\w\s]", "", b.lower()).strip()
    if not a_clean or not b_clean:
        return 0.0
    return SequenceMatcher(None, a_clean, b_clean).ratio()


def _extract_keywords(text: str) -> set[str]:
    """从文本中提取关键词。"""
    words = re.findall(r"[a-zA-Z一-鿿]+", text.lower())
    return {w for w in words if w not in STOP_WORDS and len(w) > 1}


def deduplicate(signals: list[dict]) -> list[dict]:
    """
    去重：
    1. URL 完全相同 → 合并
    2. 标题相似度 > 0.90 → 合并，保留互动量更高的
    3. 同一 URL 出现在多个源 → 合并为一条，标注跨平台验证
    """
    if not signals:
        return []

    config = load_config()
    threshold = config.get("dedup", {}).get("title_similarity", 0.90)

    unique: list[dict] = []
    url_map: dict[str, int] = {}  # url → index in unique

    for signal in signals:
        url = signal.get("url", "")
        title = signal.get("title", "")

        # 第 1 道: URL 精确匹配
        if url and url in url_map:
            idx = url_map[url]
            existing = unique[idx]
            # 合并 sources
            existing_sources = existing.get("_raw_sources", [existing.get("source", "")])
            existing_sources.append(signal.get("source", ""))
            existing["_raw_sources"] = existing_sources
            # 保留互动量更高的
            if signal["engagement"]["total"] > existing["engagement"]["total"]:
                unique[idx] = signal
                unique[idx]["_raw_sources"] = existing_sources
            continue

        # 第 2 道: 标题相似度
        is_dup = False
        for j, existing in enumerate(unique):
            sim = _title_similarity(title, existing.get("title", ""))
            if sim >= threshold:
                # 合并来源
                existing_sources = existing.get("_raw_sources", [existing.get("source", "")])
                existing_sources.append(signal.get("source", ""))
                existing["_raw_sources"] = existing_sources
                # 标记跨平台
                existing["discussion_count"] = max(
                    existing.get("discussion_count", 0),
                    signal.get("discussion_count", 0),
                )
                is_dup = True
                break

        if not is_dup:
            signal["_raw_sources"] = [signal.get("source", "")]
            unique.append(signal)
            if url:
                url_map[url] = len(unique) - 1

    dup_count = len(signals) - len(unique)
    print(f"[去重] {len(signals)} → {len(unique)}（合并 {dup_count} 条重复）")
    return unique


# ─── 聚类 ───────────────────────────────────────────

def cluster(signals: list[dict]) -> list[dict]:
    """
    将相关信号归为同一话题。
    基于关键词重叠率（Jaccard 相似度），将高度相关的信号合并为话题组。
    每个话题组选一条代表信号，附上所有子信号的引用。
    """
    if len(signals) <= 1:
        return signals

    kw_cache: dict[int, set[str]] = {}
    for i, s in enumerate(signals):
        title = s.get("title", "")
        summary = s.get("summary", "")
        kw_cache[i] = _extract_keywords(f"{title} {summary}")

    # 简单的连通分量聚类（Jaccard > 0.25）
    parent = list(range(len(signals)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    for i in range(len(signals)):
        for j in range(i + 1, len(signals)):
            kws_i = kw_cache[i]
            kws_j = kw_cache[j]
            if not kws_i or not kws_j:
                continue
            intersection = kws_i & kws_j
            union_size = len(kws_i | kws_j)
            jaccard = len(intersection) / union_size if union_size > 0 else 0

            # 同一源的信号即使关键词重叠也不聚类（避免自聚合）
            same_source = signals[i].get("source_key") == signals[j].get("source_key")
            threshold = 0.50 if same_source else 0.25

            if jaccard >= threshold:
                union(i, j)

    # 按 group 聚合
    groups: dict[int, list[int]] = {}
    for i in range(len(signals)):
        root = find(i)
        groups.setdefault(root, []).append(i)

    clustered: list[dict] = []
    multi_platform_count = 0

    for root, indices in groups.items():
        group_signals = [signals[i] for i in indices]

        # 选互动量最高的为代表
        best = max(group_signals, key=lambda s: s["engagement"]["total"])

        # 收集所有来源平台
        all_sources = []
        for s in group_signals:
            for src in s.get("_raw_sources", [s.get("source", "")]):
                if src not in all_sources:
                    all_sources.append(src)

        best["_raw_sources"] = all_sources

        # 如果组内有多个信号且跨多个源 → 标注跨平台验证
        if len(group_signals) >= 2 and len(set(s.get("source_key", "") for s in group_signals)) >= 2:
            multi_platform_count += 1
            best["_cluster_info"] = {
                "size": len(group_signals),
                "cross_platform": True,
                "related_ids": [s.get("id", "") for s in group_signals if s.get("id") != best.get("id")],
            }

        clustered.append(best)

    print(f"[聚类] {len(signals)} → {len(clustered)} 组（{multi_platform_count} 组跨平台验证）")
    return clustered


# ─── 跨域痛点检测 ───────────────────────────────────

# 源类型 → 域分类（用于跨域检测）
SOURCE_DOMAIN_MAP = {
    # tech: 技术社区 — 开发者/工程师视角
    "github": "tech", "hn": "tech", "lobsters": "tech",
    "devcommunity": "tech", "arxiv": "tech", "huggingface": "tech",
    # consumer: 消费者社区 — 普通用户视角
    "reddit-consumer": "consumer", "douban": "consumer",
    "xiaohongshu": "consumer", "xhs": "consumer",
    "producthunt": "consumer",
    # search: 搜索趋势 — 意图数据
    "trends": "search",
    # mixed: 混合社区（可能 tech 也可能 consumer）
    "reddit": "mixed", "v2ex": "mixed", "w2solo": "mixed",
    "indiehackers": "mixed", "jike": "mixed",
}


def _classify_domain(source_key: str) -> str:
    """将 source_key 映射到域类型。"""
    return SOURCE_DOMAIN_MAP.get(source_key, "unknown")


def detect_cross_domain_patterns(signals: list[dict], top_n: int = 15) -> list[dict]:
    """
    跨域痛点模式检测（v2.2 新增）。
    当同一用户痛点出现在不同类型源（技术 + 消费者 + 搜索）时，提升信号可信度。

    流程:
      1. 选取 top_n 个信号（优先跨平台的）
      2. 用 LLM 识别跨域匹配对
      3. 跨域验证的信号 → cross_platform_count 虚拟 +1
    """
    if len(signals) <= 5:
        return signals

    # 按源多样性 + 初步热度排序选取候选信号
    # v2.2 fix: 分层选取 — 每个域各取 top N/3，确保跨域覆盖
    domain_buckets: dict[str, list] = {"tech": [], "consumer": [], "search": [], "mixed": []}
    for s in signals:
        sources = s.get("_raw_sources", [s.get("source", "")])
        unique_src = len(set(sources))
        engagement = s.get("engagement", {}).get("total", 0)
        sk = s.get("source_key", "")
        domain = _classify_domain(sk)
        if domain not in domain_buckets:
            domain = "mixed"
        domain_buckets[domain].append((unique_src, engagement, s))

    # 每个域取 top_n // 4 + 1 个（至少 1 个），然后合并
    per_domain = max(1, top_n // 4)
    top_signals = []
    for domain in ["tech", "consumer", "search", "mixed"]:
        bucket = domain_buckets.get(domain, [])
        bucket.sort(key=lambda x: (x[0], x[1]), reverse=True)
        top_signals.extend([s for _, _, s in bucket[:per_domain]])

    # 如果还不够 top_n，从剩余中补足
    if len(top_signals) < top_n:
        seen_ids = {id(s) for s in top_signals}
        all_sorted = sorted(
            [(len(set(s.get("_raw_sources", [s.get("source", "")]))),
              s.get("engagement", {}).get("total", 0), s)
             for s in signals if id(s) not in seen_ids],
            key=lambda x: (x[0], x[1]), reverse=True
        )
        top_signals.extend([s for _, _, s in all_sorted[:top_n - len(top_signals)]])

    # 按域分组统计
    domains_present = set()
    for s in top_signals:
        sk = s.get("source_key", "")
        domains_present.add(_classify_domain(sk))

    # 如果只有 1 个域，跨域检测没有意义
    if len(domains_present) < 2:
        print("[跨域] 候选信号仅覆盖 1 个域，跳过")
        return signals

    # 构建 LLM prompt
    signal_list = []
    for i, s in enumerate(top_signals):
        sk = s.get("source_key", "?")
        domain = _classify_domain(sk)
        signal_list.append({
            "id": i,
            "domain": domain,
            "source": f"{s.get('source', '?')} ({sk})",
            "title": s.get("title", ""),
            "summary": (s.get("summary", "") or "")[:150],
            "tags": [t for t in s.get("tags", []) if isinstance(t, str)][:5],
        })

    system = """你是一个产品需求分析师。你的任务是：
1. 阅读一组来自不同社区的信号（技术社区、消费者社区、搜索趋势等）
2. 找出指向「同一个用户痛点或需求」的信号对（跨域匹配）
3. 只标记真正代表同一需求的匹配 —— 不要因为两个信号都提到 AI 就认为它们匹配

判断标准：
- 两个信号是否在解决同一个具体问题？（如 "PDF 编辑太贵" vs "寻找 Adobe 替代品"）
- 两个信号是否面向同一类用户？（如 开发者工具 ≠ 普通消费者工具）
- 两个信号来自不同类型的源吗？（只标记跨域匹配，同域忽略）

返回纯 JSON 格式，不要 markdown 代码块，不要额外文字：
{"matches": [{"a": 0, "b": 3, "shared_pain": "一句话描述共同痛点"}, ...], "note": "简要分析"}
如果没有跨域匹配，返回 {"matches": [], "note": "无"}"""

    user = f"候选信号列表（{len(top_signals)} 个）：\n\n"
    for s in signal_list:
        tags_str = ", ".join(s["tags"])
        user += (
            f"[{s['id']}] domain={s['domain']} | source={s['source']}\n"
            f"   title: {s['title']}\n"
            f"   summary: {s['summary'][:120]}\n"
            f"   tags: {tags_str}\n\n"
        )

    # 调用 LLM
    try:
        from scripts.llm_client import chat

        raw = chat(
            system_prompt=system,
            user_prompt=user,
            temperature=0.3,
            max_tokens=1024,
        )

        # 解析响应 —— 防御性提取 JSON
        raw = raw.strip()
        # 移除可能的 markdown 代码块标记
        if raw.startswith("```"):
            raw = re.sub(r"^```\w*\n?", "", raw)
            raw = re.sub(r"\n```$", "", raw)
        result = json.loads(raw)
        matches = result.get("matches", [])
        note = result.get("note", "")

    except Exception as e:
        print(f"[跨域] LLM 调用/解析失败: {e}，跳过跨域检测")
        # 写入 pipeline_status 以便 dashboard 显示告警
        try:
            from scripts.pipeline_status import write as write_pipeline_status
            write_pipeline_status(
                datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d"),
                "cross_domain",
                "error",
                reason="llm_or_parse_failure",
                message=f"Cross-domain LLM call/parse failed: {str(e)[:200]}"
            )
        except Exception:
            pass
        return signals

    if not matches:
        print(f"[跨域] 未检测到跨域匹配 ({note})")
        return signals

    # 标记跨域验证的信号
    validated_ids = set()
    for m in matches:
        a_idx = m.get("a")
        b_idx = m.get("b")
        shared = m.get("shared_pain", "")
        if a_idx is not None and b_idx is not None:
            # 查找原始信号
            sig_a = top_signals[a_idx] if a_idx < len(top_signals) else None
            sig_b = top_signals[b_idx] if b_idx < len(top_signals) else None
            if sig_a and sig_b:
                domain_a = _classify_domain(sig_a.get("source_key", ""))
                domain_b = _classify_domain(sig_b.get("source_key", ""))
                # 只标记真正跨域的（不同域类型）
                if domain_a != domain_b:
                    sig_a["_cross_domain_validated"] = True
                    sig_a["_cross_domain_pair"] = {
                        "with_title": sig_b.get("title", "")[:60],
                        "shared_pain": shared,
                        "domains": f"{domain_a} × {domain_b}",
                    }
                    sig_b["_cross_domain_validated"] = True
                    sig_b["_cross_domain_pair"] = {
                        "with_title": sig_a.get("title", "")[:60],
                        "shared_pain": shared,
                        "domains": f"{domain_a} × {domain_b}",
                    }
                    validated_ids.add(a_idx)
                    validated_ids.add(b_idx)

    if validated_ids:
        # 对跨域验证的信号，virtually 增加 cross_platform_count
        for s in signals:
            if s.get("_cross_domain_validated"):
                s["cross_platform_count"] = s.get("cross_platform_count", 1) + 1
                s["_cross_domain_boost"] = True

        print(f"[跨域] 发现 {len(validated_ids)} 个跨域验证信号 ({len(matches)} 对匹配)")
        for m in matches[:5]:
            print(f"  [{m.get('a')}]×[{m.get('b')}]: {m.get('shared_pain', '')[:80]}")
    else:
        print(f"[跨域] 所有匹配均为同域，无有效跨域信号")

    return signals


# ─── E-P-A 打分 ─────────────────────────────────────

def score_epa(signals: list[dict]) -> list[dict]:
    """
    E-P-A 打分。
    Score = cross_platform×3 + volume×2 + freshness×2 + actionability×2 + buyer_clarity×1 + consumer_appeal×2 + problem_clarity×2

    cross_platform: 统计 _raw_sources 中不同平台
    volume: 讨论量 vs 阈值表
    freshness: 基于 collected_at 判断
    actionability: 基于关键词规则
    buyer_clarity: 基于关键词规则
    consumer_appeal: C 端消费者吸引力
    problem_clarity: 区分真痛点 vs 伪热度（v2.2 新增）
    """
    config = load_config()
    weights = config["scoring"]["weights"]
    rubrics = config["scoring"]["rubrics"]
    today = datetime.now(TZ_SHANGHAI).date()

    for s in signals:
        # 1. cross_platform
        sources = s.get("_raw_sources", [s.get("source", "")])
        unique_sources = len(set(sources))
        if unique_sources >= 3:
            cp_score = rubrics["cross_platform"]["3_plus_platforms"]
        elif unique_sources >= 2:
            cp_score = rubrics["cross_platform"]["2_platforms"]
        else:
            cp_score = rubrics["cross_platform"]["1_platform"]

        # 2. volume
        discussion = s.get("discussion_count", 0)
        engagement_total = s.get("engagement", {}).get("total", discussion)
        volume = discussion + engagement_total // 2  # 综合 discussion 和 engagement
        if volume >= 500:
            v_score = rubrics["volume"]["gt_500"]
        elif volume >= 200:
            v_score = rubrics["volume"]["200_500"]
        elif volume >= 50:
            v_score = rubrics["volume"]["50_200"]
        else:
            v_score = rubrics["volume"]["lt_50"]

        # 3. freshness
        collected = s.get("collected_at", "")
        try:
            collected_date = datetime.fromisoformat(collected).date()
            days_old = (today - collected_date).days
        except (ValueError, TypeError):
            days_old = 0

        if days_old == 0:
            f_score = rubrics["freshness"]["today"]
        elif days_old == 1:
            f_score = rubrics["freshness"]["yesterday"]
        else:
            f_score = rubrics["freshness"]["3_days_plus"]

        # 4. actionability（基于文本关键词判断）
        tags = [t for t in s.get("tags", []) if isinstance(t, str)]
        text = f"{s.get('title', '')} {s.get('summary', '')} {' '.join(tags)}"
        text_lower = text.lower()

        actionable_patterns = [
            "alternative to", "open source", "free", "pricing", "revenue",
            "mrr", "替代", "免费", "开源", "产品", "发布", "launch",
            "收入", "定价", "赚钱", "副业", "创业", "工具",
            "builder", "template", "starter", "boilerplate", "saas",
            # 中文扩展 — 构建意图
            "怎么做", "求推荐", "有没有", "想做一个", "众筹",
            "接单", "外包", "教程", "课程", "付费", "会员",
            "订阅", "卖", "出海", "独立开发", "变现", "接活",
        ]
        complaint_patterns = [
            "抱怨", "为什么", "太贵", "不好用", "why is", "too expensive",
            "frustrated", "problem", "issue", "bug", "broken",
            # 中文扩展 — 抱怨信号
            "坑", "骗", "垃圾", "没人用", "倒闭", "跑路",
            "割韭菜", "难用", "找不到", "缺", "烦", "难受",
            "要是…就好了", "要是...就好了", "忍不了",
        ]

        actionable_count = sum(1 for p in actionable_patterns if p in text_lower)
        complaint_count = sum(1 for p in complaint_patterns if p in text_lower)

        if "show_hn" in s.get("signal_type", "") or "product-launch" in s.get("tags", []):
            a_score = rubrics["actionability"]["concrete_product_with_pricing"]
        elif actionable_count >= 3:
            a_score = rubrics["actionability"]["concrete_product_with_pricing"]
        elif actionable_count >= 1:
            a_score = rubrics["actionability"]["vague_direction"]
        elif complaint_count >= 2:
            # v2.2: C-end 源的投诉视为可操作信号（抱怨 = 未满足的需求）
            if s.get("source_key") in ("reddit-consumer", "douban", "xiaohongshu", "xhs"):
                a_score = rubrics["actionability"]["vague_direction"]
            else:
                a_score = 2  # 介于 vague 和 pure complaint 之间
        else:
            a_score = rubrics["actionability"]["pure_complaint"]

        # 5. buyer_clarity（基于角色关键词）
        buyer_patterns = [
            "工程经理", "cto", "vp", "manager", "founder", "创业",
            "独立开发者", "indie hacker", "freelancer", "自由职业",
            "developer", "engineer", "designer", "pm", "产品经理",
            "企业", "enterprise", "team", "small business",
            # 中文扩展 — 可识别买家角色
            "程序员", "老板", "小团队", "个人", "兼职", "远程",
            "数字游民", "学生", "宝妈", "自媒体", "博主", "运营",
            "hr", "财务", "律师", "医生", "教师", "设计师",
            "出海", "外贸", "电商",
        ]
        buyer_count = sum(1 for p in buyer_patterns if p in text_lower)

        if buyer_count >= 3:
            b_score = rubrics["buyer_clarity"]["specific_buyer"]
        elif buyer_count >= 1:
            b_score = rubrics["buyer_clarity"]["likely_buyer"]
        else:
            b_score = rubrics["buyer_clarity"]["unknown_buyer"]

        # 5.5. problem_clarity（v2.2 新增 — 区分真痛点 vs 伪热度）
        # 真痛点信号：有人正在承受痛苦、付钱解决、或明确抱怨
        pain_signal_patterns = [
            # 付费痛苦
            "paying", "for.*but", "tired of paying", "too expensive", "overpriced",
            "waste of money", "costs too much", "alternatives?",
            "cancel.*subscription", "switching from",
            # 功能痛苦
            "missing feature", "wish i could", "if only", "why doesn't",
            "still can't", "waiting for", "no way to",
            # 流程痛苦
            "spend.*hours", "takes forever", "manual.*process", "every time i",
            "frustrated", "hate it when", "pain point",
            "annoying", "drives me crazy", "drives me nuts",
            # 中文痛点
            "太贵了", "受不了", "每次都要", "找不到", "忍了很久",
            "有没有.*替代", "付费.*但是", "浪费.*时间", "坑爹",
            "求推荐", "求助", "怎么办", "有没有人",
            "后悔", "不值", "被坑", "踩坑", "避坑",
            "想换", "想找一个", "需要一个",
        ]
        # 伪热度信号：看起来酷但没人会付钱
        hype_signal_patterns = [
            "built with rust", "rewrite in", "yet another", "show hn",
            "just launched", "my first", "weekend project", "side project",
            "benchmark", "faster than", "zero dependency", "zero dependencies",
            "built with", "made with",
            "i built", "i made", "i created", "我做了", "我做了一个",
            "开源.*替代", "clone", "克隆",
        ]

        pain_count = sum(1 for p in pain_signal_patterns if p in text_lower)
        hype_count = sum(1 for p in hype_signal_patterns if p in text_lower)

        # Show HN / Product Launch 自带 "发布即宣传" 属性 → 伪热度风险 +1
        if "show hn" in text_lower[:30] or s.get("signal_type") == "show_hn":
            hype_count += 1
        # "I made" / "I built" 类个人项目 → 伪热度风险 +1
        if re.search(r"\bi (made|built|created|launched)\b", text_lower):
            hype_count += 1

        if pain_count >= 3 and hype_count == 0:
            pc_score = rubrics["problem_clarity"]["clear_pain_point"]
        elif pain_count >= 2 and pain_count > hype_count:
            pc_score = rubrics["problem_clarity"]["likely_pain"]
        elif pain_count >= 1 and hype_count == 0:
            pc_score = rubrics["problem_clarity"]["possible_pain"]
        elif pain_count >= 1 and hype_count >= 1:
            pc_score = rubrics["problem_clarity"]["mixed_signal"]
        elif pain_count == 0 and hype_count >= 2:
            pc_score = rubrics["problem_clarity"]["likely_hype"]
        else:
            pc_score = rubrics["problem_clarity"]["neutral"]

        # 6. consumer_appeal（C 端消费者吸引力 — v2.2 扩展）
        # 检测信号是否面向普通消费者（而非纯开发者工具）
        c_end_patterns = [
            # 消费场景关键词
            "game", "gaming", "golf", "puzzle", "游戏", "娱乐", "play",
            "pdf", "document", "文档", "scan", "扫描",
            "audio", "music", "podcast", "音乐", "播客", "有声", "tts", "text-to-speech",
            "video", "视频", "movie", "film",
            "photo", "image", "图片", "照片", "camera",
            "health", "fitness", "wellness", "健康", "运动", "sleep", "睡眠",
            "food", "recipe", "cooking", "美食", "菜", "做饭",
            "travel", "旅行", "trip", "flight",
            "home", "garden", "lawn", "家居", "花园", "植物", "grass",
            "pet", "dog", "cat", "宠物", "猫", "狗",
            "fashion", "clothing", "时尚", "衣服",
            "book", "reading", "阅读", "书",
            "writing", "写作", "日记", "journal",
            "kids", "children", "儿童", "小孩", "教育",
            "shopping", "deal", "购物", "优惠",
            "car", "vehicle", "auto", "driving",
            "finance", "budget", "理财", "省钱", "saving money",
            # 桌面/移动 App
            "mac app", "macos", "mac menu bar", "menu bar app",
            "iphone", "ipad", "ios app", "android app",
            "chrome extension", "浏览器插件", "chrome 插件", "browser extension",
            "desktop app", "桌面应用", "桌面工具", "electron app",
            # 生活方式 / 非技术场景
            "lifestyle", "生活", "日常",
            "productivity", "效率", "番茄", "pomodoro",
            "break reminder", "休息提醒", "休息",
            "logitech", "razer", "keychron", "外设", "鼠标", "键盘", "硬件", "peripheral",
            "drone", "iot", "smart home", "智能家居",
            # 消费者服务
            "subscription", "订阅", "membership",
            "marketplace", "freelance", "兼职", "副业",
            "no ai", "without ai", "pure", "不依赖 ai",
            # 讽刺/娱乐/内容
            "satire", "parody", "讽刺", "恶搞", "搞笑", "fun", "daily",
            # v2.2: C-end 扩展 — 家居/日用品/耐用消费品
            "mattress", "床垫", "sofa", "沙发", "furniture", "家具",
            "appliance", "家电", "冰箱", "洗衣机", "空调", "吸尘器",
            "grocery", "杂货", "超市", "sale price", "打折",
            "boots", "shoes", "鞋", "jacket", "coat", "外套",
            "bag", "backpack", "背包", "luggage", "行李箱",
            "kitchen", "厨房", "cookware", "锅", "刀",
            "skincare", "护肤", "makeup", "化妆", "sunscreen", "防晒",
            "hair", "头发", "shampoo", "洗发",
            # v2.2: 耐用消费品/工具
            "bifl", "buy it for life", "durable", "耐用", "warranty", "保修",
            "repair", "维修", "fix", "diy", "自己动手",
            "tool", "工具", "drill", "电钻",
            # v2.2: 抱怨/求助信号（C-end 强信号：有人正在痛苦）
            "help", "求助", "recommend", "推荐", "suggestion", "建议",
            "anyone else", "有人", "does anyone", "谁用过",
            "worth it", "值不值", "划算", "性价比",
            "regret", "后悔", "disappointed", "失望",
            " PSA ", "warning", "提醒", "avoid", "避坑", "别买",
            "review", "评测", "测评", "体验",
        ]
        c_end_count = sum(1 for p in c_end_patterns if p in text_lower)

        # 信号源加权：Product Hunt + HN Show HN 通常有 C 端受众
        source_bonus = 0
        if s.get("source_key") in ("producthunt",):
            source_bonus += 1
        if "show_hn" in s.get("signal_type", ""):
            source_bonus += 1
        # Reddit 非编程子版块
        if s.get("source_key") in ("reddit", "reddit-consumer"):
            source_bonus += 1
        # C-end 专属源（豆瓣、小红书）
        if s.get("source_key") in ("douban", "xiaohongshu", "xhs"):
            source_bonus += 2

        c_end_total = c_end_count + source_bonus

        if c_end_total >= 3:
            c_score = rubrics["consumer_appeal"]["strong_c_end"]
        elif c_end_total >= 2:
            c_score = rubrics["consumer_appeal"]["mixed_audience"]
        else:
            c_score = rubrics["consumer_appeal"]["developer_only"]

        # 计算总分
        c_weight = weights.get("consumer_appeal", 2)  # 向前兼容旧 config
        pc_weight = weights.get("problem_clarity", 2)  # v2.2 新增
        score = (
            cp_score * weights["cross_platform"]
            + v_score * weights["volume"]
            + f_score * weights["freshness"]
            + a_score * weights["actionability"]
            + b_score * weights["buyer_clarity"]
            + c_score * c_weight
            + pc_score * pc_weight
        )

        s["cross_platform_count"] = unique_sources
        s["score"] = score
        s["c_end_flag"] = c_end_total >= 3  # 标记为强 C 端信号（v2.1: 阈值从4降至3以适配开发者向信号源）
        s["c_end_score"] = c_end_total
        s["problem_clarity"] = pc_score  # v2.2 新增
        s["score_breakdown"] = {
            "cross_platform": {"raw": unique_sources, "score": cp_score, "weighted": cp_score * weights["cross_platform"]},
            "volume": {"raw": volume, "score": v_score, "weighted": v_score * weights["volume"]},
            "freshness": {"raw": days_old, "score": f_score, "weighted": f_score * weights["freshness"]},
            "actionability": {"raw": f"keywords:{actionable_count}", "score": a_score, "weighted": a_score * weights["actionability"]},
            "buyer_clarity": {"raw": f"buyer_keywords:{buyer_count}", "score": b_score, "weighted": b_score * weights["buyer_clarity"]},
            "consumer_appeal": {"raw": f"c_end_keywords:{c_end_total}", "score": c_score, "weighted": c_score * c_weight},
            "problem_clarity": {"raw": f"pain:{pain_count}/hype:{hype_count}", "score": pc_score, "weighted": pc_score * pc_weight},
        }

    # 最高分和平均分
    scores = [s["score"] for s in signals]
    if scores:
        print(f"[打分] 最高: {max(scores)} 分 | 平均: {sum(scores)/len(scores):.1f} 分")
        action_threshold = config["scoring"]["thresholds"]["action_trigger"]
        min_platforms = config["scoring"]["thresholds"]["cross_platform_min"]
        qualified = [s for s in signals if s["score"] >= action_threshold and s["cross_platform_count"] >= min_platforms]
        print(f"[打分] 触发 Action 方案: {len(qualified)} 个")

    return signals


# ─── 衰减 ───────────────────────────────────────────

def apply_decay(signals: list[dict], date_str: str) -> list[dict]:
    """
    信号衰减：连续出现的同一话题降权。
    对比前 2-4 天处理后的信号，如果同一话题连续出现：
    - 连续 3 天 → score × 0.5
    - 连续 5 天 → 标记 cooling=true
    """
    today = datetime.strptime(date_str, "%Y-%m-%d")
    config = load_config()
    decay_factor = config["decay"]["3_days_same_topic"]

    # 加载前 4 天的处理结果
    previous_titles: list[str] = []
    for i in range(1, 5):
        prev_date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        prev_path = DAILY_DIR / prev_date / "signals.json"
        if prev_path.exists():
            try:
                prev_data = json.loads(prev_path.read_text(encoding="utf-8"))
                for ps in prev_data.get("signals", []):
                    previous_titles.append(ps.get("title", ""))
            except (json.JSONDecodeError, KeyError):
                pass

    decay_count = 0
    cooling_count = 0

    for s in signals:
        title = s.get("title", "")
        # 统计最近 4 天中标题相似的出现天数
        streak = 1  # 今天
        for prev_title in previous_titles:
            if _title_similarity(title, prev_title) >= 0.75:
                streak += 1

        if streak >= 5:
            s["cooling"] = True
            s["score"] = int(s["score"] * 0.3)
            cooling_count += 1
        elif streak >= 3:
            s["score"] = int(s["score"] * decay_factor)
            s["decayed"] = True
            decay_count += 1

    print(f"[衰减] 降权: {decay_count} 条 | 冷却: {cooling_count} 条")
    return signals


# ─── 主流程 ─────────────────────────────────────────

def run(date_str: str | None = None) -> list[dict]:
    """执行完整信号处理 pipeline。"""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    config = load_config()

    print(f"\n{'='*60}")
    print(f"[处理] KAKAOPC 信号处理引擎 — {date}")
    print(f"{'='*60}")

    # Step 1: 加载
    signals = load_raw_signals(date)
    if not signals:
        print("[处理] 无信号，跳过")
        return []

    # Step 2: 去重
    signals = deduplicate(signals)

    # Step 3: 聚类
    signals = cluster(signals)

    # Step 3.5: 跨域痛点检测（v2.2 新增）
    signals = detect_cross_domain_patterns(signals)

    # Step 4: E-P-A 打分
    signals = score_epa(signals)

    # Step 5: 衰减
    signals = apply_decay(signals, date)

    # Step 6: 排序
    signals.sort(key=lambda s: s.get("score", 0), reverse=True)

    # Step 7: 清理内部字段（不输出 _ 前缀字段到文件）+ 净化 tags
    for s in signals:
        s.pop("_raw_sources", None)
        # 跨域检测 → 公开字段
        if s.pop("_cross_domain_validated", False):
            s["cross_domain_validated"] = True
            s["cross_domain_pair"] = s.pop("_cross_domain_pair", None)
        else:
            s.pop("_cross_domain_pair", None)
            s["cross_domain_validated"] = False
        s.pop("_cross_domain_boost", None)
        # 过滤 tags 中的 None / 非字符串值，防御下游 join() 崩溃
        raw_tags = s.get("tags", [])
        if raw_tags:
            s["tags"] = [t for t in raw_tags if isinstance(t, str) and t]

    # 保存
    output_dir = DAILY_DIR / date
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "signals.json"

    output_data = {
        "processed_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "date": date,
        "config": {
            "scoring_formula": config["scoring"]["formula"],
            "action_threshold": config["scoring"]["thresholds"]["action_trigger"],
        },
        "total_raw": len(signals),
        "signals": signals,
        "summary": {
            "top_score": max(s.get("score", 0) for s in signals) if signals else 0,
            "avg_score": round(sum(s.get("score", 0) for s in signals) / len(signals), 1) if signals else 0,
            "action_qualified": len([s for s in signals if s.get("score", 0) >= config["scoring"]["thresholds"]["action_trigger"]]),
            "cross_platform_signals": len([s for s in signals if s.get("cross_platform_count", 0) >= 2]),
        },
    }

    output_path.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[处理] 结果已保存 → {output_path}")

    # 打印 Top 10
    action_threshold = config["scoring"]["thresholds"]["action_trigger"]
    print(f"\n{'─'*60}")
    print(f"Top 10 信号（阈值: {action_threshold} 分）:")
    print(f"{'─'*60}")
    for i, s in enumerate(signals[:10], 1):
        flag = ">>>" if s["score"] >= action_threshold else "   "
        print(f"  {i:2d}. [{s['score']:3d}分] {flag} {s.get('title', 'N/A')[:65]}")
        print(f"      来源: {s.get('source', '?')} | 跨平台: {s.get('cross_platform_count', 0)} | 互动: {s.get('discussion_count', 0)}")

    return signals


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    run(today)
