"""
竞品追踪目标导出器
从数据库导出所有活跃追踪目标 → tracking_targets.json
供 generate_competitor_intel.py 消费

用法：
  python -m scripts.export_tracking_targets [--output tracking/tracking_targets.json]
"""
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
TRACKING_DIR = ROOT / "tracking"
TZ_SHANGHAI = timezone(timedelta(hours=8))

# 加载 .env 以传递给 Node.js 子进程
load_dotenv(ROOT / ".env")
load_dotenv(ROOT / ".env.local")


def _query_db() -> list[dict]:
    """通过 Node.js 子进程从数据库查询活跃追踪目标。"""
    js_code = """
const { PrismaClient } = require('@prisma/client');
const { PrismaNeonHttp } = require('@prisma/adapter-neon');
// database_url is auto-bound via process.env from parent Python process
const adapter = new PrismaNeonHttp(process.env.database_url, {});
const prisma = new PrismaClient({ adapter });
prisma.trackingTarget.findMany({
  where: { status: 'active' },
  select: {
    id: true, userId: true, name: true, type: true,
    aliases: true, keywords: true, notes: true, createdAt: true
  }
}).then(function(targets) {
  console.log(JSON.stringify(targets));
  prisma.$disconnect();
}).catch(function(e) {
  console.error(JSON.stringify({ error: e.message }));
  prisma.$disconnect();
  process.exit(1);
});
""".strip()

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".js", prefix="export_targets_", delete=False,
        encoding="utf-8", dir=str(ROOT)
    ) as f:
        f.write(js_code)
        tmp_path = f.name

    # 构建环境变量（传递 DATABASE_URL 给 Node.js，避免 dotenv 的 stdout 干扰）
    env = os.environ.copy()
    if "DATABASE_URL" in env:
        env["database_url"] = env["DATABASE_URL"]

    try:
        result = subprocess.run(
            ["node", tmp_path],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout and result.stdout.strip():
            targets = json.loads(result.stdout.strip())
            print(f"[Export] 从数据库导出 {len(targets)} 个活跃追踪目标")
            return targets
        elif result.stderr and "error" in result.stderr.lower():
            print(f"[Export] 查询失败: {result.stderr[:300]}")
        else:
            err_msg = (result.stderr or "")[:300]
            print(f"[Export] 查询返回空 (exit={result.returncode}, stderr={err_msg})")
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"[Export] 子进程错误: {e}")
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except OSError:
            pass

    return []


def run() -> list[dict]:
    """从数据库导出所有活跃追踪目标。失败时回退到缓存 JSON。"""
    targets = _query_db()
    if targets:
        return targets

    # Fallback: read cached JSON
    cache_path = TRACKING_DIR / "tracking_targets.json"
    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            targets = cached.get("targets", [])
            print(f"[Export] 从缓存读取 {len(targets)} 个追踪目标")
            return targets
        except Exception as e:
            print(f"[Export] 缓存读取失败: {e}")

    print("[Export] 无追踪目标可用")
    return []


def save(targets: list[dict], output_path: Path | None = None):
    """Save tracking targets to JSON file."""
    path = output_path or (TRACKING_DIR / "tracking_targets.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "exported_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "count": len(targets),
        "targets": targets,
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[Export] 已保存 -> {path}")


if __name__ == "__main__":
    targets = run()
    save(targets)
    print(f"[Export] 完成 - {len(targets)} 个追踪目标")
