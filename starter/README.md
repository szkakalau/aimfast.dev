# Starter Design System

一个独立的 CSS 文件，拖进任何项目就能让界面看起来更专业。约 5KB（gzip 后）。

> 🤖 **用 Claude 一键升级**：打开 [UPGRADE.md](UPGRADE.md)，复制那行 prompt，粘贴到 Claude 对话中即可。

---

## 手动用法（3 步）

### 第 1 步：复制文件

把 `design-system.css` 复制到你的项目里。根据你用的框架：

| 框架 | 放在哪里 |
|------|---------|
| Next.js (App Router) | `app/design-system.css` |
| Vite + React | `src/design-system.css` |
| 纯 HTML | 和 `index.html` 同一个文件夹 |

### 第 2 步：加载字体

把下面这行粘贴到 HTML 的 `<head>` 标签里：

```html
<link href="https://fonts.googleapis.com/css2?family=Fira+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
```

| 框架 | 在哪里加 |
|------|---------|
| Next.js | `app/layout.tsx` 的 `<head>` 标签内 |
| Vite + React | `index.html` |
| 纯 HTML | `index.html` |

### 第 3 步：导入 CSS

**Next.js** — 在 `app/layout.tsx` 顶部加一行：

```tsx
import './design-system.css';
```

**Vite + React** — 在 `src/main.tsx` 顶部加一行：

```tsx
import './design-system.css';
```

**纯 HTML** — 在 `<head>` 里加：

```html
<link rel="stylesheet" href="design-system.css">
```

---

## 改品牌色

打开 `design-system.css`，搜索 `BRAND`，改这 3 行：

```css
--color-accent:       #d97706;   /* ← 改成你的品牌色 */
--color-accent-hover: #b45309;   /* ← 改成深一点的版本 */
--color-accent-muted: oklch(55% 0.18 60 / 0.1);  /* ← 同上，保持 / 0.1 */
```

---

## 可以用的 CSS 类

### 卡片

```html
<!-- 普通卡片（无边框，阴影代替） -->
<div class="card">...</div>

<!-- 带左侧色条的强调卡片 -->
<div class="card card-accent">...</div>
```

### 按钮

```html
<a href="/buy" class="btn btn-primary">立即购买</a>
<button class="btn btn-outline">了解更多</button>
```

### 其他

```html
<span class="badge">New</span>
<span class="eyebrow">Section Label</span>
<div class="container">...</div>
<hr class="hr">
```

### 动画和加载

```html
<!-- 从下往上淡入 -->
<div class="anim-fade-up">...</div>

<!-- 延迟出现 -->
<div class="anim-fade-up anim-delay-1">...</div>

<!-- 加载占位符 -->
<div class="skeleton" style="height: 200px;"></div>
```

---

## 图标（可选，推荐）

上面的步骤已经够用了。如果你还想把 emoji 换成专业图标：

```bash
npm install lucide-react
```

然后这样用：

```tsx
import { Search, Shield, Target, BarChart3 } from 'lucide-react';

{/* 大图标（装饰用） */}
<Search size={32} />

{/* 小图标（放在文字旁边） */}
<Target size={16} className="icon-inline" /> Today's Decision
```

常用图标速查：

| 含义 | 图标 | 导入 |
|------|------|------|
| 搜索/发现 | `Search` | `lucide-react` |
| 保护/监控 | `Shield` | `lucide-react` |
| 目标/决策 | `Target` | `lucide-react` |
| 数据/图表 | `BarChart3` | `lucide-react` |
| 金钱/定价 | `Banknote` | `lucide-react` |
| 闪电/快速 | `Zap` | `lucide-react` |
| 下跌/趋势 | `TrendingDown` | `lucide-react` |
| 眼睛/观察 | `Eye` | `lucide-react` |
| 时钟/时间 | `Clock` | `lucide-react` |
| 列表/报告 | `ClipboardList` | `lucide-react` |
| 关闭 | `X` | `lucide-react` |

---

## 设计原则

1. **卡片不用边框** — 用阴影区分层次
2. **标题用无衬线体** — 等宽字体只在代码/数据标签上用
3. **间距按 8px 倍数** — 用 `var(--space-2)` 代替随手写的 `16px`
4. **hover 要有反馈** — 卡片浮起 + 阴影加深
