# Design Upgrade Prompt

将此文件内容复制到 Claude 对话中，即可对任何项目执行本文档末尾列出的设计升级。

## 使用方式

1. 先把 `design-system.css` 复制到目标项目中
2. 在 Claude 中粘贴下面的 prompt
3. Claude 会按顺序执行所有升级步骤

---

## Prompt（从这里开始复制）

```
你要对这个项目执行以下设计升级，按顺序逐项完成，每完成一项构建验证后提交。

**前置条件**：`design-system.css` 已放在项目目录中。

### 第 1 项：加载字体

在 HTML <head> 中添加 Google Fonts：

```
<link href="https://fonts.googleapis.com/css2?family=Fira+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
```

找出项目中加载字体的位置：
- Next.js App Router → `app/layout.tsx`
- Next.js Pages Router → `pages/_document.tsx`
- Vite + React → `index.html`
- 纯 HTML → `index.html`

加完后构建验证。

### 第 2 项：导入设计系统 CSS

在主 CSS 文件或入口文件中导入 `design-system.css`：
- 如果有 `globals.css`，在顶部加 `@import './design-system.css';`
- 如果是 JS/TS 入口文件，加 `import './design-system.css';`
- 如果是纯 HTML，在 `<head>` 加 `<link rel="stylesheet" href="design-system.css">`

加完后构建验证。

### 第 3 项：品牌色定制

打开 `design-system.css`，搜索 `BRAND`，把 3 行品牌色改成项目已有的主色调。如果项目还没有主色调，保持默认的琥珀色。

### 第 4 项：标题字体升级

找到项目中所有设置标题字体的地方，确保：
- 标题使用 sans-serif（非等宽字体）
- 等宽字体只用于代码块、数据标签、badge、日期
- 标题字重至少 600，h1 建议 700-800
- h1 字号不低于 `clamp(2rem, 5vw, 3.5rem)`
- 标题 letter-spacing 收紧到 -0.02em 到 -0.03em

### 第 5 项：卡片升级（边框 → 阴影）

找到项目中所有带 `border: 1px solid` 的卡片/面板/列表项，执行：
- 去掉 `border`（或改为 `border: none`）
- 添加 `box-shadow: var(--shadow-xs)`（或 `--shadow-sm`）
- hover 时：`box-shadow: var(--shadow-md)` + `transform: translateY(-1px)`
- 添加 transition 使变化平滑

**例外**（保留边框）：
- 输入框（input、textarea、select）
- 按钮（btn-outline 类）
- 卡片内部的区域分隔线（border-top / border-bottom）
- 强调色条（如 card-accent 的左侧 accent border）

### 第 6 项：Emoji → Lucide 图标

如果项目有 emoji 做装饰性图标，执行：
1. `npm install lucide-react`
2. 搜索所有 emoji 使用位置
3. 替换为对应的 Lucide 图标（`size={32}` 做大图标，`size={16}` 做内联图标）
4. 内联图标加 CSS 类：`display: inline-block; vertical-align: middle; margin-right: 4px;`

**保留不做替换的**：
- 纯文本标记符号（✓ ✗ ❌ → 等，作为内容的一部分）
- 列表项的 bullet

每改完一个文件构建验证。

### 第 7 项：Hero/首屏视觉焦点

如果项目有 Hero 区域，添加视觉焦点：
- 给 Hero 容器加 `position: relative; overflow: hidden;`
- 用 `::before` 伪元素添加径向渐变光晕：
```
background: radial-gradient(ellipse 50% 50% at 50% 0%, oklch(品牌色 / 0.10) 0%, oklch(品牌色 / 0.04) 40%, transparent 70%);
```
- Hero 直接子元素加 `position: relative; z-index: 1;` 确保在光晕之上

### 每项完成后的提交格式

```
style: <项目名> — <具体做了什么>
```

全部完成后推送。
```

---

## 适用场景

| 项目类型 | 效果 |
|---------|------|
| SaaS Landing Page | 全部 7 项 |
| 后台 Dashboard | 第 1-6 项（跳过 Hero） |
| 个人博客 | 第 1-4 项 |
| 纯工具/CLI 页面 | 第 1-2 项 |
