"""
第三层：Term 归一化引擎
──────────────────────────
将 term_index 中的变体名（如 "Claude5", "Sonnet5", "Claude Sonnet Five"）
归一化为 canonical name（"Claude Sonnet 5"）。

算法:
  1. 字符串相似度 → 候选对（便宜，无 LLM）
  2. Union-Find → 聚类组
  3. LLM 验证 + 选 canonical 名（准确，每簇一次调用）
  4. 合并统计 → canonical_terms.json

输入: tracking/term_index.json
输出:
  - tracking/canonical_terms.json  — canonical 名 + aliases + 合并统计
  - tracking/term_index.json       — 更新 terms 的 canonical_name 字段
"""
import json
import re
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACKING_DIR = ROOT / "tracking"
CONFIG_PATH = ROOT / "config.json"

TZ_SHANGHAI = timezone(timedelta(hours=8))
TERM_INDEX_PATH = TRACKING_DIR / "term_index.json"
CANONICAL_PATH = TRACKING_DIR / "canonical_terms.json"

# ── 候选对生成: 字符串相似度 ─────────────────────────────

def _tokenize(name: str) -> set[str]:
    """将名称拆为 token 集合（数字也保留，模型名关键特征）。"""
    # "GPT-5.6" → {"gpt", "5", "6"}
    # "Claude Sonnet 5" → {"claude", "sonnet", "5"}
    tokens = re.findall(r"[a-zA-Z0-9]+", name.lower())
    # 过滤 1-2 字母的无意义 token，但保留数字
    return {t for t in tokens if len(t) >= 2 or t.isdigit()}


def _jaccard(a: set, b: set) -> float:
    """Jaccard 相似度。"""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _char_similarity(a: str, b: str) -> float:
    """字符级模糊匹配。"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _acronym_match(a: str, b: str) -> bool:
    """检测首字母缩写匹配。
    例: "VS Code" ↔ "Visual Studio Code"
        "AI SDK" ↔ "Artificial Intelligence SDK" (弱匹配)
    """
    a_upper = "".join(c for c in a if c.isupper())
    b_upper = "".join(c for c in b if c.isupper())
    if len(a_upper) >= 3 and len(b_upper) >= 3:
        return a_upper == b_upper or a_upper in b_upper or b_upper in a_upper
    return False


# 候选对生成阈值: term 数超过此值切换为词索引方案（避免 O(n²)）
_WORD_INDEX_THRESHOLD = 500


def _score_pair(name_i: str, name_j: str, tokens_i: set[str], tokens_j: set[str]) -> float | None:
    """对一对名称打分，返回平均分数；不满足阈值则返回 None。"""
    score = 0.0
    reasons = 0

    jac = _jaccard(tokens_i, tokens_j)
    if jac >= 0.5:
        score += jac
        reasons += 1

    char_sim = _char_similarity(name_i, name_j)
    if char_sim >= 0.70:
        score += char_sim
        reasons += 1

    if _acronym_match(name_i, name_j):
        score += 0.8
        reasons += 1

    a_clean = re.sub(r"[^a-zA-Z0-9]", "", name_i.lower())
    b_clean = re.sub(r"[^a-zA-Z0-9]", "", name_j.lower())
    shorter = a_clean if len(a_clean) <= len(b_clean) else b_clean
    longer = b_clean if len(a_clean) <= len(b_clean) else a_clean
    if len(shorter) >= 4 and shorter in longer:
        score += 0.85
        reasons += 1

    high_confidence = jac >= 0.80 or char_sim >= 0.85
    if reasons >= 2 or (reasons == 1 and high_confidence):
        return score / max(reasons, 1)
    return None


def _find_candidate_pairs(term_names: list[str]) -> list[tuple[int, int, float]]:
    """用字符串相似度生成候选重复对。返回 [(i, j, score), ...]。

    小数据集 (<500 terms): O(n²) 直接比较。
    大数据集 (≥500 terms): 词索引方案 → 只在共享关键词的 term 对之间比较。
    """
    n = len(term_names)
    if n == 0:
        return []

    tokens_list = [_tokenize(name) for name in term_names]

    # ── 小数据集: O(n²) 直接比较 ──
    if n < _WORD_INDEX_THRESHOLD:
        pairs: list[tuple[int, int, float]] = []
        for i in range(n):
            for j in range(i + 1, n):
                s = _score_pair(term_names[i], term_names[j], tokens_list[i], tokens_list[j])
                if s is not None:
                    pairs.append((i, j, s))
        return pairs

    # ── 大数据集: 词索引方案（参考 track_recurring.py 倒排索引模式）──
    print(f"  [Norm] term 数超过 {_WORD_INDEX_THRESHOLD}，切换词索引方案避免 O(n²)")

    # 1. 构建倒排索引: word → [term_indices]
    from collections import defaultdict
    word_index: dict[str, list[int]] = defaultdict(list)
    word_df: dict[str, int] = defaultdict(int)

    for i, tokens in enumerate(tokens_list):
        for token in tokens:
            word_index[token].append(i)
        for token in set(tokens):
            word_df[token] += 1

    # 2. 过滤高频词（>30% 的 term 都包含 → 无区分度）
    max_df = int(n * 0.30)
    for word in list(word_index.keys()):
        if word_df.get(word, 0) > max_df:
            del word_index[word]

    # 3. 从词索引生成候选对（去重）
    seen_pairs: set[tuple[int, int]] = set()
    pairs: list[tuple[int, int, float]] = []

    for word, indices in word_index.items():
        bucket = indices
        if len(bucket) < 2:
            continue
        for a in range(len(bucket)):
            for b in range(a + 1, len(bucket)):
                i, j = bucket[a], bucket[b]
                if i > j:
                    i, j = j, i
                if (i, j) in seen_pairs:
                    continue
                seen_pairs.add((i, j))
                s = _score_pair(term_names[i], term_names[j], tokens_list[i], tokens_list[j])
                if s is not None:
                    pairs.append((i, j, s))

    print(f"  [Norm] 词索引: {len(word_index)} 个关键词, "
          f"候选对 {len(seen_pairs)} (vs O(n²)={n*(n-1)//2:,})")
    return pairs


# ── LLM 验证 ────────────────────────────────────────────

VERIFY_SYSTEM_PROMPT = """你是一个技术术语归一化专家。你的任务是判断一组名称是否指向同一个实体，并选出规范名称（canonical name）。

