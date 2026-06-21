"""
X/Twitter 信号采集器
使用 last30days 引擎的 bird_x 模块搜索 X 上的技术讨论
认证: ~/.config/last30days/.env 中的 AUTH_TOKEN + CT0
"""
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"
CONFIG_PATH = ROOT / "config.json"

TZ_SHANGHAI = timezone(timedelta(hours=8))

# 每日搜索话题 — 覆盖独立开发者关注的技术领域
DAILY_QUERIES = [
    "AI agent developer tool launch",
    "open source dev tool shipping",
    "indie hacker SaaS launch",
    "Claude Code Cursor Copilot AI coding",
    "YC startup launch product",
]


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_x_config() -> dict | None:
    """检查 X 认证是否就绪。"""
    env_path = Path.home() / ".config" / "last30days" / ".env"
    if not env_path.exists():
        return None

    auth_token = None
    ct0 = None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("AUTH_TOKEN="):
            auth_token = line.split("=", 1)[1].strip()
        elif line.startswith("CT0="):
            ct0 = line.split("=", 1)[1].strip()

    if auth_token and ct0:
        return {"AUTH_TOKEN": auth_token, "CT0": ct0}

    # 也检查 XAI_API_KEY 和 XQUIK_API_KEY
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("XAI_API_KEY="):
            return {"XAI_API_KEY": line.split("=", 1)[1].strip()}
        if line.startswith("XQUIK_API_KEY="):
            return {"XQUIK_API_KEY": line.split("=", 1)[1].strip()}

    return None


def resolve_engine_and_python() -> tuple[Path | None, str]:
    """解析 last30days 引擎路径和 Python。"""
    cache_base = Path.home() / ".claude" / "plugins" / "cache" / "last30days-skill" / "last30days"
    engine = None
    if cache_base.exists():
        for ver_dir in sorted([d for d in cache_base.iterdir() if d.is_dir()], reverse=True):
            candidate = ver_dir / "skills" / "last30days" / "scripts" / "last30days.py"
            if candidate.exists():
                engine = candidate
                break
    return engine, sys.executable


def search_x(topic: str, engine_path: Path, python_path: str,
             x_creds: dict, timeout_s: int = 120) -> list[dict]:
    """用 last30days 引擎搜索 X，返回信号列表。"""
    start = time.time()
    env = {
        **dict(os.environ),
        "LAST30DAYS_NATIVE_SEARCH": "0",
    }
    # 注入 X 认证
    if "AUTH_TOKEN" in x_creds:
        env["AUTH_TOKEN"] = x_creds["AUTH_TOKEN"]
        env["CT0"] = x_creds.get("CT0", "")
    elif "XAI_API_KEY" in x_creds:
        env["XAI_API_KEY"] = x_creds["XAI_API_KEY"]
    elif "XQUIK_API_KEY" in x_creds:
        env["XQUIK_API_KEY"] = x_creds["XQUIK_API_KEY"]

    cmd = [
        python_path, str(engine_path), topic,
        "--emit=compact",
        "--search=x",          # 只搜 X
        "--auto-resolve",
        "--max-items", "20",
        "--save-suffix=",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
            env=env,
        )
        stdout = result.stdout or ""
    except subprocess.TimeoutExpired:
        print(f"[X] timeout searching '{topic}'")
        return []
    except Exception as e:
        print(f"[X] engine error: {e}")
        return []

    elapsed = time.time() - start
    signals = _parse_x_items(stdout, topic)
    print(f"[X] '{topic}' → {len(signals)} items ({elapsed:.1f}s)")
    return signals


