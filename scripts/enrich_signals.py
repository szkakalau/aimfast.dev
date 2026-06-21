"""
/last30days 社区语境丰富 — 对当日 Top 信号运行社区研究引擎
输入: daily/YYYY-MM-DD/signals.json
输出: daily/YYYY-MM-DD/enrichment.json + daily/YYYY-MM-DD/enrichment/*.md
"""
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DAILY_DIR = ROOT / "daily"
CONFIG_PATH = ROOT / "config.json"

TZ_SHANGHAI = timezone(timedelta(hours=8))

# ── 配置 ──────────────────────────────────────────────

def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_enrichment_config() -> dict:
    """读取 enrichment 配置段，缺失时返回安全默认值。"""
    cfg = load_config()
    ec = cfg.get("enrichment", {})
    return {
        "enabled": ec.get("enabled", True),
        "engine_path": ec.get("engine_path", "auto"),
        "python_path": ec.get("python_path", "auto"),
        "max_signals": ec.get("max_signals", 2),
        "min_score": ec.get("min_score", 20),
        "timeout_per_signal_s": ec.get("timeout_per_signal_s", 180),
        "max_items": ec.get("max_items", 15),
        "memory_dir": ec.get("memory_dir", str(Path.home() / "Documents" / "Last30Days")),
    }


# ── 引擎路径解析 ──────────────────────────────────────

def resolve_engine_path(config_engine_path: str) -> Path | None:
    """解析 last30days 引擎的 scripts/last30days.py 路径。"""
    # 如果用户显式指定了路径
    if config_engine_path and config_engine_path != "auto":
        expanded = Path(config_engine_path).expanduser().resolve()
        candidate = expanded / "skills" / "last30days" / "scripts" / "last30days.py"
        if candidate.exists():
            return candidate
        # 也尝试直接在指定路径下找
        direct = expanded / "scripts" / "last30days.py"
        if direct.exists():
            return direct

    # 自动发现：找最新版本的缓存插件
    cache_base = Path.home() / ".claude" / "plugins" / "cache" / "last30days-skill" / "last30days"
    if cache_base.exists():
        versions = sorted(
            [d for d in cache_base.iterdir() if d.is_dir()],
            reverse=True,
        )
        for ver_dir in versions:
            engine = ver_dir / "skills" / "last30days" / "scripts" / "last30days.py"
            if engine.exists():
                return engine

    return None


def resolve_python(config_python: str) -> str:
    """解析 Python 解释器路径。"""
    if config_python and config_python != "auto":
        return config_python
    # 使用当前运行脚本的 Python
    return sys.executable


# ── 话题提取 ──────────────────────────────────────────

