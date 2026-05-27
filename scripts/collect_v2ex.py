"""
V2EX 信号采集
数据源: V2EX API v1 (https://www.v2ex.com/api)
采集内容: 创造/分享/创业/程序员节点热帖
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"

TZ_SHANGHAI = timezone(timedelta(hours=8))
V2EX_API = "https://www.v2ex.com/api"

# 目标节点: (节点名, 权重, 类别)
TARGET_NODES = [
    ("create", 3, "产品发布"),
    ("share", 3, "分享发现"),
    ("ideas", 2, "奇思妙想"),
    ("programmer", 1, "程序员"),
]


def _fetch_node(node_name: str) -> list[dict]:
    """获取单个节点的帖子列表（v1 API）。"""
    url = f"{V2EX_API}/topics/show.json"
    try:
        resp = requests.get(url, params={"node_name": node_name}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return data
        return []
    except requests.RequestException as e:
        print(f"[V2EX] 节点 {node_name} 请求失败: {e}")
        return []


def _to_signal(topic: dict, node_name: str, node_weight: int, node_label: str) -> dict | None:
    """将 V2EX topic 转为标准信号格式。"""
    title = topic.get("title", "")
    if len(title) < 5:
        return None

    tid = topic.get("id", "")
    replies = topic.get("replies", 0) or 0
    url = topic.get("url", f"https://www.v2ex.com/t/{tid}")

    # 提取作者信息
    member = topic.get("member", {})
    author = member.get("username", "") if member else ""

    return {
        "id": f"v2ex-{tid}",
        "title": title.strip(),
        "url": url,
        "source": f"V2EX {node_label}",
        "source_key": "v2ex",
        "signal_type": "topic",
        "discussion_count": replies,
        "engagement": {
            "replies": replies,
            "node_weight": node_weight,
            "total": replies * 2 + node_weight * 5,
        },
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "raw_created": topic.get("created", 0),
        "summary": f"[{node_label}] {title[:80]}（{replies} 回复）",
        "tags": [node_name, node_label],
        "author": author,
        "node": topic.get("node", {}),
    }


def collect(date_str: str | None = None) -> list[dict]:
    """
    采集 V2EX 4 个核心节点热帖。
    按互动量（replies×2 + node_weight×5）降序，去重后取 top 40。
    """
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    seen: set[str] = set()
    signals: list[dict] = []

    for node_name, weight, label in TARGET_NODES:
        topics = _fetch_node(node_name)
        node_signals = 0
        for t in topics:
            signal = _to_signal(t, node_name, weight, label)
            if signal and signal["id"] not in seen:
                seen.add(signal["id"])
                signals.append(signal)
                node_signals += 1
        print(f"[V2EX] {label}({node_name}): {node_signals} 条有效信号")

    signals.sort(key=lambda s: s["engagement"]["total"], reverse=True)
    signals = signals[:40]

    print(f"[V2EX] 总计: {len(signals)} 条 → {date}")
    return signals


def save_raw(signals: list[dict], date_str: str) -> None:
    """保存原始采集数据到 ./raw/YYYY-MM-DD/v2ex.json"""
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "v2ex",
        "count": len(signals),
        "signals": signals,
    }
    path = dir_path / "v2ex.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[V2EX] {len(signals)} 条信号 → {path}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
