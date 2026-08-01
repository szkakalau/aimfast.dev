"""
Quality Audit — 每周人工质量检查系统
输入: tracking/term_scores.json, tracking/trend_terms.json, content/trends/*.md, tracking/source_audit.json
输出: tracking/quality_audit.json
运行: python scripts/quality_audit.py (手动，不加入 pipeline)
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
TRACKING_DIR = ROOT / "tracking"
CONTENT_TRENDS_DIR = ROOT / "content" / "trends"
TZ_SHANGHAI = timezone(timedelta(hours=8))


def load_json_safe(path: Path) -> dict:
    """加载 JSON 文件，任何失败返回空 dict。"""
    if not path.exists():
        print(f"  [WARN] 文件不存在: {path}", file=sys.stderr)
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [WARN] JSON 加载失败: {path} — {e}", file=sys.stderr)
        return {}


def get_top_n_terms(term_scores: dict, n: int = 5) -> list[dict]:
    """从 term_scores.json 中提取分数前 N 的词条。"""
    scores = term_scores.get("scores", [])
    if not scores:
        return []
    sorted_scores = sorted(scores, key=lambda s: s.get("score", 0), reverse=True)
    return [
        {
            "term": s.get("term", "?"),
            "score": s.get("score", 0),
            "stage": s.get("stage", "unknown"),
        }
        for s in sorted_scores[:n]
    ]


def get_bottom_n_terms(term_scores: dict, n: int = 5) -> list[dict]:
    """从 term_scores.json 中提取分数后 N 的词条。"""
    scores = term_scores.get("scores", [])
    if not scores:
        return []
    sorted_scores = sorted(scores, key=lambda s: s.get("score", 0))
    return [
        {
            "term": s.get("term", "?"),
            "score": s.get("score", 0),
            "stage": s.get("stage", "unknown"),
        }
        for s in sorted_scores[:n]
    ]


def get_stage_distribution(trend_terms: dict) -> dict[str, int]:
    """统计各 stage 下的词条数量。"""
    terms = trend_terms.get("terms", [])
    distribution: dict[str, int] = {}
    for t in terms:
        stage = t.get("stage", "unknown")
        distribution[stage] = distribution.get(stage, 0) + 1
    return distribution


def sample_reports(n: int = 5) -> list[dict]:
    """抽取最新 N 篇趋势报告进行完整性检查。"""
    if not CONTENT_TRENDS_DIR.exists():
        return []

    # 只取中文版 (*.md，排除 *-en.md 和 _archive/)
    md_files = [
        f for f in CONTENT_TRENDS_DIR.glob("*.md")
        if not f.name.endswith("-en.md") and "_archive" not in str(f)
    ]

    if not md_files:
        return []

    # 按修改时间倒序
    md_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    sampled = md_files[:n]

    results = []
    for f in sampled:
        slug = f.stem
        en_path = CONTENT_TRENDS_DIR / f"{slug}-en.md"
        has_zh = f.exists()
        has_en = en_path.exists()

        content = ""
        word_count_zh = 0
        has_opportunity = False
        try:
            content = f.read_text(encoding="utf-8")
            word_count_zh = len(content.split())
            has_opportunity = (
                "## Product ideas" in content
                or "## Commercial opportunities" in content
                or "## 产品机会" in content
                or "## 商业机会" in content
            )
        except OSError:
            pass

        results.append({
            "slug": slug,
            "has_zh": has_zh,
            "has_en": has_en,
            "has_opportunity": has_opportunity,
            "word_count_zh": word_count_zh,
        })

    return results


def get_source_health() -> dict:
    """从 source_audit.json 汇总信源健康度。"""
    audit = load_json_safe(TRACKING_DIR / "source_audit.json")
    sources = audit.get("sources", [])

    p0 = sum(1 for s in sources if s.get("recommendation") == "keep_p0")
    p2 = sum(1 for s in sources if s.get("recommendation") == "keep_p2")
    cut = sum(1 for s in sources if s.get("recommendation") == "cut")
    investigate = sum(1 for s in sources if s.get("recommendation") == "investigate")

    return {
        "p0_sources": p0,
        "p2_sources": p2,
        "cut_candidates": cut,
        "investigate": investigate,
    }


def generate_alerts(audit_data: dict) -> list[str]:
    """生成人类可读的告警。"""
    alerts = []

    # 高分但无报告的告警
    top_5 = audit_data.get("top_5_terms", [])
    for t in top_5:
        if t["score"] < 10:
            alerts.append(
                f"Top-5 词条 '{t['term']}' (score={t['score']}) 评分极低但在前5 — "
                f"检查评分是否合理"
            )

    # 低分词条有报告
    bottom_5 = audit_data.get("bottom_5_terms", [])
    for t in bottom_5:
        if t["score"] < 10:
            alerts.append(
                f"Bottom-5 词条 '{t['term']}' (score={t['score']}) 评分极低 — "
                f"考虑是否应降低报告优先级"
            )

    # Stage 分布异常
    stage_dist = audit_data.get("stage_distribution", {})
    total = sum(stage_dist.values())
    if total > 0:
        nascent_pct = stage_dist.get("nascent", 0) / total
        if nascent_pct > 0.5:
            alerts.append(
                f"Nascent stage 占比 {nascent_pct:.0%} ({stage_dist['nascent']}/{total}) — "
                f"可能表明分类管线滞后或信源噪声过大"
            )

    # 报告完整性
    reports = audit_data.get("report_sample", [])
    for r in reports:
        if not r["has_en"]:
            alerts.append(f"报告 '{r['slug']}' 缺少英文版 (-en.md)")
        if not r["has_opportunity"]:
            alerts.append(f"报告 '{r['slug']}' 缺少商业机会章节")
        if r["word_count_zh"] < 200:
            alerts.append(
                f"报告 '{r['slug']}' 中文内容过短 ({r['word_count_zh']} 词) — "
                f"可能是生成失败或截断"
            )

    # 信源健康
    source_health = audit_data.get("source_health", {})
    if source_health.get("cut_candidates", 0) > 0:
        alerts.append(
            f"有 {source_health['cut_candidates']} 个信源候选待清理 — "
            f"运行 scripts/audit_sources.py 查看详情"
        )
    if source_health.get("investigate", 0) > 0:
        alerts.append(
            f"有 {source_health['investigate']} 个信源需要调查 — "
            f"可能产生数据但不产生有效信号"
        )

    return alerts


def run(date_str: str | None = None):
    """主入口：汇聚所有数据源，生成质量审计报告。"""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")

    print(f"[QualityAudit] 开始审计 — {date}")

    # 1. 加载输入
    term_scores = load_json_safe(TRACKING_DIR / "term_scores.json")
    trend_terms = load_json_safe(TRACKING_DIR / "trend_terms.json")

    # 2. Top/Bottom 5
    top_5 = get_top_n_terms(term_scores, 5)
    bottom_5 = get_bottom_n_terms(term_scores, 5)

    # 3. Stage 分布
    stage_dist = get_stage_distribution(trend_terms)

    # 4. 报告抽样
    reports = sample_reports(5)

    # 5. 信源健康
    source_health = get_source_health()

    # 6. 组装输出
    output = {
        "date": date,
        "generated_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "top_5_terms": top_5,
        "bottom_5_terms": bottom_5,
        "report_sample": reports,
        "stage_distribution": stage_dist,
        "source_health": source_health,
        "alerts": [],
    }

    # 7. 生成告警
    output["alerts"] = generate_alerts(output)

    # 8. 写入
    from scripts.defaults import atomic_write_json
    output_path = TRACKING_DIR / "quality_audit.json"
    atomic_write_json(output_path, output)

    print(f"[QualityAudit] 报告已保存到 {output_path}")
    if output["alerts"]:
        print(f"[QualityAudit] {len(output['alerts'])} 条告警:")
        for alert in output["alerts"]:
            print(f"  [!] {alert}")
    else:
        print("[QualityAudit] 一切正常，无告警 [OK]")

    return output


if __name__ == "__main__":
    run()
