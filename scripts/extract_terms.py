"""
第二层：命名实体提取 + 跨源 Term 数据库
──────────────────────────────────────────
从每日 raw 信号中用 LLM 提取产品名、技术名、公司名、模型名，
然后写入累积 term_index，自动统计每个 term 的跨源出现次数。

输入: raw/{date}/*.json (原始信号)
输出:
  - daily/{date}/terms.json      — 当日提取的 terms
  - tracking/term_index.json     — 累积 term 数据库（跨日期增长）

设计原则:
  1. 一次 LLM 调用处理全天所有信号的 title + summary（批处理，省 token）
  2. 自动与历史 term_index 合并，累积统计
  3. 跨源计数 = 同一个 term 出现在 ≥2 个不同 source_key → cross_source_count
  4. 预算感知：单次调用 ~5-10K tokens，不超出月度预算
"""
import json
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"
DAILY_DIR = ROOT / "daily"
TRACKING_DIR = ROOT / "tracking"
CONFIG_PATH = ROOT / "config.json"

TZ_SHANGHAI = timezone(timedelta(hours=8))
TERM_INDEX_PATH = TRACKING_DIR / "term_index.json"

# ── LLM Prompt ─────────────────────────────────────────

SYSTEM_PROMPT = """你是一个技术情报命名实体提取器。你的任务是从一批信号标题中提取所有值得追踪的命名实体。

## 提取规则

提取以下类型的实体（只提取有明确名称的，不要提取泛化描述）：

1. **产品名** (product): 具体产品、SaaS 工具、App 的名称
   例: "Claude Code", "ChatGPT", "Vercel", "Notion", "Figma", "Supabase"

2. **技术/框架** (technology): 编程语言、框架、协议、架构模式
   例: "Rust", "WebAssembly", "RAG", "Kubernetes", "GraphQL", "WebGPU"

3. **公司/组织** (company): 公司名、开源组织
   例: "Anthropic", "OpenAI", "Google", "Meta", "Cloudflare", "HuggingFace"

4. **模型/AI** (model): AI 模型名、API 名
   例: "Claude 4", "GPT-5", "Gemini", "Stable Diffusion", "Llama 4"

5. **项目/仓库** (project): 开源项目名、GitHub 仓库名（保留 owner/repo 格式）
   例: "continuedev/continue", "langchain-ai/langchain", "mastra-ai/mastra"

## 禁止提取

- 不要提取泛化词: "AI", "API", "SaaS", "tool", "app", "platform"
- 不要提取纯描述性短语: "new product launch", "open source tool"
- 不要提取作者名或个人 ID（除非是知名人物如 "Sam Altman", "Karpathy"）
- 不要从 Reddit 子版块名、域名中提取

## 归一化规则

- 大小写统一: "claude code" → "Claude Code"
- 同义词合并: "Vercel AI SDK" 和 "Vercel AI" → 选最完整的那个
- 去掉前后空格和多余标点
- 英文首字母大写

## 返回格式

纯 JSON，不要 markdown 包裹，不要额外文字:
{
  "terms": [
    {
      "term": "Claude Science",
      "term_type": "product",
      "mentioned_in": ["signal-id-1", "signal-id-2"]
    }
  ]
}

如果一个信号都没提到，返回 {"terms": []}"""


def _load_daily_signals(date_str: str) -> list[dict]:
    """Fallback: 从 daily/{date}/signals.json 加载已处理的信号。"""
    daily_path = DAILY_DIR / date_str / "signals.json"
    if not daily_path.exists():
        print(f"[TermExtract] {daily_path} 也不存在 — 无信号可处理")
        return []

    signals: list[dict] = []
    try:
        data = json.loads(daily_path.read_text(encoding="utf-8"))
        for s in data.get("signals", []):
            signals.append({
                "id": s.get("id", ""),
                "title": s.get("title", ""),
                "summary": s.get("summary", "")[:200],
                "source": s.get("source", ""),
                "source_key": s.get("source_key", ""),
                "url": s.get("url", ""),
            })
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[TermExtract] 读取 {daily_path} 失败: {e}")

    print(f"[TermExtract] [fallback: daily/] 加载 {len(signals)} 条信号")
    return signals


