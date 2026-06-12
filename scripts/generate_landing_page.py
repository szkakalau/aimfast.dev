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
from scripts.pipeline_status import write as write_pipeline_status

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

## 核心目标：收集用户邮箱

这是验证阶段的 LP。唯一的目标是让用户**输入邮箱并提交**。不是卖产品，不是展示定价——是测试这个想法有没有人感兴趣。
每多一个步骤（点击按钮 → 弹窗 → 填邮箱 → 提交），转化率就砍半。所以：**邮箱输入框必须直接内嵌在 Hero 区域，零点击可见。**

## 设计铁律（违反任何一条 = 不合格）

### 1. 引用共享设计系统 —— 禁止内联重复定义
LP 必须通过 <link> 引用项目共享的设计系统文件，不得在 <style> 中重新定义 token：
```html
<link rel="stylesheet" href="/_ds/base.css">
<link rel="stylesheet" href="/_ds/components.css">
```
共享 tokens.css 已定义所有 OKLCH 色彩、字体、间距变量，components.css 已定义 .btn、.badge、.card、.eyebrow、.icon、.container 等组件。直接使用这些 class，不要重新发明。

### 2. OKLCH 色彩 —— 禁止硬编码 hex
所有颜色必须使用 CSS 变量。核心变量：
- 背景: var(--color-bg), 表面: var(--color-surface) / var(--color-surface-alt)
- 强调色: var(--color-accent)
- 文字: var(--color-text) / var(--color-text-secondary) / var(--color-text-muted)
- 边框: var(--color-border)
禁止硬编码 `#xxx`、`oklch(...)` 或任何颜色值。

### 3. 邮箱优先布局
页面只有一个焦点：让用户输入邮箱。布局必须：
- **Hero 区域直接放置内嵌邮箱表单**（不是按钮→弹窗，是直接可见的 input + button）
- 表单使用横向布局（桌面端 input + button 并排），移动端竖向堆叠
- input 样式：大号（高度 ≥ 48px），清晰的 border，focus 时 border-color 变为 var(--color-accent)
- button 文字必须具体："Get Early Access" / "Join 500+ Developers" / "Send Me the Guide"

### 4. 无弹窗！无 Modal！
禁止使用 Modal/Dialog 收集邮箱。所有 email capture 必须是页面内嵌的表单。
唯一允许的 "弹窗" 是提交成功后的轻量 toast 提示（页面顶部滑入，2 秒后自动消失）。

### 5. 对称布局
- Selling Points: 3 列等宽 grid
- 禁止偏移、错位、重叠、非等距排列

### 6. Lucide Icons —— 零 Emoji
所有图标必须是内联 Lucide SVG（viewBox="0 0 24 24"，stroke-width 1.8，fill="none"）。
常用路径：
- 邮件: `<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>`
- 锁: `<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>`
- 检查/shield-check: `<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/>`

### 7. 8px 节奏
所有自定义间距使用 var(--space-N): --space-1:8px, --space-2:16px, --space-3:24px, --space-4:32px, --space-5:40px, --space-6:48px, --space-8:64px。

### 8. 排版
- 标题: var(--font-heading) — Space Grotesk + JetBrains Mono
- 正文: var(--font-body) — DM Sans, line-height 1.6-1.75
- 代码: var(--font-mono) — JetBrains Mono

### 9. 动画克制
hover transition ≤ 200ms，使用 var(--duration-normal) / var(--ease-out)。禁止弹跳、旋转。

### 10. SEO 元数据 —— 必须注入 <head>
```html
<meta name="robots" content="index, follow">
<meta name="theme-color" content="#1a1d24">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="canonical" href="https://www.aimfast.dev/SLUG/">
<meta property="og:type" content="product">
<meta property="og:title" content="PRODUCT_NAME — TAGLINE">
<meta property="og:description" content="ONE_SENTENCE_VALUE_PROP">
<meta property="og:url" content="https://www.aimfast.dev/SLUG/">
<meta property="og:site_name" content="KAKAOPC Intel">
<meta property="og:image" content="https://www.aimfast.dev/favicon.svg">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="PRODUCT_NAME — TAGLINE">
<meta name="twitter:description" content="ONE_SENTENCE_VALUE_PROP">
<meta name="twitter:image" content="https://www.aimfast.dev/favicon.svg">
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"SoftwareApplication","name":"PRODUCT_NAME","applicationCategory":"AIApplication","operatingSystem":"Web","description":"PRODUCT_DESCRIPTION","url":"https://www.aimfast.dev/SLUG/","offers":{"@type":"Offer","price":"PRICE","priceCurrency":"USD"}}
</script>
```

