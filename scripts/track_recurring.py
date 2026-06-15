"""
重复信号追踪引擎
扫描所有 daily/*/signals.json，检测跨日期反复出现的信号话题。
输出: tracking/recurring_signals.json
"""
import json
import re
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAILY_DIR = ROOT / "daily"
TRACKING_DIR = ROOT / "tracking"

TZ_SHANGHAI = timezone(timedelta(hours=8))


def _title_similarity(a: str, b: str) -> float:
    """计算两个标题的相似度（0-1），与 process_signals.py 保持一致。"""
    a_clean = re.sub(r"[^\w\s]", "", a.lower()).strip()
    b_clean = re.sub(r"[^\w\s]", "", b.lower()).strip()
    if not a_clean or not b_clean:
        return 0.0
    return SequenceMatcher(None, a_clean, b_clean).ratio()


def _load_all_signals() -> list[dict]:
    """加载所有日期的信号，附带日期信息。"""
    all_signals: list[dict] = []
    if not DAILY_DIR.exists():
        return all_signals

    for date_dir in sorted(DAILY_DIR.iterdir()):
        if not date_dir.is_dir():
            continue
        date_str = date_dir.name
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            continue

        signals_path = date_dir / "signals.json"
        if not signals_path.exists():
            continue

        try:
            data = json.loads(signals_path.read_text(encoding="utf-8"))
            for s in data.get("signals", []):
                s["_date"] = date_str
                all_signals.append(s)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[重复追踪] 读取 {date_str}/signals.json 失败: {e}")

    print(f"[重复追踪] 共加载 {len(all_signals)} 条信号（{len(set(s.get('_date', '') for s in all_signals))} 天）")
    return all_signals


def _load_opportunities() -> dict[str, dict]:
    """加载机会追踪表，建立 title → opportunity 的映射。"""
    opp_map: dict[str, dict] = {}
    opp_path = TRACKING_DIR / "opportunities.json"
    if not opp_path.exists():
        return opp_map

    try:
        data = json.loads(opp_path.read_text(encoding="utf-8"))
        for op in data.get("opportunities", []):
            opp_name = op.get("opportunity", "").strip().lower()
            if opp_name:
                opp_map[opp_name] = op
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[重复追踪] 读取 opportunities.json 失败: {e}")

    return opp_map


def _find_linked_opportunity(topic: str, opp_map: dict[str, dict], related_ids: list[str]) -> dict | None:
    """查找与话题关联的机会。"""
    # 1. 直接按话题名匹配
    topic_lower = topic.strip().lower()
    if topic_lower in opp_map:
        return opp_map[topic_lower]

    # 2. 模糊匹配（标题相似度 > 0.65）
    for opp_name, op in opp_map.items():
        if _title_similarity(topic, opp_name) >= 0.65:
            return op

    # 3. 按 signal ID 匹配（机会的 signal_id 字段）
    for op in opp_map.values():
        op_signal_id = op.get("signal_id", "")
        if op_signal_id and op_signal_id in related_ids:
            return op

    return None


def _compute_trend(first_seen: str, last_seen: str, days_with_signal: set[str]) -> str:
    """计算趋势：rising / stable / fading。"""
    today = datetime.now(TZ_SHANGHAI).date()

    # 最近 7 天内出现的天数
    recent_count = 0
    for d_str in days_with_signal:
        try:
            d = datetime.strptime(d_str, "%Y-%m-%d").date()
            if (today - d).days <= 7:
                recent_count += 1
        except ValueError:
            pass

    # 前 7-14 天出现的天数（对比基线）
    earlier_count = 0
    for d_str in days_with_signal:
        try:
            d = datetime.strptime(d_str, "%Y-%m-%d").date()
            if 7 < (today - d).days <= 14:
                earlier_count += 1
        except ValueError:
            pass

    if recent_count > earlier_count:
        return "rising"
    elif recent_count == 0 and earlier_count > 0:
        return "fading"
    else:
        return "stable"