def _load_raw_signals(date_str: str) -> list[dict]:
    """加载当日所有原始信号（标题 + 摘要 + ID + 来源）。

    优先从 raw/{date}/ 读取（CI 环境），不存在时 fallback 到 daily/{date}/signals.json。
    """
    raw_path = RAW_DIR / date_str
    if not raw_path.exists():
        print(f"[TermExtract] {raw_path} 不存在 → fallback 到 daily/{date_str}/signals.json")
        return _load_daily_signals(date_str)

    signals: list[dict] = []
    for f in sorted(raw_path.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            for s in data.get("signals", []):
                signals.append({
                    "id": s.get("id", ""),
                    "title": s.get("title", ""),
                    "summary": s.get("summary", "")[:200],
                    "source": s.get("source", ""),
                    "source_key": s.get("source_key", ""),
                    "url": s.get("url", ""),
                })
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[TermExtract] 读取 {f.name} 失败: {e}")

    if signals:
        print(f"[TermExtract] 加载 {len(signals)} 条原始信号")
    else:
        print(f"[TermExtract] raw/{date_str}/ 为空 → fallback 到 daily/{date_str}/signals.json")
        return _load_daily_signals(date_str)

    return signals


def _build_llm_prompt(signals: list[dict]) -> str:
    """构建发给 LLM 的信号列表。"""
    from scripts.defaults import sanitize_for_llm

    lines = ["以下是从多个平台采集的技术信号标题和摘要。请从中提取所有值得追踪的命名实体。\n"]
    lines.append(f"共 {len(signals)} 条信号：\n")

    for i, s in enumerate(signals):
        sid = s["id"]
        src = s["source"]
        title = sanitize_for_llm(s["title"][:150], strip_markdown=True)
        summary = sanitize_for_llm((s["summary"] or "")[:120], strip_markdown=True)
        lines.append(f"[{sid}] [{src}] {title}")
        if summary and summary != title[:120]:
            lines.append(f"    摘要: {summary}")
        lines.append("")

    return "\n".join(lines)


def _call_llm_extract(signals: list[dict]) -> list[dict]:
    """批量 LLM 调用提取所有命名实体。

    当信号数过多（>200 条）时自动分批处理，避免 LLM 响应截断。
    每批 ~200 条信号，合并去重返回。
    """
    if len(signals) == 0:
        return []

    BATCH_SIZE = 200
    all_terms: list[dict] = []

    for batch_idx in range(0, len(signals), BATCH_SIZE):
        batch = signals[batch_idx:batch_idx + BATCH_SIZE]
        batch_num = batch_idx // BATCH_SIZE + 1
        total_batches = (len(signals) + BATCH_SIZE - 1) // BATCH_SIZE

        if total_batches > 1:
            print(f"[TermExtract] 批处理 {batch_num}/{total_batches}: {len(batch)} 条信号")

        user_prompt = _build_llm_prompt(batch)

        try:
            from scripts.llm_client import chat

            raw = chat(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=8192,
            )

            # 防御性解析: 移除可能的 markdown 包裹
            raw = raw.strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```\w*\n?", "", raw)
                raw = re.sub(r"\n```$", "", raw)

            result = json.loads(raw)
            batch_terms = result.get("terms", [])
            print(f"[TermExtract] 批次 {batch_num}: LLM 提取 {len(batch_terms)} 个命名实体")
            all_terms.extend(batch_terms)

        except json.JSONDecodeError as e:
            print(f"[TermExtract] 批次 {batch_num}: LLM 返回 JSON 解析失败: {e}")
            print(f"  原始响应前 200 字符: {raw[:200] if 'raw' in dir() else 'N/A'}")
        except Exception as e:
            print(f"[TermExtract] 批次 {batch_num}: LLM 调用失败: {e}")

    # 批间去重（按 term 名）
    seen: set[str] = set()
    unique_terms: list[dict] = []
    for t in all_terms:
        term_name = t.get("term", "").strip().lower()
        if term_name and term_name not in seen:
            seen.add(term_name)
            unique_terms.append(t)
        elif term_name:
            # 合并 mentioned_in
            for existing in unique_terms:
                if existing.get("term", "").strip().lower() == term_name:
                    existing_ids = set(existing.get("mentioned_in", []))
                    for mid in t.get("mentioned_in", []):
                        if mid not in existing_ids:
                            existing.setdefault("mentioned_in", []).append(mid)
                            existing_ids.add(mid)
                    break

    print(f"[TermExtract] 总共提取 {len(unique_terms)} 个命名实体（{len(all_terms)} → 去重 {len(unique_terms)}）")
    return unique_terms


def _load_term_index() -> dict:
    """加载累积 term_index。"""
    if TERM_INDEX_PATH.exists():
        try:
            return json.loads(TERM_INDEX_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, KeyError):
            pass
    return {
        "_schema": "跨源 Term 数据库 — 从每日信号中累积提取的命名实体",
        "_version": "1.0",
        "last_updated": "",
        "total_terms": 0,
        "terms": {},
    }


def _save_term_index(index: dict):
    """保存累积 term_index（原子写入，防崩溃损坏）。"""
    from scripts.defaults import atomic_write_json
    atomic_write_json(TERM_INDEX_PATH, index)


def _build_signal_map(signals: list[dict]) -> dict[str, dict]:
    """构建 signal_id → signal info 的快速映射。"""
    smap: dict[str, dict] = {}
    for s in signals:
        smap[s["id"]] = s
    return smap


def merge_terms(
    new_terms: list[dict],
    signal_map: dict[str, dict],
    date_str: str,
    existing_index: dict,
) -> dict:
    """将新提取的 terms 合并到累积 index 中。"""
    terms_db = existing_index.get("terms", {})
    today = date_str

    merged_count = 0
    new_count = 0

    for t in new_terms:
        term_name = t.get("term", "").strip()
        if not term_name or len(term_name) < 3:
            continue

        term_type = t.get("term_type", "unknown")
        mentioned_ids = t.get("mentioned_in", [])

        if not isinstance(mentioned_ids, list):
            mentioned_ids = []

        # Resolve signal info for each mentioned ID
        sources: dict[str, int] = {}
        signal_refs: list[dict] = []
        for sid in mentioned_ids:
            if sid in signal_map:
                si = signal_map[sid]
                src = si["source"]
                sources[src] = sources.get(src, 0) + 1
                signal_refs.append({
                    "date": date_str,
                    "source": src,
                    "source_key": si.get("source_key", ""),
                    "title": si["title"][:120],
                    "signal_id": sid,
                })

        if not signal_refs:
            continue

        # Check if term already exists
        key = term_name.lower()  # case-insensitive key
        existing_entry = None
        existing_key = None
        for ek, ev in terms_db.items():
            if ek.lower() == key:
                existing_entry = ev
                existing_key = ek
                break

        if existing_entry:
            # 只追加原始 signals（聚合统计由 normalize_terms → canonical_terms 统一计算）
            existing_entry["last_seen"] = today
            existing_ids = {r.get("signal_id", "") for r in existing_entry.get("signals", [])}
            for ref in signal_refs:
                if ref["signal_id"] not in existing_ids:
                    existing_entry.setdefault("signals", []).append(ref)
                    existing_ids.add(ref["signal_id"])
            # 裁剪：每个 term 只保留最近 90 天的详细信号记录
            cutoff = (datetime.now(TZ_SHANGHAI) - timedelta(days=90)).strftime("%Y-%m-%d")
            existing_entry["signals"] = [
                r for r in existing_entry.get("signals", [])
                if r.get("date", "") >= cutoff
            ]
            merged_count += 1
        else:
            # 新 term — 只存原始数据，不预计算聚合
            terms_db[term_name] = {
                "first_seen": today,
                "last_seen": today,
                "term_type": term_type,
                "signals": signal_refs,
            }
            new_count += 1

    existing_index["terms"] = terms_db
    existing_index["total_terms"] = len(terms_db)
    existing_index["last_updated"] = datetime.now(TZ_SHANGHAI).isoformat()

    print(f"[TermExtract] 合并: {new_count} 个新 term, {merged_count} 个合并到已有 term")
    print(f"[TermExtract] term_index 总计: {len(terms_db)} 个命名实体")
    return existing_index


def run(date_str: str | None = None):
    """执行完整 term 提取 pipeline。"""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")

    print(f"\n{'='*50}")
    print(f"[TermExtract] 第二层：命名实体提取 — {date}")
    print(f"{'='*50}")

    # Step 1: 加载原始信号
    signals = _load_raw_signals(date)
    if not signals:
        print("[TermExtract] 无信号，跳过")
        return

    # Step 2: LLM 提取命名实体
    start = time.time()
    new_terms = _call_llm_extract(signals)
    elapsed = time.time() - start
    print(f"[TermExtract] LLM 提取耗时: {elapsed:.1f}s")

    if not new_terms:
        print("[TermExtract] 未提取到任何命名实体 — 保存空结果")
        # 仍然保存当天空文件，标记已处理
        output_dir = DAILY_DIR / date
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "terms.json").write_text(
            json.dumps({"date": date, "terms": [], "note": "LLM 未提取到任何实体"}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return

    # Step 3: 构建 signal 映射
    signal_map = _build_signal_map(signals)

    # Step 4: 保存当日 terms
    output_dir = DAILY_DIR / date
    output_dir.mkdir(parents=True, exist_ok=True)
    today_output = {
        "date": date,
        "extracted_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "signal_count": len(signals),
        "term_count": len(new_terms),
        "terms": new_terms,
    }
    (output_dir / "terms.json").write_text(
        json.dumps(today_output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[TermExtract] 当日 terms → {output_dir / 'terms.json'}")

    # Step 5: 合并到累积 term_index
    existing_index = _load_term_index()
    merged_index = merge_terms(new_terms, signal_map, date, existing_index)
    _save_term_index(merged_index)

    # Step 6: 打印跨源验证统计
    cross_source_terms = [
        (name, entry) for name, entry in merged_index["terms"].items()
        if entry.get("distinct_sources", 0) >= 2
    ]
    cross_source_terms.sort(key=lambda x: x[1]["distinct_sources"], reverse=True)

    print(f"\n[TermExtract] 跨源验证的 terms（≥2 个独立源）: {len(cross_source_terms)} 个")
    for name, entry in cross_source_terms[:15]:
        sources_str = ", ".join(
            f"{s}({c})" for s, c in sorted(entry["sources"].items(), key=lambda x: -x[1])[:4]
        )
        print(f"  [{entry['distinct_sources']}源/{entry['appearances']}次] {name}  ← {sources_str}")
    if len(cross_source_terms) > 15:
        print(f"  ... 还有 {len(cross_source_terms) - 15} 个")

    print(f"\n[TermExtract] term_index → {TERM_INDEX_PATH}")
    return merged_index


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    run(today)
