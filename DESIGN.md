# AimFast.Dev Design System

> 本文档记录 AimFast.Dev 的设计决策和模式。先读此文，再写代码。
> 最后更新: 2026-07-15 | 审查: `/plan-design-review`

## 设计哲学

**Material Design 纯粹性** — 依靠间距（Spacing）和文字粗细（Font Weight）建立视觉层级，而非依赖边框和阴影。卡片无边框（`border: none`），深度由 `box-shadow` 表达。

**自然过渡** — 所有状态切换使用 `duration-200 ease-out`，严禁突变。

**克制优先** — 如果 UI 元素不能证明其存在的必要性，就删除它。

## 颜色系统

使用 OKLCH 色板（所有颜色有 hex 回退，兼容 Safari <15.4）。

| Token | 用途 | 值 |
|-------|------|-----|
| `--color-bg` | 页面背景 | `oklch(98.5% 0.002 250)` |
| `--color-surface` | 卡片/容器背景 | `oklch(100% 0 0)` |
| `--color-text` | 主文字 | `oklch(18% 0.005 90)` |
| `--color-text-secondary` | 次要文字 | `oklch(38% 0.01 90)` |
| `--color-text-muted` | 辅助文字 | `oklch(52% 0.01 90)` |
| `--color-accent` | 主强调色 (amber) | `oklch(55% 0.18 60)` |
| `--color-blue` | 数据/操作色 | `oklch(45% 0.22 265)` |
| `--color-green` | 成功色 | `oklch(58% 0.16 155)` |
| `--color-red` | 错误色 | `oklch(52% 0.22 25)` |

**暗色模式**：添加 `[data-theme="dark"]` 到 `<html>` 即可切换。所有颜色通过 token 引用，无需修改组件。

## 排版

- **Headings**: Fira Sans, weight 600-800, letter-spacing -0.025em
- **Body**: Fira Sans, weight 400, line-height 1.65
- **Data/Mono**: JetBrains Mono, weight 400-500（数字、标签、badge、stage、排序控件）
- **字号**: h1 clamp(2.4rem, 5.5vw, 4rem) → 正文 1rem → mono 0.75-0.85rem
- **禁用**: system-ui、-apple-system 作为正文字体

## 间距

8px 节奏系统：`--space-1: 8px` → `--space-12: 96px`

## 圆角

`--radius-sm: 6px` → `--radius-md: 8px` → `--radius-lg: 12px` → `--radius-xl: 16px`

## 阴影

6 级阴影（xs → xl）+ glow。卡片默认 `shadow-xs`，hover 升到 `shadow-md` + `translateY(-2px)`。

## 组件模式

### 卡片系统（3 层）

```css
.card             /* 基础卡片：surface bg, radius-lg, padding-4, shadow-xs */
.card-interactive /* 可交互：+ hover: shadow-md + translateY(-2px) */
.card-highlight   /* 强调：+ border-left: 3px accent */
```

Size modifier: `.card-sm` (padding-3) / `.card-md` (padding-4, 默认) / `.card-lg` (padding-5)

### 按钮

- `.btn-primary` — accent 实心，glow shadow
- `.btn-outline` — 透明 + border，hover 时 accent 边框
- `.stage-filter-btn` — 圆角 pill，mono 字体
- `.track-btn` — 小号边框按钮

### Badge / Pill

- `.badge` — mono + uppercase + 全圆角（100px）
- `.stage-badge` — 按 stage 着色（nascent/emergent/validating/rising）
- `.eyebrow` — accent 色 + mono + uppercase pill

### Skeleton Loader

`.skeleton` — shimmer 动画（1.5s），用于 loading 状态。子类：`.skeleton-text`、`.skeleton-chart`。

## 响应式断点

| 断点 | 适用 |
|------|------|
| 900px | Trend grid: 3→2 列, Detail: 2→1 列 |
| 720px | Homepage grid: 多列→1 列, 按钮全宽 |
| 640px | 移动端 nav: hamburger, Filter bar: 垂直布局 |
| 480px | 紧凑间距, 字号微调 |
| 360px | 极小屏优化 |

## 交互状态标准

每个组件必须覆盖 5 种状态：
1. **Loading** — skeleton 占位
2. **Empty** — 引导性空态（warmth + primary action + context）
3. **Error** — Section 级 ErrorBanner（不阻断整个页面）
4. **Success** — 正常数据展示
5. **Edge Case** — 极值数据（0 结果、47 字符名、50 item 上限）

## 图标

- **UI 图标**: Lucide（`lucide-react`），stroke-width 1.8
- **数据 emoji**: 可保留在卡片内容中（source badge），但不在 UI 控件中使用
- **尺寸**: `.icon` (24px), `.icon-sm` (16px), `.icon-lg` (32px)

## 可访问性

- Focus visible: 2px accent outline, offset 3px
- Touch target: ≥44px 所有交互元素
- Skip link: 页面顶部，跳转到主内容
- Label: 所有 form 控件有可见或 sr-only label
- Reduced motion: `@media (prefers-reduced-motion: reduce)` 覆盖所有动画

## 禁止模式

1. Emoji 作为 UI 元素（emoji 仅限内容中）
2. 背景渐变色 / 装饰性圆球 / 波浪 SVG
3. 边框 + 阴影并用（选其一）
4. 硬编码颜色值（必须用 CSS 变量）
5. 新卡片变体（使用 3 层卡片系统）
6. `<16px` 的正文字号
7. placeholder 作为唯一 label
8. 默认字体栈（Inter/Roboto/Arial/system-ui）
