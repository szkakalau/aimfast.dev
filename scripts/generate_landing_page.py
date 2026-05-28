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

### 1. 引用共享设计系统 —— 禁止内联重复定义
LP 必须通过 <link> 引用项目共享的设计系统文件，不得在 <style> 中重新定义 token：
```html
<link rel="stylesheet" href="/_ds/base.css">
<link rel="stylesheet" href="/_ds/components.css">
```
共享 tokens.css 已定义所有 OKLCH 色彩、字体、间距变量，components.css 已定义 .btn、.badge、.card、.eyebrow、.icon、.container 等组件。直接使用这些 class，不要重新发明。

### 2. OKLCH 色彩 —— 禁止硬编码 hex
所有颜色必须使用 CSS 变量引用 tokens.css 中定义的变量。核心变量：
- 背景: var(--color-bg) — 暖色暗色，非纯黑
- 表面: var(--color-surface) / var(--color-surface-alt)
- 强调色: var(--color-accent) — 暖橙
- 文字: var(--color-text) / var(--color-text-secondary) / var(--color-text-muted)
- 边框: var(--color-border) / var(--color-border-hover)
禁止在规则中直接写 `#xxx`、`oklch(...)` 或任何硬编码颜色值。

### 3. 对称布局
LP 布局必须使用对称网格。Selling Points 用 3 列等宽 grid，Pricing 用 3 列等宽 grid。禁止偏移、错位、重叠、非等距排列。
推荐结构：
- Selling Points: `grid-template-columns: repeat(3, 1fr)`
- Pricing: `grid-template-columns: repeat(3, 1fr)`，中间卡片用 .featured 视觉突出但不偏移

### 4. Lucide Icons —— 零 Emoji
所有图标必须是内联 Lucide SVG（viewBox="0 0 24 24"，stroke-width 1.8，fill="none"）。
直接使用 components.css 中的 .icon / .icon-sm / .icon-lg / .icon-accent class。
常用路径参考：
- 闪电/zap: `<path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>`
- 箭头/arrow-right: `<path d="M5 12h14M12 5l7 7-7 7"/>`
- 文件/file-text: `<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>`
- 编辑/edit: `<path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>`
- GitHub: `<path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"/>`

### 5. 8px 节奏
所有自定义间距（margin/padding/gap）必须是 8 的倍数，使用 var(--space-N) 变量。
--space-1: 8px, --space-2: 16px, --space-3: 24px, --space-4: 32px, --space-5: 40px, --space-6: 48px, --space-8: 64px。

### 6. 排版
使用 tokens.css 中的字体变量：
- 标题: var(--font-heading) — Space Grotesk + JetBrains Mono
- 正文: var(--font-body) — DM Sans
- 代码/数字: var(--font-mono) — JetBrains Mono
正文 line-height: 1.6-1.75。标题与正文有明显字重/字号/颜色对比。

### 7. 动画克制
hover transition ≤ 200ms。使用 var(--duration-normal) 和 var(--ease-out)。禁止弹跳、旋转、脉冲动画。

### 8. SEO 元数据 —— 必须注入 <head>
每个 LP 的 <head> 必须包含以下 SEO 标签（使用 LP 的实际内容填入）：
```html
<meta name="robots" content="index, follow">
<meta name="theme-color" content="#1a1d24">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="canonical" href="https://aimfast.dev/SLUG/">
<!-- Open Graph -->
<meta property="og:type" content="product">
<meta property="og:title" content="PRODUCT_NAME — TAGLINE">
<meta property="og:description" content="ONE_SENTENCE_VALUE_PROP">
<meta property="og:url" content="https://aimfast.dev/SLUG/">
<meta property="og:site_name" content="KAKAOPC Intel">
<meta property="og:image" content="https://aimfast.dev/favicon.svg">
<!-- Twitter Card -->
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="PRODUCT_NAME — TAGLINE">
<meta name="twitter:description" content="ONE_SENTENCE_VALUE_PROP">
<meta name="twitter:image" content="https://aimfast.dev/favicon.svg">
<!-- JSON-LD Structured Data -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "PRODUCT_NAME",
  "applicationCategory": "AIApplication",
  "operatingSystem": "Web",
  "description": "PRODUCT_DESCRIPTION",
  "url": "https://aimfast.dev/SLUG/",
  "offers": {
    "@type": "Offer",
    "price": "PRICE",
    "priceCurrency": "USD"
  }
}
</script>
```
将 SLUG、PRODUCT_NAME、TAGLINE、ONE_SENTENCE_VALUE_PROP、PRODUCT_DESCRIPTION、PRICE 替换为 LP 的实际内容。

## 页面结构
Hero → Selling Points（对称 3 列 grid）→ Pricing（对称 3 列 grid，中间卡片 .featured 突出）→ FAQ（左对齐 accent 竖线）→ CTA（居中）→ Footer

## 内容要求
- Headline ≤ 10 词（英文），必须具体描述产品价值
- 3 个 Selling Points，每个 ≤ 30 词
- 定价展示简洁（单次 / 月度）
- CTA 按钮文字具体（"Try Free" > "Learn More"）
- Footer 包含 © 2026 和返回 aimfast.dev 的链接
- 每个 section 必须有 h2 标题（含 Selling Points 和 FAQ），后续层级用 h3。禁止跳过 heading 层级（h1 → h3）。
- <title> 格式："PRODUCT_NAME — TAGLINE | aimfast.dev"

输出完整的 HTML 源码。不要用代码块包裹。"""


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
