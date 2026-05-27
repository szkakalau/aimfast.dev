"""
即刻 信号采集
数据源: 即刻 APP（web 端 + mobile_use fallback）
采集内容: 创业/副业/独立开发圈热门动态

即刻是移动端优先平台，完整采集需要 mobile_use。
当前实现：尝试 web 端搜素 + 明确标记依赖。
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"

TZ_SHANGHAI = timezone(timedelta(hours=8))

# 即刻 web 端
JIKE_WEB = "https://web.okjike.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
}


def _search_web(query: str) -> list[dict]:
    """尝试通过即刻 web 端搜索公开内容。"""
    results: list[dict] = []
    try:
        # 即刻 web 搜索
        url = f"{JIKE_WEB}/search"
        resp = requests.get(url, headers=HEADERS, params={"q": query}, timeout=10)
        if resp.status_code == 200:
            # 即刻 web 端返回 JS 渲染页面，搜索功能受限
            # 此处仅做连通性探测，实际数据需 mobile_use
            results.append({
                "title": f"即刻搜索: {query}",
                "url": f"{JIKE_WEB}/search?q={query}",
                "source": "即刻",
                "note": "web端搜索结果需 mobile_use 解析",
            })
    except requests.RequestException:
        pass
    return results


def collect(date_str: str | None = None) -> list[dict]:
    """
    采集即刻热帖。

    完整采集需要 mobile_use（Claude 操控手机抓取即刻 APP）。
    当前返回占位信号，标记为"待 mobile_use 采集"。

    配置方式:
    1. 启用 Claude mobile_use session
    2. 目标话题: 创业、副业、独立开发、产品
    3. 手动或自动截图热门动态
    4. 数据输出到 ./raw/YYYY-MM-DD/jike.json
    """
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    signals: list[dict] = []

    # 尝试 web 搜索
    search_topics = ["独立开发", "创业", "副业", "MicroSaaS"]
    for topic in search_topics:
        web_results = _search_web(topic)
        for r in web_results:
            signals.append({
                "id": f"jike-web-{topic}",
                "title": r["title"],
                "url": r.get("url", ""),
                "source": "即刻",
                "source_key": "jike",
                "signal_type": "placeholder",
                "discussion_count": 0,
                "engagement": {"total": 1},
                "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
                "summary": f"[即刻] {topic}相关搜索（需 mobile_use 完整采集）",
                "tags": [topic, "needs-mobile-use"],
            })

    # 检查是否有 mobile_use 产出的数据
    mobile_data_path = RAW_DIR / date_str / "jike_mobile.json"
    if mobile_data_path.exists():
        try:
            mobile_data = json.loads(mobile_data_path.read_text(encoding="utf-8"))
            mobile_signals = mobile_data.get("signals", [])
            signals = mobile_signals + signals  # mobile_use 数据优先
            print(f"[即刻] 加载 mobile_use 数据: {len(mobile_signals)} 条")
        except (json.JSONDecodeError, KeyError):
            pass

    if not signals:
        print("[即刻] 即刻采集需要 mobile_use 支持。")
        print("[即刻] 当前产出占位信号，待 mobile_use session 采集后替换。")
        print("[即刻] 目标话题: 创业、副业、独立开发、产品")
    else:
        print(f"[即刻] {len(signals)} 条信号（含 web 探测）")

    return signals[:30]


def save_raw(signals: list[dict], date_str: str) -> None:
    """保存原始采集数据。"""
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "jike",
        "note": "即刻完整采集需要 mobile_use。当产出为占位信号时，说明尚未进行 mobile_use 采集。",
        "count": len(signals),
        "signals": signals,
    }
    path = dir_path / "jike.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[即刻] {len(signals)} 条信号 → {path}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