def extract_topic(signal: dict) -> str:
    """从信号中提取适合 last30days 搜索的话题短语。"""
    title = signal.get("title", "")
    summary = signal.get("summary", "")

    # 去掉 GitHub owner/repo 前缀
    cleaned = title
    cleaned = re.sub(r"^[\w.-]+/[\w.-]+\s*[:：]?\s*", "", cleaned)

    # 去掉常见前缀
    cleaned = re.sub(
        r"^(Show HN|Ask HN|Launch HN|Tell HN)\s*[:：]\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    # 去掉末尾的来源标注
    cleaned = re.sub(r"\s*[（(][\d,.KkMm]+ (star|fork|赞|评论|分).*$", "", cleaned)
    cleaned = re.sub(r"\s*https?://\S+$", "", cleaned)

    # 取前 80 个字符作为搜索话题
    cleaned = cleaned.strip()
    if len(cleaned) > 80:
        # 在单词边界截断
        truncated = cleaned[:80]
        last_space = truncated.rfind(" ")
        if last_space > 40:
            cleaned = truncated[:last_space]
        else:
            cleaned = truncated

    # 如果清理后太短，尝试用 summary
    if len(cleaned) < 10 and summary:
        cleaned = summary[:80]

    return cleaned.strip()


def topic_to_slug(topic: str) -> str:
    """话题 → 文件名安全 slug。"""
    slug = topic.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    return slug[:60]


# ── 信号选择 ──────────────────────────────────────────

def select_top_signals(signals: list[dict], max_count: int, min_score: int) -> list[dict]:
    """选出需要富化的 Top 信号。"""
    # 按分数降序，过滤低分
    candidates = [
        s for s in signals
        if s.get("score", 0) >= min_score and not s.get("cooling", False)
    ]
    candidates.sort(key=lambda s: s.get("score", 0), reverse=True)

    # 按标题相似度去重（避免对同一话题跑多次）
    selected = []
    seen_topics = set()

    for sig in candidates:
        topic = extract_topic(sig)
        topic_lower = topic.lower()
        # 检查是否与已选话题高度重叠
        is_dup = False
        for seen in seen_topics:
            if _title_similarity(topic_lower, seen) > 0.75:
                is_dup = True
                break
        if not is_dup:
            selected.append(sig)
            seen_topics.add(topic_lower)
        if len(selected) >= max_count:
            break

    return selected


def _title_similarity(a: str, b: str) -> float:
    """简易 Jaccard 词级相似度。"""
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


# ── 引擎调用 ──────────────────────────────────────────

def run_engine(topic: str, engine_path: Path, python_path: str,
               output_dir: Path, timeout_s: int, max_items: int) -> dict:
    """调用 last30days 引擎，返回结果摘要。"""
    start = time.time()

    cmd = [
        python_path,
        str(engine_path),
        topic,
        "--emit=compact",
        "--auto-resolve",
        "--max-items", str(max_items),
        "--save-dir", str(output_dir),
        "--save-suffix=",
    ]

    # 设置环境变量
    env = {
        **dict(subprocess.os.environ),
        "LAST30DAYS_NATIVE_SEARCH": "0",  # 自动化模式不用 WebSearch
    }

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
            env=env,
            cwd=str(output_dir),
        )
        elapsed = time.time() - start
        stdout = result.stdout
        stderr = result.stderr
        success = result.returncode == 0
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        stdout = ""
        stderr = f"Timeout after {timeout_s}s"
        success = False
    except Exception as e:
        elapsed = time.time() - start
        stdout = ""
        stderr = str(e)
        success = False

    # 解析引擎输出提取 stats（stdout 可能为 None 当引擎崩溃时）
    stdout = stdout or ""
    sources_found = _parse_source_counts(stdout)
    total_items = sum(sources_found.values())
    top_voices = _parse_top_voices(stdout)
    summary_brief = _extract_summary_brief(stdout)

    return {
        "success": success,
        "elapsed_s": round(elapsed, 1),
        "sources_found": sources_found,
        "total_items": total_items,
        "top_voices": top_voices,
        "summary_brief": summary_brief,
        "stdout": stdout,
        "stderr": stderr,
    }


def _parse_source_counts(output: str) -> dict[str, int]:
    """从引擎输出中提取各源条目数。"""
    counts = {}
    # 匹配 "├─ 🟠 Reddit: 4 threads" 等行
    pattern = r"[├└]─\s+\S+\s+(\w+):\s+(\d+)"
    for match in re.finditer(pattern, output):
        source = match.group(1).lower()
        count = int(match.group(2))
        counts[source] = count
    return counts


def _parse_top_voices(output: str) -> list[str]:
    """从引擎输出中提取 Top voices。"""
    pattern = r"Top voices:\s*(.+?)$"
    match = re.search(pattern, output, re.MULTILINE)
    if match:
        return [v.strip() for v in match.group(1).split(",")[:5]]
    return []


def _extract_summary_brief(output: str) -> str:
    """从引擎 compact 输出中提取简要摘要。"""
    # 尝试找 stats 行作为摘要
    lines = output.strip().split("\n")
    brief_parts = []
    for line in lines:
        if "threads" in line.lower() or "stories" in line.lower() or "items" in line.lower():
            brief_parts.append(line.strip())
        if "sources:" in line.lower() or "active" in line.lower():
            brief_parts.append(line.strip())
    if brief_parts:
        return " | ".join(brief_parts[:3])
    # 回退：取第一行非标记内容
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("🌐"):
            return line[:200]
    return ""


# ── 保存输出 ──────────────────────────────────────────

