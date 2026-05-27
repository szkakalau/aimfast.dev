"""
小红书 信号采集
数据源: 小红书 APP（爆款检测 skill）
采集内容: 创业/副业爆款笔记 + 搜索趋势

前置依赖: 小红书爆款检测 skill（Claude Skill）。
该 skill 负责抓取小红书指定话题的热门笔记并结构化输出。
本脚本负责消费 skill 的输出并标准化为信号格式。
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"

TZ_SHANGHAI = timezone(timedelta(hours=8))

# 目标话题标签（小红书搜索关键词）
TARGET_TOPICS = [
    "创业",
    "副业",
    "独立开发",
    "一人公司",
    "AI工具",
    "AI赚钱",
    "AI变现",
    "MicroSaaS",
]

# 爆款检测 skill 默认输出路径
SKILL_OUTPUT_PATH = RAW_DIR / "xhs_skill_output"


def _find_latest_skill_output() -> Path | None:
    """查找最新的爆款检测 skill 输出文件。"""
    if not SKILL_OUTPUT_PATH.exists():
        return None
    json_files = sorted(SKILL_OUTPUT_PATH.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return json_files[0] if json_files else None


def _parse_skill_output(filepath: Path) -> list[dict]:
    """解析爆款检测 skill 的输出。"""
    try:
        data = json.loads(filepath.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return []

    # 适配多种输出格式
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("notes") or data.get("items") or data.get("posts") or []
    return []


def _to_signal(note: dict) -> dict:
    """将小红书笔记转为标准信号格式。"""
    title = note.get("title") or note.get("content", "")[:80] or "无标题"
    likes = note.get("likes") or note.get("like_count") or 0
    collects = note.get("collects") or note.get("collect_count") or 0
    comments = note.get("comments") or note.get("comment_count") or 0

    return {
        "id": f"xhs-{note.get('note_id', note.get('id', title.replace(' ', '-')))}",
        "title": title.strip(),
        "url": note.get("url") or note.get("share_url", ""),
        "source": "小红书",
        "source_key": "xiaohongshu",
        "signal_type": "note",
        "discussion_count": comments,
        "engagement": {
            "likes": int(likes),
            "collects": int(collects),
            "comments": int(comments),
            "total": int(likes) + int(collects) * 2 + int(comments) * 3,
        },
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "summary": f"[小红书] {title[:100]}（{likes} 赞 / {collects} 收藏 / {comments} 评论）",
        "tags": note.get("tags") or note.get("topics") or [],
        "author": note.get("author") or note.get("user", {}).get("name", ""),
    }


def collect(date_str: str | None = None) -> list[dict]:
    """
    采集小红书爆款笔记。

    前置条件:
    1. 已配置小红书爆款检测 skill
    2. Skill 已输出 JSON 到 ./raw/xhs_skill_output/
    3. 输出文件包含 notes 列表

    若 skill 输出不存在，返回占位信号。
    """
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    signals: list[dict] = []

    latest = _find_latest_skill_output()
    if latest is None:
        print(f"[小红书] 未找到爆款检测 skill 输出。")
        print(f"[小红书] 请确保爆款检测 skill 已将 JSON 输出到 {SKILL_OUTPUT_PATH}")
        print(f"[小红书] 目标话题: {', '.join(TARGET_TOPICS)}")
        return signals

    print(f"[小红书] 读取: {latest}")
    notes = _parse_skill_output(latest)

    for note in notes:
        signal = _to_signal(note)
        signals.append(signal)

    signals.sort(key=lambda s: s["engagement"]["total"], reverse=True)
    signals = signals[:40]

    print(f"[小红书] {len(signals)} 条爆款笔记")
    return signals


def save_raw(signals: list[dict], date_str: str) -> None:
    """保存原始采集数据。"""
    dir_path = RAW_DIR / date_str
    dir_path.mkdir(parents=True, exist_ok=True)
    output = {
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "source": "xiaohongshu",
        "note": "数据来自小红书爆款检测 skill。若信号数为 0，说明 skill 尚未产出数据。",
        "count": len(signals),
        "signals": signals,
    }
    path = dir_path / "xhs.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[小红书] {len(signals)} 条信号 → {path}")


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    data = collect(today)
    save_raw(data, today)