def _parse_x_items(output: str, query: str) -> list[dict]:
    """从引擎 compact 输出中提取 X 条目为 pipeline 信号。"""
    signals = []
    # 匹配 X 条目: 1. [x] Title (score N, ...)
    # 或带链接的格式
    in_x_section = False
    current_item = {}

    for line in output.split("\n"):
        line_stripped = line.strip()

        # 检测 X 区块开始
        if re.match(r"^##\s+X\b", line_stripped, re.IGNORECASE):
            in_x_section = True
            continue
        elif re.match(r"^##\s+", line_stripped) and in_x_section:
            in_x_section = False
            continue

        if not in_x_section:
            continue

        # 匹配条目: "N. [x] Title (score N, M items, sources: X)"
        m = re.match(
            r"^\d+\.\s+\[x\]\s+(.+?)\s+\(score\s+(\d+).*?\)\s*$",
            line_stripped,
        )
        if m:
            if current_item and current_item.get("title"):
                signals.append(_to_signal(current_item, query))
            current_item = {"title": m.group(1).strip(), "score": int(m.group(2))}
            continue

        # 匹配 URL
        url_m = re.search(r"URL:\s*(https?://(?:x\.com|twitter\.com)/\S+)", line_stripped)
        if url_m and current_item:
            current_item["url"] = url_m.group(1).strip()
            continue

        # 匹配 evidence 摘录
        if line_stripped.startswith("- Evidence:") and current_item:
            current_item["summary"] = line_stripped.replace("- Evidence:", "").strip()[:200]
            continue

        # 匹配日期和互动数据
        eng_m = re.search(
            r"(\d{4}-\d{2}-\d{2}).*?\[(\d+)\s*(?:likes|like)",
            line_stripped,
        )
        if eng_m and current_item:
            current_item["raw_created_at"] = eng_m.group(1)
            try:
                current_item["engagement"] = {"likes": int(eng_m.group(2)), "total": int(eng_m.group(2))}
            except (ValueError, IndexError):
                pass
            continue

        # 匹配 @handle
        handle_m = re.search(r"@(\w+)", line_stripped)
        if handle_m and current_item and "author" not in current_item:
            current_item["author"] = handle_m.group(1)

    # 保存最后一个
    if current_item and current_item.get("title"):
        signals.append(_to_signal(current_item, query))

    return signals


def _to_signal(item: dict, query: str) -> dict:
    """转为标准 pipeline 信号格式。"""
    title = item.get("title", query)[:200]
    url = item.get("url", "")
    engagement = item.get("engagement", {"likes": 0, "total": 0})
    likes = engagement.get("likes", 0)

    signal_id = f"x-{abs(hash(url or title)) % 10_000_000:07d}"

    return {
        "id": signal_id,
        "title": title,
        "url": url,
        "source": "X/Twitter",
        "source_key": "x",
        "signal_type": "post",
        "discussion_count": likes,
        "engagement": engagement,
        "collected_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "raw_created_at": item.get("raw_created_at", ""),
        "summary": item.get("summary", title)[:200],
        "tags": ["x", "tech"],
        "author": item.get("author", ""),
    }


def collect(date_str: str | None = None) -> list[dict]:
    """采集 X 上当日技术讨论。"""
    x_creds = get_x_config()
    if x_creds is None:
        print("[X] no X auth configured — skip. Add AUTH_TOKEN+CT0 to ~/.config/last30days/.env")
        return []

    engine_path, python_path = resolve_engine_and_python()
    if engine_path is None:
        print("[X] last30days engine not found, skip")
        return []

    # 按需缩小搜索范围：如果配置了自定义查询，用自定义；否则用默认
    cfg = load_config()
    x_cfg = cfg.get("signals", {}).get("x", {})
    queries = x_cfg.get("queries", DAILY_QUERIES)
    max_total = x_cfg.get("max_total_items", 40)

    all_signals = []
    seen_urls = set()

    for query in queries:
        results = search_x(query, engine_path, python_path, x_creds)
        for sig in results:
            url = sig.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_signals.append(sig)
        if len(all_signals) >= max_total:
            break

    # 去重 + 排序（按互动量）
    all_signals.sort(key=lambda s: s.get("engagement", {}).get("total", 0), reverse=True)
    all_signals = all_signals[:max_total]

    print(f"[X] collected {len(all_signals)} signals total (de-duplicated)")
    return all_signals


def run():
    """CLI 入口 — 采集并保存到 raw/ 目录。"""
    date_str = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    print(f"[X] X/Twitter 信号采集 — {date_str}")

    signals = collect(date_str)
    if not signals:
        print("[X] no signals collected")
        return

    # 保存
    output_dir = RAW_DIR / date_str
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "x.json"
    output_path.write_text(
        json.dumps({"signals": signals, "collected_at": datetime.now(TZ_SHANGHAI).isoformat()},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[X] saved {len(signals)} signals → {output_path}")


if __name__ == "__main__":
    run()
