"""
Landing Page 生成与部署
输入: daily/YYYY-MM-DD/landing-page.md（Action 方案）
输出: landing_pages/OP-XXXXXXXX/index.html（可直接部署到 Vercel 的单页）
"""
import json
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

from scripts.llm_client import chat

ROOT = Path(__file__).resolve().parent.parent
DAILY_DIR = ROOT / "daily"
TRACKING_DIR = ROOT / "tracking"
LP_DIR = ROOT / "public"

TZ_SHANGHAI = timezone(timedelta(hours=8))


def find_action_plan(date_str: str) -> tuple[str, dict | None]:
    """查找当日的 Action 方案。返回 (plan_md, tracking_entry)。"""
    plan_path = DAILY_DIR / date_str / "landing-page.md"
    if not plan_path.exists():
        return "", None

    plan_md = plan_path.read_text(encoding="utf-8")

    # 查找对应的 tracking entry
    tracking = None
    opp_path = TRACKING_DIR / "opportunities.json"
    if opp_path.exists():
        opps = json.loads(opp_path.read_text(encoding="utf-8")).get("opportunities", [])
        for op in opps:
            if op.get("date") == date_str and op.get("lp_status") == "not_built":
                tracking = op
                break

    return plan_md, tracking


def _build_system_prompt() -> str:
    return """你是 KAKAOPC 情报科的 Landing Page 设计师。你的任务是将 Action 方案转化为一个可直接部署的单页 HTML。

## 设计铁律（违反任何一条 = 不合格）

### 1. 语义 Token —— 零硬编码值
所有颜色/间距/圆角必须定义为 CSS 变量，禁止在规则中直接写 `#xxx` 或 `px` 值。
```
:root {
  --color-bg: #0d0f12;
  --color-surface: #14171c;
  --color-surface-alt: #1a1d24;
  --color-border: #252830;
  --color-text: #f0ede8;
  --color-text-secondary: #a8a6a2;
  --color-text-muted: #7a7875;
  --color-accent: #f59e42;
  --color-accent-hover: #f7b25c;
  --color-accent-muted: rgba(245, 158, 66, 0.1);
  --color-accent-glow: rgba(245, 158, 66, 0.2);
  --radius-sm: 6px; --radius-md: 8px; --radius-lg: 12px;
  --space-1: 8px; --space-2: 16px; --space-3: 24px; --space-4: 32px; --space-5: 40px; --space-6: 48px; --space-8: 64px;
  --font-heading: 'DM Sans', sans-serif;
  --font-mono: 'DM Mono', monospace;
  --transition: 180ms ease;
}
```

### 2. Lucide Icons —— 零 Emoji
所有图标必须是内联 Lucide SVG（viewBox="0 0 24 24"，stroke-width 1.8）。
常用路径参考：
- 闪电/zap: `<path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>`
- 箭头/arrow-right: `<path d="M5 12h14M12 5l7 7-7 7"/>`
- 文件/file-text: `<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>`
- 编辑/edit: `<path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>`
- 帮助/help-circle: `<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/>`
- 锁/lock: `<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>`

### 3. 非对称布局
Selling Points 不可以用 3 列对称网格。必须用偏移、重叠或错位布局。
- 推荐：2+1 staggered（第2张卡片 mt-48）、非等宽 grid、或单列交替左右。

### 4. 8px 节奏
所有间距（margin/padding/gap）必须是 8 的倍数。禁止 5px、7px、10px、15px、20px 等非 8px 倍数值。

### 5. 暖色暗色模式
背景带温度偏色（非纯黑 #000000），单一强调色 #f59e42，无彩虹配色。
卡片用微妙 border 区分层级，阴影轻柔。圆角 6-12px，无硬边框。

### 6. 排版
- 标题 DM Sans（weight 600-700），正文 DM Sans（weight 400）
- 代码/数字/标签用 DM Mono
- 正文 line-height: 1.6-1.75
- 标题与正文有明显字重/字号/颜色对比

### 7. 动画克制
hover transition ≤ 200ms，避免过度装饰。无弹跳、无旋转、无脉冲动画。

## 页面结构
Hero → Selling Points（非对称 3 卡片）→ Pricing（中间卡片突出）→ FAQ（左对齐 accent 竖线）→ CTA → Footer

## 内容要求
- Headline ≤ 10 词（英文）或 ≤ 15 字（中文）
- 3 个 Selling Points，每个 ≤ 30 字描述
- 定价展示简洁（单次 / 月度）
- CTA 按钮文字具体（"免费试用" > "了解更多"）

输出完整的 HTML 源码，不要用代码块包裹。"""