## 判断标准
- 同一个产品/模型的不同写法 → YES（例: "Claude5" = "Claude Sonnet 5" = "Sonnet5"）
- 版本号不同 → NO，除非社区混用（例: "GPT-5.5" ≠ "GPT-5.6"）
- 公司名 vs 产品名 → NO（例: "OpenAI" ≠ "ChatGPT"）
- GitHub 仓库名 vs 产品名 → 可能是同一个（例: "LangChain" = "langchain-ai/langchain"）
- 带版本后缀 → 看情况（例: "GPT-5.6 Luna" ≠ "GPT-5.6 Sol"，因为 Luna/Sol 是不同变体）

## Canonical 名称选择规则
1. 优先选官方全名（"Claude Sonnet 5" > "Claude5"）
2. 优先选无特殊字符的（"GPT-5.6" > "GPT 5.6"）
3. GitHub 仓库保留 owner/repo 格式
4. 大小写规范：每个单词首字母大写

## 返回格式
纯 JSON，不要 markdown 包裹:
{
  "groups": [
    {
      "canonical": "Claude Sonnet 5",
      "aliases": ["Claude5", "Sonnet5", "Claude Sonnet Five"],
      "is_same": true
    }
  ]
}

如果组内名称都不相同，返回:
{"groups": []}"""


def _cluster_to_components(pairs: list[tuple[int, int, float]], n: int) -> list[list[int]]:
    """Union-Find 将候选对聚为连通分量。"""
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    for i, j, _ in pairs:
        union(i, j)

    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(i)

    # 只返回 ≥2 个成员的组
    return [members for members in groups.values() if len(members) >= 2]


def _verify_clusters(
    clusters: list[list[int]],
    term_names: list[str],
    term_types: list[str],
) -> dict[str, dict]:
    """用 LLM 验证每个聚类，返回 canonical 映射。"""
    canonical_map: dict[str, dict] = {}  # lower_name → {canonical, aliases}

    for cluster in clusters:
        cluster_names = [term_names[i] for i in cluster]
        cluster_types = [term_types[i] for i in cluster]
        dominant_type = max(set(cluster_types), key=cluster_types.count)

        # 过滤：只处理同类型的（跨类型的不太可能是重复）
        unique_types = set(cluster_types)
        if len(unique_types) > 1:
            # 允许 project ↔ product 跨类型（如 LangChain 既是项目也是产品）
            allowed_cross = [{"project", "product"}, {"company", "product"}, {"model", "product"}]
            if unique_types not in [set(p) for p in allowed_cross]:
                continue

        if len(cluster_names) < 2:
            continue

        # 构建 prompt
        names_list = "\n".join(f"  - {n} (type: {t})" for n, t in zip(cluster_names, cluster_types))
        user_prompt = f"""判断以下 {len(cluster_names)} 个名称是否指向同一个实体。