## 页面结构（严格按此顺序）

```
Hero（内嵌邮箱表单）
  → Why This Matters（2-3 段文字，≥ 150 words——Google 索引的关键内容）
    → How It Works（3 steps，每步有描述段落）
      → Selling Points（3 列 grid，每列 ≥ 20 words 实质描述）
        → Trust bar（一行小字）
          → Footer
```

**整个页面正文文字（不含 HTML/CSS/导航/SVG）必须 ≥ 250 个英文单词。** Google 对 < 300 词的页面视为 thin content。Selling Points 的卡片描述、How It Works 的步骤描述、Why This Matters 的段落文字 —— 全部计入词数。

## 每个区块的内容要求

### Why This Matters（h2: "Why [product_category] Matters Right Now"）
写 2-3 个段落解释：
1. 当前痛点是什么（引用信号来源——HN 讨论、GitHub star 数等）
2. 为什么现有解决方案不够好
3. 为什么现在是最佳时机（信号热度、趋势）
总计 ≥ 150 words。使用 <p> 标签。

### How It Works（h2: "How It Works"）
3 个步骤，每个步骤包含标题 + 描述段落（≥ 15 words），不是单行标签。
```html
<div class="step">
  <div class="step-num">1</div>
  <div class="step-content">
    <h3>Step title</h3>
    <p>Descriptive paragraph explaining what happens in this step — 15+ words with keywords.</p>
  </div>
</div>
```

### Selling Points（h2: "What You Get" 或从信号驱动的标题）
3 列 grid，每列包含：
- 图标（Lucide SVG, 32x32）
- 标题（≤ 5 词）
- 描述（≥ 20 words 实质性说明，不能是口号）

### Trust Bar
一行小字，包含 3 个信任信号。

## 不要出现的内容
- ❌ 定价表（Pricing grid）—— 验证阶段不需要
- ❌ Modal 弹窗 —— 邮箱直接嵌在页面里
- ❌ 多个 CTA 按钮指向不同目标
- ❌ "Subscribe" / "Buy Now" / "Start Free Trial" 等承诺性文字 —— 用 "Get Early Access" / "Join the Waitlist"

## 内容要求
- Headline ≤ 8 词
- 副标题 ≤ 15 词，解释为什么值得关注
- 页面正文 ≥ 250 个英文单词（不含 HTML/CSS/注释/SVG）
- <title>: PRODUCT_NAME — TAGLINE | www.aimfast.dev
- <meta name="description"> ≤ 160 字符
- OG image: `https://www.aimfast.dev/og/PRODUCT_SLUG.png`（不要用 favicon.svg）
- Footer: © 2026 · www.aimfast.dev

## 邮箱表单技术规范
```html
<form id="signup-form" class="signup-form" onsubmit="handleSubmit(event)">
  <input type="email" name="email" placeholder="you@example.com" required autocomplete="email">
  <button type="submit" class="btn btn-primary btn-lg">Get Early Access</button>
</form>
```
- 表单使用真实 URL: action="https://formspree.io/f/your-form-id" method="POST"
- JS handleSubmit: 阻止默认提交 → fetch POST → 成功时原地显示 "✓ You're on the list!"（替换表单，不弹窗）
- 失败时原地显示错误信息（替换表单，不弹窗）
- input 必须带 required、autocomplete="email"、type="email"

Output complete HTML source. Do not wrap in code blocks."""


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
        write_pipeline_status(date_str, "lp", "skipped",
            reason="no_action_plan",
            message="No landing-page.md found. Action plan was not generated today (threshold not met).")
        return None
    if tracking is None:
        print("[LP] 所有机会已处理或 tracking 不存在，跳过")
        write_pipeline_status(date_str, "lp", "skipped",
            reason="no_pending_opportunity",
            message="All tracked opportunities already have LPs built.")
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
    print(f"[LP] URL: https://www.aimfast.dev/{project_slug}")
    print(f"[LP] 部署: vercel --prod")

    write_pipeline_status(date_str, "lp", "generated",
        message=f"LP generated for {tracking.get('opportunity', 'N/A')[:60]} → https://www.aimfast.dev/{project_slug}")

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
            op["landing_page_url"] = f"https://www.aimfast.dev/{slug}"
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