def _build_user_prompt(plan_md: str, tracking: dict | None) -> str:
    lines = ["## Action 方案内容", "", plan_md]

    if tracking:
        lines.extend([
            "",
            "## 追踪信息",
            f"- ID: {tracking.get('id', '?')}",
            f"- 机会: {tracking.get('opportunity', '?')}",
            f"- 分数: {tracking.get('score', 0)} 分 | 跨平台: {tracking.get('cross_platform_count', 0)}",
        ])

    lines.extend([
        "",
        "---",
        "",
        "请基于以上 Action 方案生成完整的 Landing Page HTML。",
        "产品名使用方案中建议的名称，若未指定则从信号标题推断。",
        "确保 HTML 完整可用——打开即可看到效果，无需任何构建工具。",
    ])

    return "\n".join(lines)


def generate(date_str: str) -> str | None:
    """生成 Landing Page HTML。返回 output path 或 None。"""
    print(f"\n{'='*50}")
    print(f"[LP] Landing Page 生成 — {date_str}")
    print(f"{'='*50}")

    plan_md, tracking = find_action_plan(date_str)
    if not plan_md:
        print("[LP] 今日无 Action 方案，跳过")
        return None
    if tracking is None:
        print("[LP] 所有机会已处理或 tracking 不存在，跳过")
        return None

    tid = tracking["id"]
    print(f"[LP] 机会: {tid} — {tracking.get('opportunity', '')[:60]}")

    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(plan_md, tracking)

    print(f"[LP] 上下文: {len(system_prompt)} + {len(user_prompt)} = {len(system_prompt) + len(user_prompt)} 字符")

    html = chat(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.4,
        max_tokens=4096,
    )

    # 去掉可能的 markdown 代码块包裹
    if html.startswith("```"):
        lines = html.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        html = "\n".join(lines)

    # 确保以 <!DOCTYPE html> 开头
    if not html.strip().startswith("<!DOCTYPE"):
        print("[LP] 警告: 输出不以 DOCTYPE 开头，可能不是完整 HTML")

    # 生成 URL slug
    project_slug = tracking.get("opportunity", "project").lower()[:30]
    project_slug = "".join(c if c.isalnum() else "-" for c in project_slug)
    project_slug = project_slug.strip("-")

    # 保存到 public/<slug>/
    output_dir = LP_DIR / project_slug
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "index.html"
    output_path.write_text(html, encoding="utf-8")

    # 更新 tracking
    _update_tracking(tid, output_dir, project_slug)

    print(f"[LP] Landing Page 已保存 → {output_path}")
    print(f"[LP] 大小: {len(html):,} 字符")
    print(f"[LP] URL: https://aimfast.dev/{project_slug}")
    print(f"[LP] 部署: vercel --prod")

    return str(output_path)


def _update_tracking(tid: str, output_dir: Path, slug: str) -> None:
    """更新 tracking 中的 LP 状态。"""
    opp_path = TRACKING_DIR / "opportunities.json"
    if not opp_path.exists():
        return

    data = json.loads(opp_path.read_text(encoding="utf-8"))
    for op in data.get("opportunities", []):
        if op.get("id") == tid:
            op["lp_status"] = "live"
            op["landing_page_url"] = f"https://aimfast.dev/{slug}"
            op["notes"] = f"LP 已生成于 {datetime.now(TZ_SHANGHAI).strftime('%Y-%m-%d %H:%M')} | 部署: vercel --prod"
            break

    opp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[LP] 已更新 tracking: {tid} → lp_status=live")


def run(date_str: str | None = None) -> str | None:
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    return generate(date)


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    result = run(today)
    if result:
        try:
            print(f"\nLanding Page: {result}")
        except UnicodeEncodeError:
            print(f"\n[LP generated: {result}]")
