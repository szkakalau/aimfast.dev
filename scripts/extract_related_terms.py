"""
从已有趋势研究报告中提取 Related Terms，写入 trend_terms.json。
零额外 LLM 调用 — 解析已有报告中的 "Related Terms" 章节。

用法:
  python scripts/extract_related_terms.py              # 处理所有未提取的 term
  python scripts/extract_related_terms.py --dry-run    # 仅统计，不写入
  python scripts/extract_related_terms.py --date YYYY-MM-DD  # 指定日期（用于管线日志）
"""
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACKING_FILE = ROOT / "tracking" / "trend_terms.json"

TZ_SHANGHAI = timezone(timedelta(hours=8))

# 关系类型关键词映射 — 从描述文本推断关系类型
RELATION_PATTERNS: list[tuple[str, list[str]]] = [
    ("depends-on", ["依赖", "依赖关系", "depends on", "requires", "需要", "基于", "底层", "built on"]),
    ("competes-with", ["竞争", "替代", "alternative", "competitor", "competing", "取代"]),
    ("complements", ["互补", "结合", "complements", "配合", "协同", "协作"]),
    ("enables", ["推动", "使能", "驱动", "enables", "支撑", "支撑层"]),
    ("part-of", ["子领域", "子集", "subset", "subfield", "一部分", "分支"]),
]


def infer_relation_type(description: str) -> str:
    """从描述文本推断关系类型，默认为 related-to。"""
    desc_lower = description.lower()
    for rel_type, keywords in RELATION_PATTERNS:
        if any(kw in desc_lower for kw in keywords):
            return rel_type
    return "related-to"


def extract_from_english_section(text: str) -> list[dict]:
    """从英文格式的 Related Terms 章节提取（段落式，**Term** - desc）。"""
    relations = []
    # 匹配 **Term Name** – description（可选中文注解，如 **Term**（中文名）：desc）
    pattern = r'\*\*([^*]+?)\*\*\s*(?:（[^）]*）)?\s*(?:——|[–\-—:：])\s*(.+?)(?=\n\n|\n\*\*|\Z)'
    for m in re.finditer(pattern, text, re.DOTALL):
        term = m.group(1).strip()
        desc = m.group(2).strip()
        # 清理：去除末尾句号后多余内容，限制到句子边界
        desc = re.sub(r'\s+', ' ', desc)[:200]
        if term and desc and len(term) >= 2 and len(desc) >= 10:
            relations.append({
                "term": term.lower(),
                "relation": infer_relation_type(desc),
                "reason": desc,
            })
    return relations


def extract_from_chinese_section(text: str) -> list[dict]:
    """从中文格式的 Related Terms 章节提取（列表式，- **Term**：desc）。"""
    relations = []
    # 匹配 - **Term**：description 或 - **Term** — description（可选中文注解）
    pattern = r'[-•]\s*\*\*([^*]+?)\*\*\s*(?:（[^）]*）)?\s*(?:——|[：:—–\-])\s*(.+?)(?=\n[-•]|\n\n|\Z)'
    for m in re.finditer(pattern, text, re.DOTALL):
        term = m.group(1).strip()
        desc = m.group(2).strip()
        desc = re.sub(r'\s+', ' ', desc)[:200]
        if term and desc and len(term) >= 2 and len(desc) >= 10:
            relations.append({
                "term": term.lower(),
                "relation": infer_relation_type(desc),
                "reason": desc,
            })
    return relations


def extract_related_from_report(md_path: str) -> list[dict]:
    """从单个研究报告 markdown 中提取 Related Terms。

    支持两种格式：
      1. 英文段落式：## Related terms\n**Term** – description\n**Term2** – description
      2. 中文列表式：## Related terms（相关趋势）\n- **Term**：description
    """
    full_path = ROOT / md_path if md_path else None
    if not full_path or not full_path.exists():
        return []

    text = full_path.read_text(encoding="utf-8")

    # 匹配 Related Terms 章节（支持中英文变体）
    # 从 "## Related terms" 到下一个 "## " 标题或文件末尾
    pattern = r'##\s*Related\s+[Tt]erms[^#\n]*\s*\n(.*?)(?=\n##\s|\Z)'
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if not match:
        return []

    section = match.group(1).strip()
    if not section:
        return []

    # 尝试中文列表格式
    relations = extract_from_chinese_section(section)
    if relations:
        return relations[:5]

    # 尝试英文段落格式
    relations = extract_from_english_section(section)
    if relations:
        return relations[:5]

    # 章节存在但两种格式都未匹配 → 格式可能已变化
    print(f"[related_terms] WARNING: {md_path} — 有 Related Terms 章节但无法解析格式")
    return relations[:5]


def run(date_str: str | None = None, dry_run: bool = False):
    """扫描所有有研究报告的 term，提取 related_terms。

    Args:
        date_str: 日期（仅用于日志标记）
        dry_run: True 时仅统计不写入
    """
    today = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")

    if not TRACKING_FILE.exists():
        print("[related_terms] trend_terms.json 不存在，跳过")
        return

    trend_data = json.loads(TRACKING_FILE.read_text(encoding="utf-8"))
    terms = trend_data.get("terms", [])
    total_with_reports = sum(1 for t in terms if t.get("research_md_path"))
    print(f"[related_terms] 共 {len(terms)} 个 term，其中 {total_with_reports} 个有研究报告")

    updated = 0
    skipped_existing = 0
    skipped_no_section = 0

    for term in terms:
        # 已有关系的跳过
        if term.get("related_terms"):
            skipped_existing += 1
            continue

        md_path = term.get("research_md_path", "")
        if not md_path:
            continue

        relations = extract_related_from_report(md_path)
        if relations:
            if not dry_run:
                term["related_terms"] = relations
            updated += 1
        else:
            skipped_no_section += 1

    if updated > 0 and not dry_run:
        # 直接保存 trend_terms.json
        trend_data["updated_at"] = datetime.now(TZ_SHANGHAI).isoformat()
        TRACKING_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TRACKING_FILE, "w", encoding="utf-8") as f:
            json.dump(trend_data, f, ensure_ascii=False, indent=2)
        print(f"[related_terms] 为 {updated} 个 term 提取了关系数据")

    # 统计报告
    print(f"[related_terms] 结果: 新增 {updated} | 已有关系 {skipped_existing} | 无章节 {skipped_no_section}")
    if dry_run:
        print("[related_terms] DRY RUN — 未写入任何数据")

    # 打印几个样例
    if updated > 0:
        print("\n[related_terms] 样例:")
        sample_count = 0
        for term in terms:
            if term.get("related_terms"):
                name = term.get("canonical_zh", "") or term.get("canonical", "?")
                rels = term["related_terms"]
                print(f"  {name}: {len(rels)} 条关系")
                for r in rels[:3]:
                    print(f"    → {r['term']} [{r['relation']}]")
                sample_count += 1
                if sample_count >= 5:
                    break


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    date_str = None
    for i, arg in enumerate(sys.argv):
        if arg == "--date" and i + 1 < len(sys.argv):
            date_str = sys.argv[i + 1]
    run(date_str=date_str, dry_run=dry_run)