def save_enrichment_output(
    date_str: str,
    signal: dict,
    topic: str,
    result: dict,
    enrichment_dir: Path,
) -> Path | None:
    """保存引擎 raw markdown 到 enrichment 目录。返回文件路径。"""
    slug = topic_to_slug(topic)
    enrichment_dir.mkdir(parents=True, exist_ok=True)

    # 保存 raw markdown
    raw_file = enrichment_dir / f"{slug}.md"
    header = (
        f"# /last30days Enrichment: {topic}\n"
        f"Signal: {signal.get('title', 'N/A')} (score: {signal.get('score', 'N/A')})\n"
        f"Date: {date_str} | Engine elapsed: {result['elapsed_s']}s\n\n"
    )
    raw_file.write_text(header + result["stdout"], encoding="utf-8")

    return raw_file


# ── 主入口 ────────────────────────────────────────────

def run(date_str: str | None = None):
    """对当日 Top 信号运行 last30days 社区研究。"""
    ec = get_enrichment_config()
    if not ec["enabled"]:
        print("[enrich] disabled in config, skip")
        _write_status(date_str, "skipped", "disabled_in_config")
        return

    # 解析引擎路径
    engine_path = resolve_engine_path(ec["engine_path"])
    if engine_path is None:
        print("[enrich] last30days engine not found — skip enrichment")
        _write_status(date_str, "skipped", "engine_not_found")
        return

    python_path = resolve_python(ec["python_path"])
    print(f"[enrich] engine: {engine_path}")
    print(f"[enrich] python: {python_path}")

    # 读取当日信号
    if date_str is None:
        date_str = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")

    signals_path = DAILY_DIR / date_str / "signals.json"
    if not signals_path.exists():
        print(f"[enrich] no signals.json for {date_str}, skip")
        _write_status(date_str, "skipped", "no_signals_data")
        return

    with open(signals_path, "r", encoding="utf-8") as f:
        signals_data = json.load(f)

    all_signals = signals_data.get("signals", [])
    if not all_signals:
        print("[enrich] empty signals array, skip")
        _write_status(date_str, "skipped", "empty_signals")
        return

    # 选择 Top 信号
    selected = select_top_signals(all_signals, ec["max_signals"], ec["min_score"])
    if not selected:
        print(f"[enrich] no signals meet min_score={ec['min_score']}, skip")
        _write_status(date_str, "skipped", "no_qualified_signals")
        return

    print(f"[enrich] {len(selected)} signals selected for enrichment")

    # 准备输出目录
    enrichment_dir = DAILY_DIR / date_str / "enrichment"
    enrichment_dir.mkdir(parents=True, exist_ok=True)

    # 逐信号运行引擎
    items = _enrich_signals(selected, enrichment_dir, date_str, engine_path, python_path, ec)

    # 写入 enrichment.json
    enrichment_data = {
        "date": date_str,
        "enriched_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "config": {
            "max_signals": ec["max_signals"],
            "min_score": ec["min_score"],
        },
        "signals_enriched": len(items),
        "items": items,
    }

    output_path = DAILY_DIR / date_str / "enrichment.json"
    output_path.write_text(
        json.dumps(enrichment_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    total_items = sum(it["total_items"] for it in items)
    _write_status(
        date_str, "generated",
        message=f"Enriched {len(items)} signals, {total_items} community items found",
    )

    print(f"[enrich] done — {len(items)} signals enriched → {output_path}")


def _enrich_signals(selected: list[dict], output_dir: Path, date_str: str,
                    engine_path: Path, python_path: str, ec: dict) -> list[dict]:
    """对一批信号运行引擎，返回 item 列表。"""
    items = []
    for i, sig in enumerate(selected):
        topic = extract_topic(sig)
        print(f"[enrich] [{i+1}/{len(selected)}] researching: {topic}")

        result = run_engine(
            topic=topic,
            engine_path=engine_path,
            python_path=python_path,
            output_dir=output_dir,
            timeout_s=ec["timeout_per_signal_s"],
            max_items=ec["max_items"],
        )

        raw_file = save_enrichment_output(date_str, sig, topic, result, output_dir)

        item = {
            "signal_id": sig.get("id", ""),
            "signal_title": sig.get("title", ""),
            "topic": topic,
            "score": sig.get("score", 0),
            "engine_success": result["success"],
            "engine_elapsed_s": result["elapsed_s"],
            "sources_found": result["sources_found"],
            "total_items": result["total_items"],
            "top_voices": result["top_voices"],
            "summary_brief": result["summary_brief"],
            "raw_file": str(raw_file.relative_to(ROOT)) if raw_file else "",
        }
        items.append(item)

        if not result["success"]:
            print(f"[enrich]   engine failed: {result['stderr'][:200]}")

    return items


# ── 周度深度回溯 ───────────────────────────────────────

def collect_weekly_top_topic(date_str: str, min_score: int = 15) -> dict | None:
    """扫描过去 7 天信号，找到本周最热话题。

    返回 {topic, signals, total_score, days_present, representative} 或 None。
    """
    today = datetime.strptime(date_str, "%Y-%m-%d")
    all_week_signals: list[dict] = []

    for i in range(7):
        d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        sp = DAILY_DIR / d / "signals.json"
        if not sp.exists():
            continue
        try:
            data = json.loads(sp.read_text(encoding="utf-8"))
            for s in data.get("signals", []):
                if s.get("score", 0) >= min_score and not s.get("cooling", False):
                    s["_day"] = d
                    all_week_signals.append(s)
        except (json.JSONDecodeError, OSError):
            continue

    if not all_week_signals:
        return None

    # 按话题聚类（Jaccard 标题相似度 > 0.5）
    clusters: list[list[dict]] = []
    assigned = [False] * len(all_week_signals)

    for i, sig in enumerate(all_week_signals):
        if assigned[i]:
            continue
        cluster = [sig]
        assigned[i] = True
        ti = extract_topic(sig).lower()
        for j in range(i + 1, len(all_week_signals)):
            if assigned[j]:
                continue
            tj = extract_topic(all_week_signals[j]).lower()
            if _title_similarity(ti, tj) > 0.5:
                cluster.append(all_week_signals[j])
                assigned[j] = True
        clusters.append(cluster)

    if not clusters:
        return None

    # 评分：聚合分数 × 出现天数 bonus
    def cluster_weight(cluster: list[dict]) -> float:
        total_score = sum(s.get("score", 0) for s in cluster)
        days = len(set(s.get("_day", "") for s in cluster))
        return total_score * (1 + 0.3 * min(days, 5))  # 最多 2.5x bonus

    clusters.sort(key=cluster_weight, reverse=True)
    best = clusters[0]
    rep = max(best, key=lambda s: s.get("score", 0))

    return {
        "topic": extract_topic(rep),
        "signal_count": len(best),
        "total_score": sum(s.get("score", 0) for s in best),
        "days_present": len(set(s.get("_day", "") for s in best)),
        "representative": rep,
        "all_in_cluster": best,
    }


def run_weekly(date_str: str | None = None):
    """周日触发：对本周最热话题做 30 天深度社区回溯。"""
    ec = get_enrichment_config()
    if not ec["enabled"]:
        print("[enrich-weekly] disabled in config, skip")
        return

    engine_path = resolve_engine_path(ec["engine_path"])
    if engine_path is None:
        print("[enrich-weekly] engine not found, skip")
        return

    python_path = resolve_python(ec["python_path"])

    if date_str is None:
        date_str = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")

    today = datetime.strptime(date_str, "%Y-%m-%d")
    iso = today.isocalendar()
    week_label = f"{today.year}-W{iso.week:02d}"

    print(f"\n{'='*50}")
    print(f"[enrich-weekly] 周度社区深度回溯 — {week_label}")
    print(f"{'='*50}")

    # 找到本周最热话题
    top = collect_weekly_top_topic(date_str, min_score=ec["min_score"])
    if top is None:
        print("[enrich-weekly] no qualified signals this week, skip")
        return

    print(f"[enrich-weekly] 话题: {top['topic']}")
    print(f"[enrich-weekly] 信号数: {top['signal_count']} 条（{top['days_present']} 天出现）")
    print(f"[enrich-weekly] 聚合分数: {top['total_score']}")

    # 用 30 天窗口深度搜索
    weekly_dir = ROOT / "weekly"
    weekly_dir.mkdir(parents=True, exist_ok=True)

    # 更长的超时（30 天回溯数据量更大）
    weekly_timeout = ec["timeout_per_signal_s"] * 2

    print(f"[enrich-weekly] running 30-day deep dive (timeout: {weekly_timeout}s)...")

    result = run_engine(
        topic=top["topic"],
        engine_path=engine_path,
        python_path=python_path,
        output_dir=weekly_dir,
        timeout_s=weekly_timeout,
        max_items=min(ec["max_items"] * 2, 30),
    )

    # 额外加 --days=30 参数再跑一次（更广的时间窗口）
    cmd_30d = [
        python_path,
        str(engine_path),
        top["topic"],
        "--emit=compact",
        "--auto-resolve",
        "--days=30",
        "--max-items", str(min(ec["max_items"] * 2, 30)),
        "--save-dir", str(weekly_dir),
        "--save-suffix=",
    ]
    env = {**dict(subprocess.os.environ), "LAST30DAYS_NATIVE_SEARCH": "0"}

    start = time.time()
    try:
        proc = subprocess.run(
            cmd_30d,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=weekly_timeout,
            env=env,
            cwd=str(weekly_dir),
        )
        result_30d = {
            "success": proc.returncode == 0,
            "elapsed_s": round(time.time() - start, 1),
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
        }
    except subprocess.TimeoutExpired:
        result_30d = {"success": False, "elapsed_s": weekly_timeout, "stdout": "", "stderr": "Timeout"}
    except Exception as e:
        result_30d = {"success": False, "elapsed_s": 0, "stdout": "", "stderr": str(e)}

    stdout_30d = result_30d["stdout"] or ""
    sources_30d = _parse_source_counts(stdout_30d)
    voices_30d = _parse_top_voices(stdout_30d)

    # 保存 raw markdown
    raw_file = weekly_dir / f"{week_label}-enrichment.md"
    header = (
        f"# /last30days Weekly Deep-Dive: {top['topic']}\n"
        f"Week: {week_label} | Date: {date_str}\n"
        f"Signals this week: {top['signal_count']} across {top['days_present']} days | "
        f"Aggregate score: {top['total_score']}\n"
        f"Engine elapsed: {result_30d['elapsed_s']}s\n\n"
    )
    raw_file.write_text(header + stdout_30d, encoding="utf-8")

    # 写入结构化 JSON
    weekly_data = {
        "week": week_label,
        "date": date_str,
        "enriched_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "topic": top["topic"],
        "week_stats": {
            "signal_count": top["signal_count"],
            "days_present": top["days_present"],
            "aggregate_score": top["total_score"],
            "representative_signal": {
                "id": top["representative"].get("id", ""),
                "title": top["representative"].get("title", ""),
                "score": top["representative"].get("score", 0),
                "source": top["representative"].get("source", ""),
            },
        },
        "research_30d": {
            "engine_success": result_30d["success"],
            "elapsed_s": result_30d["elapsed_s"],
            "sources_found": sources_30d,
            "total_items": sum(sources_30d.values()),
            "top_voices": voices_30d,
        },
        "raw_file": str(raw_file.relative_to(ROOT)),
    }

    weekly_json_path = weekly_dir / f"{week_label}-enrichment.json"
    weekly_json_path.write_text(
        json.dumps(weekly_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[enrich-weekly] 30-day research: {sum(sources_30d.values())} items across "
          f"{list(sources_30d.keys())}")
    print(f"[enrich-weekly] saved → {raw_file}")
    print(f"[enrich-weekly] saved → {weekly_json_path}")


def _write_status(date_str: str | None, status: str, reason: str = "",
                  message: str = ""):
    """写入 pipeline 状态。"""
    from scripts.pipeline_status import write
    if date_str is None:
        date_str = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    write(date_str, "enrichment", status, reason=reason, message=message)


# ── CLI 入口 ──────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Enrich daily signals with /last30days community research")
    parser.add_argument("--date", type=str, default=None, help="Date in YYYY-MM-DD format")
    parser.add_argument("--weekly", action="store_true", help="Run weekly 30-day deep-dive mode")
    args = parser.parse_args()
    if args.weekly:
        run_weekly(date_str=args.date)
    else:
        run(date_str=args.date)
