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

## 设计要求

1. **极简单页**: 一个 HTML 文件，包含所有 CSS/JS，无外部依赖（除 Google Fonts）
2. **暖色暗色模式**: 背景 #0d0f12，卡片 #14171c，强调色 #f59e42
3. **结构**: Hero → 3 个 Selling Points → Pricing → CTA → Footer
4. **字体**: DM Sans（标题）+ DM Mono（代码/数字），从 Google Fonts 加载
5. **圆角**: 8px，阴影轻柔，无硬边框
6. **响应式**: 移动端友好，max-width 960px

## HTML 页面结构

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>产品名 — 一句话价值主张</title>
  <link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>/* 所有 CSS 内联 */</style>
</head>
<body>
  <main>
    <section class="hero"><!-- headline + subheadline + CTA --></section>
    <section class="selling-points"><!-- 3 cards --></section>
    <section class="pricing"><!-- pricing tiers --></section>
    <section class="cta"><!-- final CTA --></section>
    <footer><!-- copyright --></footer>
  </main>
</body>
</html>
```

## 内容要求

- Headline ≤ 10 词（英文）或 ≤ 15 字（中文）
- 3 个 Selling Points，每个 ≤ 30 字
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