候选名称：
{names_list}

请判断是否相同，并给出 canonical 名称。"""

        try:
            from scripts.llm_client import chat

            raw = chat(
                system_prompt=VERIFY_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=1024,
            )

            raw = raw.strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```\w*\n?", "", raw)
                raw = re.sub(r"\n```$", "", raw)

            result = json.loads(raw)
            groups = result.get("groups", [])

            for g in groups:
                if not g.get("is_same", False):
                    continue
                canonical = g.get("canonical", "").strip()
                aliases = g.get("aliases", [])
                if not canonical:
                    continue

                # 将所有变体（含 canonical）映射到 canonical
                for name in [canonical] + aliases:
                    canonical_map[name.lower()] = {
                        "canonical": canonical,
                        "aliases": [a for a in aliases if a.lower() != canonical.lower()],
                        "term_type": dominant_type,
                    }

        except json.JSONDecodeError as e:
            print(f"  [Norm] LLM 返回 JSON 解析失败: {e}")
        except Exception as e:
            print(f"  [Norm] LLM 调用失败: {e}")

    return canonical_map


# ── 主流程 ─────────────────────────────────────────────

def _load_canonical_table() -> dict:
    """加载已有的 canonical 表。"""
    if CANONICAL_PATH.exists():
        try:
            return json.loads(CANONICAL_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, KeyError):
            pass
    return {
        "_schema": "Term 归一化表 — canonical → aliases + 聚合统计",
        "_version": "1.0",
        "last_normalized": "",
        "canonicals": {},
    }


def _save_canonical_table(table: dict):
    """保存 canonical 表（原子写入，防崩溃损坏）。"""
    from scripts.defaults import atomic_write_json
    atomic_write_json(CANONICAL_PATH, table)


def _merge_statistics(term_index: dict, canonical_map: dict[str, dict]) -> dict:
    """将 term_index 中的统计合并到 canonical 名下。"""
    terms_db = term_index.get("terms", {})
    canonicals: dict[str, dict] = {}

    for term_name, entry in terms_db.items():
        key = term_name.lower()
        mapping = canonical_map.get(key)
        canonical_name = mapping["canonical"] if mapping else term_name
        is_alias = mapping is not None and canonical_name.lower() != key

        if canonical_name not in canonicals:
            canonicals[canonical_name] = {
                "first_seen": entry.get("first_seen", ""),
                "last_seen": entry.get("last_seen", ""),
                "term_type": entry.get("term_type", "unknown"),
                "aliases": [],
                "merged_terms": [],
                "appearances": 0,
                "distinct_days": set(),
                "distinct_sources": set(),
                "sources": {},
            }

        c = canonicals[canonical_name]

        # 别名列表
        if is_alias and term_name not in c["aliases"]:
            c["aliases"].append(term_name)

        # 合并来源
        if term_name not in c["merged_terms"]:
            c["merged_terms"].append(term_name)

        # 从 signals 数组直接计算聚合（term_index 不再预存储冗余聚合字段）
        signals = entry.get("signals", [])
        c["appearances"] += len(signals)
        for ref in signals:
            src = ref.get("source", "")
            c["sources"][src] = c["sources"].get(src, 0) + 1
            c["distinct_sources"].add(src)
            c["distinct_days"].add(ref.get("date", ""))

        # 更新时间范围
        if entry.get("first_seen", "") < c["first_seen"]:
            c["first_seen"] = entry["first_seen"]
        if entry.get("last_seen", "") > c["last_seen"]:
            c["last_seen"] = entry["last_seen"]

    # 转换 set → 可序列化
    result: dict[str, dict] = {}
    for name, c in canonicals.items():
        result[name] = {
            "first_seen": c["first_seen"],
            "last_seen": c["last_seen"],
            "term_type": c["term_type"],
            "aliases": sorted(set(c["aliases"])),
            "merged_terms": sorted(c["merged_terms"]),
            "appearances": c["appearances"],
            "distinct_days": len(c["distinct_days"]),
            "distinct_sources": len(c["distinct_sources"]),
            "sources": dict(sorted(c["sources"].items(), key=lambda x: -x[1])),
        }

    return result


def run(date_str: str | None = None):
    """执行归一化 pipeline。"""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")

    print(f"\n{'='*50}")
    print(f"[Norm] 第三层：Term 归一化 — {date}")
    print(f"{'='*50}")

    # Step 1: 加载 term_index
    if not TERM_INDEX_PATH.exists():
        print("[Norm] term_index.json 不存在，跳过")
        return

    term_index = json.loads(TERM_INDEX_PATH.read_text(encoding="utf-8"))
    terms_db = term_index.get("terms", {})
    if not terms_db:
        print("[Norm] term_index 为空，跳过")
        return

    term_names = list(terms_db.keys())
    term_types = [terms_db[n].get("term_type", "unknown") for n in term_names]
    print(f"[Norm] 加载 {len(term_names)} 个 terms")

    # Step 2: 加载已有 canonical 表
    canonical_table = _load_canonical_table()
    existing_canonicals = canonical_table.get("canonicals", {})
    print(f"[Norm] 已有 {len(existing_canonicals)} 个 canonical terms")

    # 排除已有 canonical 映射的 terms（已经归一化过的）
    # 构建 known alias → canonical 映射
    known_map: dict[str, str] = {}  # lower_alias → canonical
    for c_name, c_entry in existing_canonicals.items():
        for alias in c_entry.get("aliases", []):
            known_map[alias.lower()] = c_name

    # Step 3: 候选对生成
    pairs = _find_candidate_pairs(term_names)
    print(f"[Norm] 候选重复对: {len(pairs)} 对")

    if not pairs:
        print("[Norm] 无候选重复对，跳过 LLM 验证")
        return

    # Step 4: 聚类
    clusters = _cluster_to_components(pairs, len(term_names))
    # 过滤已归一化的
    new_clusters = []
    for cluster in clusters:
        # 如果簇中所有 term 都已经有 canonical 映射，跳过
        unmapped = [i for i in cluster if term_names[i].lower() not in known_map]
        if len(unmapped) >= 2:
            new_clusters.append(cluster)

    print(f"[Norm] 聚类: {len(clusters)} 组 → {len(new_clusters)} 组待 LLM 验证")
    for i, cluster in enumerate(new_clusters):
        names = [term_names[j] for j in cluster[:8]]
        print(f"  组{i+1}: {', '.join(names)}{'...' if len(cluster) > 8 else ''}")

    if not new_clusters:
        print("[Norm] 无新的待验证聚类")
        return

    # Step 5: LLM 验证
    print(f"\n[Norm] 正在调用 LLM 验证 {len(new_clusters)} 个聚类...")
    canonical_map = _verify_clusters(new_clusters, term_names, term_types)

    # 合并已有映射
    for alias_lower, c_name in known_map.items():
        if alias_lower not in canonical_map:
            # 从已有 canonical 表重建映射
            canonical_map[alias_lower] = {
                "canonical": c_name,
                "aliases": [],
                "term_type": existing_canonicals[c_name].get("term_type", "unknown"),
            }

    print(f"[Norm] LLM 返回 {len(canonical_map)} 个映射条目")

    # Step 6: 合并统计
    merged_canonicals = _merge_statistics(term_index, canonical_map)
    print(f"[Norm] 归一化后: {len(merged_canonicals)} 个 canonical terms")

    # Step 7: 保存
    # 7a. 更新 canonical_terms.json
    canonical_table["canonicals"] = merged_canonicals
    canonical_table["last_normalized"] = datetime.now(TZ_SHANGHAI).isoformat()
    canonical_table["total_canonicals"] = len(merged_canonicals)
    canonical_table["total_aliases"] = sum(
        len(c.get("aliases", [])) for c in merged_canonicals.values()
    )
    _save_canonical_table(canonical_table)

    # 7b. 更新 term_index 中每个 term 的 canonical_name
    for term_name in terms_db:
        mapping = canonical_map.get(term_name.lower())
        terms_db[term_name]["canonical_name"] = mapping["canonical"] if mapping else term_name

    term_index["last_updated"] = datetime.now(TZ_SHANGHAI).isoformat()
    term_index["_normalized"] = True
    from scripts.defaults import atomic_write_json
    atomic_write_json(TERM_INDEX_PATH, term_index)

    # Step 8: 打印归一化效果
    alias_count = sum(
        len(c.get("aliases", [])) for c in merged_canonicals.values()
    )
    print(f"\n[Norm] 归一化完成:")
    print(f"  原始 terms: {len(term_names)}")
    print(f"  Canonical terms: {len(merged_canonicals)}")
    print(f"  Aliases 合并: {alias_count}")
    if alias_count > 0:
        print(f"\n  合并示例:")
        for c_name, c_entry in sorted(merged_canonicals.items(), key=lambda x: -len(x[1].get("aliases", [])))[:5]:
            aliases = c_entry.get("aliases", [])
            if aliases:
                print(f"    {c_name} ← {', '.join(aliases)}")

    print(f"\n[Norm] canonical_terms.json → {CANONICAL_PATH}")

    return merged_canonicals


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    run(today)