def run(date_str: str | None = None) -> list[dict]:
    """执行重复信号追踪。"""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    print(f"\n{'='*50}")
    print(f"[重复追踪] 跨日期重复信号检测 — {date}")
    print(f"{'='*50}")

    all_signals = _load_all_signals()
    if not all_signals:
        print("[重复追踪] 无信号数据，跳过")
        return []

    opp_map = _load_opportunities()

    # ─── 使用连通分量算法分组 ───
    # 如果两条信号标题相似度 >= 0.75，归为同一话题
    n = len(all_signals)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    # 跨日期标题相似度匹配
    threshold = 0.75
    match_count = 0
    for i in range(n):
        for j in range(i + 1, n):
            # 同一天内的重复信号已经被 process_signals 的 dedup/cluster 处理过
            # 这里只关注跨日期的重复
            if all_signals[i]["_date"] == all_signals[j]["_date"]:
                continue
            sim = _title_similarity(
                all_signals[i].get("title", ""),
                all_signals[j].get("title", "")
            )
            if sim >= threshold:
                union(i, j)
                match_count += 1

    print(f"[重复追踪] 跨日期标题匹配: {match_count} 对（阈值 {threshold}）")

    # ─── 聚合分组 ───
    groups: dict[int, list[int]] = {}
    for i in range(n):
        root = find(i)
        groups.setdefault(root, []).append(i)

    # ─── 过滤：只保留出现在 >= 2 天的组 ───
    recurring: list[dict] = []
    counter = 0

    for root, indices in groups.items():
        group_signals = [all_signals[i] for i in indices]
        dates = set(s.get("_date", "") for s in group_signals)

        # 至少出现在 2 个不同日期
        if len(dates) < 2:
            continue

        counter += 1

        # 选互动量最高的为代表信号
        best = max(group_signals, key=lambda s: s.get("engagement", {}).get("total", 0))

        # 收集所有来源
        sources = list(dict.fromkeys(
            s.get("source", "") for s in group_signals if s.get("source")
        ))

        # 收集所有 signal ID
        related_ids = [s.get("id", "") for s in group_signals if s.get("id")]

        # 计算最高分
        peak_score = max(s.get("score", 0) for s in group_signals)

        # 日期排序
        sorted_dates = sorted(dates)
        first_seen = sorted_dates[0]
        last_seen = sorted_dates[-1]

        # 趋势
        trend = _compute_trend(first_seen, last_seen, dates)

        # 关联机会
        linked_opp = _find_linked_opportunity(
            best.get("title", ""), opp_map, related_ids
        )

        rec_id = f"REC-{counter:03d}"

        recurring.append({
            "id": rec_id,
            "topic": best.get("title", ""),
            "first_seen": first_seen,
            "last_seen": last_seen,
            "appearances": len(group_signals),
            "distinct_days": len(dates),
            "sources": sources,
            "peak_score": peak_score,
            "trend": trend,
            "linked_opportunity_id": linked_opp.get("id", "") if linked_opp else "",
            "related_signal_ids": related_ids,
            "last_updated": date,
        })

    # ─── 排序：按出现天数降序，同天数按最高分降序 ───
    recurring.sort(key=lambda r: (r["distinct_days"], r["peak_score"]), reverse=True)

    # 重新编号
    for i, r in enumerate(recurring):
        r["id"] = f"REC-{i+1:03d}"

    # ─── 保存 ───
    output_data = {
        "_schema": "重复信号追踪表 — 跨日期反复出现的信号话题",
        "_version": "1.0",
        "_fields": {
            "id": "唯一追踪 ID，格式：REC-XXX",
            "topic": "话题名称（代表信号的标题）",
            "first_seen": "首次出现日期",
            "last_seen": "最近出现日期",
            "appearances": "总出现次数（跨所有日期）",
            "distinct_days": "出现天数（去重日期数）",
            "sources": "来源平台列表",
            "peak_score": "最高单日得分",
            "trend": "趋势：rising（近7天增加）/ stable（持平）/ fading（近7天无新出现）",
            "linked_opportunity_id": "关联的机会追踪 ID（可为空）",
            "related_signal_ids": "所有相关信号的 ID 列表",
            "last_updated": "最后更新日期",
        },
        "recurring": recurring,
    }

    output_path = TRACKING_DIR / "recurring_signals.json"
    output_path.write_text(
        json.dumps(output_data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"[重复追踪] 发现 {len(recurring)} 个重复话题")
    for r in recurring[:10]:
        trend_icon = {"rising": "RISING", "stable": "STABLE", "fading": "FADING"}.get(r["trend"], "?")
        print(f"  {r['id']} [{trend_icon}] [{r['distinct_days']}天/{r['appearances']}次] {r['topic'][:60]}")
        print(f"       {r['first_seen']} -> {r['last_seen']} | 最高 {r['peak_score']}分 | 来源: {', '.join(r['sources'][:3])}")

    print(f"\n[重复追踪] 结果已保存 → {output_path}")
    return recurring


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    run(today)
