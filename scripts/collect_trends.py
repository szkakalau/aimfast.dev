"""
Google Trends 信号采集
数据源: pytrends（非官方 Google Trends API）
采集内容: 搜索词暴涨/降温 + 相关查询

注意: pytrends 有时会被 Google 限流，需要重试机制。
"""
import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"

TZ_SHANGHAI = timezone(timedelta(hours=8))

# 预设关注关键词（开发者工具 + SaaS 方向）
TRACKED_KEYWORDS = [
    # 2026 AI 工具链热词
    "Claude Code",
    "agent memory",
    "MCP server",
    "AI observability",
    "token cost optimizer",
    "AI governance",
    "multi-agent workflow",
    "agent skills",
    # 开发者工具
    "micro SaaS",
    "open source AI",
    "AI code assistant",
    "vibe coding",
    # 基础设施
    "agent infrastructure",
    "LLM gateway",
    "AI evaluation",
]


def _safe_import_pytrends():
    """安全导入 pytrends，包含 urllib3 2.x 兼容性补丁。"""
    try:
        # 修复 pytrends 与 urllib3 2.x 的兼容性问题
        # urllib3 2.x 将 method_whitelist 重命名为 allowed_methods
        _patch_urllib3_retry()

        from pytrends.request import TrendReq
        return TrendReq
    except ImportError:
        print("[Trends] pytrends 未安装，请执行: pip install pytrends")
        return None


def _patch_urllib3_retry():
    """兼容性补丁: urllib3 2.x 的 Retry 不再接受 method_whitelist 参数。"""
    try:
        from urllib3.util import retry as retry_module
        original_init = retry_module.Retry.__init__

        def patched_init(self, *args, **kwargs):
            # method_whitelist → allowed_methods（urllib3 2.x 改名）
            if "method_whitelist" in kwargs:
                kwargs["allowed_methods"] = kwargs.pop("method_whitelist")
            original_init(self, *args, **kwargs)

        retry_module.Retry.__init__ = patched_init
    except Exception:
        pass  # 补丁失败也不影响其他功能


def collect(date_str: str | None = None) -> list[dict]:
    """
    采集 Google Trends 搜索异动。
    1. 获取预设关键词近 7 天趋势
    2. 对比 7 天前数据，标记暴涨（>100%）和降温（>30% 下降）
    3. 获取当前热门搜索（real-time trending searches）
    """
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    signals: list[dict] = []

    TrendReq = _safe_import_pytrends()
    if TrendReq is None:
        return signals

    try:
        pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 25), retries=2)
    except Exception as e:
        print(f"[Trends] pytrends 初始化失败: {e}")
        return signals

    # 1. 获取预设关键词近期趋势
    keyword_signals = _collect_keyword_trends(pytrends)
    signals.extend(keyword_signals)
    print(f"[Trends] 关键词趋势: {len(keyword_signals)} 条异动")

    # 2. 获取实时热门搜索
    trending_signals = _collect_trending_searches(pytrends)
    signals.extend(trending_signals)
    print(f"[Trends] 实时热门: {len(trending_signals)} 条")

    # 按热度变化排序
    signals.sort(key=lambda s: s.get("engagement", {}).get("total", 0), reverse=True)
    signals = signals[:40]

    print(f"[Trends] 总计: {len(signals)} 条")
    return signals


def _collect_keyword_trends(pytrends) -> list[dict]:
    """批量获取预设关键词的搜索趋势，识别暴涨/降温。"""
    signals: list[dict] = []
    batch_size = 5  # pytrends 限制一次最多 5 个关键词

    for i in range(0, len(TRACKED_KEYWORDS), batch_size):
        batch = TRACKED_KEYWORDS[i : i + batch_size]
        try:
            pytrends.build_payload(batch, timeframe="today 1-m", geo="")
            interest_over_time = pytrends.interest_over_time()
            if interest_over_time is None or interest_over_time.empty:
                continue

            for kw in batch:
                if kw not in interest_over_time.columns:
                    continue
                series = interest_over_time[kw].dropna()
                if len(series) < 3:
                    continue

                recent = series.iloc[-7:].mean() if len(series) >= 7 else series.mean()
                older = series.iloc[:-7].mean() if len(series) > 7 else series.iloc[0]
                current = series.iloc[-1]

                # 计算变化率
                if older > 0 and recent > 0:
                    change_pct = (recent - older) / older * 100
                else:
                    change_pct = 0

                trend = "stable"
                if change_pct > 100:
                    trend = "surging"
                elif change_pct > 30:
                    trend = "rising"
                elif change_pct < -30:
                    trend = "cooling"

                if trend == "stable":
                    continue

                signals.append({
                    "id": f"trends-kw-{kw.replace(' ', '-')}",
                    "title": f"搜索趋势: {kw}",
                    "url": f"https://trends.google.com/trends/explore?q={kw.replace(' ', '%20')}",
                    "source": "Google Trends",
                    "source_key": "trends",
                    "signal_type": "keyword_trend",
                    "discussion_count": int(current),
                    "engagement": {
                        "current_interest": int(current),
                        "recent_avg": round(float(recent), 1),
                        "older_avg": round(float(older), 1),
                        "change_pct": round(change_pct, 1),
                        "total": abs(int(change_pct)),
                    },
                    "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
                    "summary": f"「{kw}」搜索量 {'暴涨' if change_pct > 0 else '下降'} {abs(change_pct):.0f}%（当前: {int(current)}）",
                    "tags": [kw, trend],
                })

            time.sleep(1)  # 避免被限流

        except Exception as e:
            print(f"[Trends] 关键词批次 {batch} 失败: {e}")
            continue

    return signals


def _collect_trending_searches(pytrends) -> list[dict]:
    """获取 Google 实时热门搜索。"""
    signals: list[dict] = []
    try:
        trending = pytrends.trending_searches(pn="united_states")
        if trending is not None and not trending.empty:
            for _, row in trending.head(20).iterrows():
                title = str(row.iloc[0])
                signals.append({
                    "id": f"trends-rt-{title.replace(' ', '-')[:50]}",
                    "title": f"Google 实时热门: {title}",
                    "url": f"https://trends.google.com/trends/explore?q={title.replace(' ', '%20')}",
                    "source": "Google Trends",
                    "source_key": "trends",
                    "signal_type": "trending_search",
                    "discussion_count": 0,
                    "engagement": {"total": 10},
                    "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
                    "summary": f"Google 实时热门搜索: {title}",
                    "tags": [title, "trending_now"],
                })
    except Exception as e:
        print(f"[Trends] 实时热门搜索获取失败: {e}")

    return signals


def save_raw(signals: list[dict], date_str: str) -> None:
    """保存原始采集数据到 ./raw/YYYY-MM-DD/trends.json"""
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "trends",
        "count": len(signals),
        "signals": signals,
    }
    path = dir_path / "trends.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[Trends] {len(signals)} 条信号 → {path}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
