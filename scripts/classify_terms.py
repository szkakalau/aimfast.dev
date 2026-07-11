"""
第四层：Term 生命周期分类
──────────────────────────
不依赖搜索量/讨论量，纯粹按「首次发现日期」判断 term 所处阶段。

阶段定义:
  Nascent    (0-7 天):   刚出现的新词——最早发现者优势
  Emergent   (8-30 天):  正在扩散——值得开始关注
  Validating (31-90 天): 需要验证——是真的趋势还是一时热度
  Rising     (91+ 天):   持续存在——已被市场确认的趋势

输入:
  - tracking/canonical_terms.json (含 first_seen)
  - tracking/term_stages.json     (昨天的阶段数据，用于检测阶段转换)

输出:
  - tracking/term_stages.json     (今天的阶段快照 + 转换记录)
  - 更新 canonical_terms.json     (stage, age_days 字段)
  - daily/{date}/stage_report.json (日报用摘要)
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACKING_DIR = ROOT / "tracking"
DAILY_DIR = ROOT / "daily"

TZ_SHANGHAI = timezone(timedelta(hours=8))
CANONICAL_PATH = TRACKING_DIR / "canonical_terms.json"
STAGES_PATH = TRACKING_DIR / "term_stages.json"

# ── 阶段定义 ──────────────────────────────────────────

STAGE_RULES = [
    (0, 7, "nascent"),
    (8, 30, "emergent"),
    (31, 90, "validating"),
    (91, float("inf"), "rising"),
]

STAGE_LABELS = {
    "nascent": "Nascent (0-7天)",
    "emergent": "Emergent (8-30天)",
    "validating": "Validating (31-90天)",
    "rising": "Rising (91+天)",
}

STAGE_ICON = {
    "nascent": "[N]",
    "emergent": "[E]",
    "validating": "[V]",
    "rising": "[R]",
}


def _classify(age_days: int) -> str:
    """根据年龄（天）返回阶段名。"""
    for min_d, max_d, stage in STAGE_RULES:
        if min_d <= age_days <= max_d:
            return stage
    return "nascent"


def _age_in_days(first_seen: str, today: datetime.date) -> int:
    """计算距今多少天。"""
    if not first_seen:
        return 0
    try:
        fs_date = datetime.strptime(first_seen, "%Y-%m-%d").date()
        return (today - fs_date).days
    except (ValueError, TypeError):
        return 0


def _load_yesterday_stages() -> dict[str, dict]:
    """加载昨天的阶段数据（用于检测转换）。"""
    if STAGES_PATH.exists():
        try:
            data = json.loads(STAGES_PATH.read_text(encoding="utf-8"))
            return data.get("terms", {})
        except (json.JSONDecodeError, KeyError):
            pass
    return {}


def _detect_transitions(
    today_stages: dict[str, str],
    yesterday_stages: dict[str, dict],
    date_str: str,
) -> list[dict]:
    """检测阶段转换（如 nascent → emergent）。"""
    transitions: list[dict] = []
    for term_name, today_stage in today_stages.items():
        yesterday = yesterday_stages.get(term_name)
        if not yesterday:
            continue
        yesterday_stage = yesterday.get("stage", "")
        if yesterday_stage and yesterday_stage != today_stage:
            transitions.append({
                "term": term_name,
                "from": yesterday_stage,
                "to": today_stage,
                "date": date_str,
            })
    return transitions


def _find_newborns(canonicals: dict, today: datetime.date) -> list[dict]:
    """找到今天首次出现的 term。"""
    newborns = []
    today_str = today.strftime("%Y-%m-%d")
    for name, entry in canonicals.items():
        if entry.get("first_seen") == today_str:
            newborns.append({
                "term": name,
                "term_type": entry.get("term_type", "unknown"),
                "sources": entry.get("sources", {}),
                "distinct_sources": entry.get("distinct_sources", 0),
            })
    newborns.sort(key=lambda x: -x["distinct_sources"])
    return newborns


def run(date_str: str | None = None):
    """执行阶段分类。"""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    today = datetime.strptime(date, "%Y-%m-%d").date()

    print(f"\n{'='*50}")
    print(f"[Stages] 第四层：Term 生命周期分类 — {date}")
    print(f"{'='*50}")

    # Step 1: 加载 canonical terms
    if not CANONICAL_PATH.exists():
        print("[Stages] canonical_terms.json 不存在，跳过")
        return

    canonical_data = json.loads(CANONICAL_PATH.read_text(encoding="utf-8"))
    canonicals = canonical_data.get("canonicals", {})
    if not canonicals:
        print("[Stages] canonical_terms 为空，跳过")
        return

    # Step 2: 加载昨天阶段
    yesterday_stages = _load_yesterday_stages()

    # Step 3: 计算每个 term 的年龄和阶段
    today_stages: dict[str, str] = {}
    stage_counts: dict[str, int] = {"nascent": 0, "emergent": 0, "validating": 0, "rising": 0}
    terms_detail: dict[str, dict] = {}

    for name, entry in canonicals.items():
        age = _age_in_days(entry.get("first_seen", ""), today)
        stage = _classify(age)

        today_stages[name] = stage
        stage_counts[stage] += 1

        terms_detail[name] = {
            "term": name,
            "term_type": entry.get("term_type", "unknown"),
            "first_seen": entry.get("first_seen", ""),
            "last_seen": entry.get("last_seen", ""),
            "age_days": age,
            "stage": stage,
            "stage_label": STAGE_LABELS[stage],
            "sources": entry.get("sources", {}),
            "distinct_sources": entry.get("distinct_sources", 0),
            "appearances": entry.get("appearances", 0),
        }

    # Step 3: 更新 canonical_terms.json
    for name, entry in canonicals.items():
        detail = terms_detail[name]
        entry["age_days"] = detail["age_days"]
        entry["stage"] = detail["stage"]

    canonical_data["last_updated"] = datetime.now(TZ_SHANGHAI).isoformat()
    from scripts.defaults import atomic_write_json
    atomic_write_json(CANONICAL_PATH, canonical_data)

    # Step 4: 检测阶段转换和新词
    transitions = _detect_transitions(today_stages, yesterday_stages, date)
    newborns = _find_newborns(canonicals, today)

    # Step 5: 保存 term_stages.json
    stage_data = {
        "_schema": "Term 生命周期快照 — 按年龄划分阶段",
        "_version": "1.0",
        "date": date,
        "summary": {
            "total_terms": len(canonicals),
            "newborns_today": len(newborns),
            "transitions_today": len(transitions),
            "stage_distribution": stage_counts,
        },
        "newborns": newborns,
        "transitions": transitions,
        "terms": terms_detail,
    }

    from scripts.defaults import atomic_write_json
    atomic_write_json(STAGES_PATH, stage_data)

    # Step 6: 输出日报摘要
    print(f"\n[Stages] Term 年龄分布:")
    for stage in ["nascent", "emergent", "validating", "rising"]:
        count = stage_counts[stage]
        label = STAGE_LABELS[stage]
        bar = "█" * max(1, count // max(1, max(stage_counts.values()) // 30))
        print(f"  {STAGE_ICON[stage]} {label:25s} {count:4d}  {bar}")

    if newborns:
        print(f"\n[Stages] [NEW] 今日新词 ({len(newborns)}):")
        for nb in newborns[:15]:
            srcs = ", ".join(list(nb["sources"].keys())[:3])
            print(f"  [{nb['term_type']}] {nb['term']} ← {srcs}")
        if len(newborns) > 15:
            print(f"  ... 还有 {len(newborns) - 15} 个")

    if transitions:
        print(f"\n[Stages] [TRANS] 阶段转换 ({len(transitions)}):")
        for t in transitions[:10]:
            print(f"  {t['term']}: {t['from']} → {t['to']}")
    else:
        print(f"\n[Stages] 今日无阶段转换（首次运行或所有 term 未跨阶段）")

    # Step 7: 保存日报文件
    output_dir = DAILY_DIR / date
    output_dir.mkdir(parents=True, exist_ok=True)
    stage_report = {
        "date": date,
        "generated_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "newborns": newborns,
        "transitions": transitions,
        "distribution": stage_counts,
        "top_emergent": sorted(
            [d for d in terms_detail.values() if d["stage"] == "emergent"],
            key=lambda x: -x["appearances"],
        )[:10],
        "top_validating": sorted(
            [d for d in terms_detail.values() if d["stage"] == "validating"],
            key=lambda x: -x["appearances"],
        )[:10],
    }
    (output_dir / "stage_report.json").write_text(
        json.dumps(stage_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n[Stages] term_stages.json → {STAGES_PATH}")
    print(f"[Stages] stage_report.json → {output_dir / 'stage_report.json'}")
    return stage_data


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    run(today)
