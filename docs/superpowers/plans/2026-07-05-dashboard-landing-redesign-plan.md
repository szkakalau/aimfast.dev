# Landing Page + Dashboard 重新设计 — 实现计划

> **Goal**: 将 Landing Page（7 段销售页）和 Dashboard（3 张卡片模式）从 spec 迁移到代码。
>
> **Architecture**: Next.js App Router（`output: 'export'`），React 客户端组件，现有 `dashboard.json` 数据源不变。
>
> **Tech Stack**: Next.js 16 + React + TypeScript + CSS（现有 design tokens）

---

## 执行顺序

```
Step 1: 新建 6 个组件（不破坏现有系统）
Step 2: 重写 dashboard-client.tsx（切换组件树）
Step 3: 重写 Landing Page（app/page.tsx）
Step 4: 新建 Reports 页面 + Login 页面 + Middleware
Step 5: 清理旧代码（删除 6 个旧组件 + 旧 CSS + 旧 HTML）
Step 6: Dashboard CSS 清理
```

---

## Global Constraints

- 不修改 `public/dashboard/data/dashboard.json` 格式
- 不修改任何 `scripts/*.py` 文件
- 继续使用 `public/_ds/` 中的 design tokens
- 过渡动画：`var(--duration-fast) var(--ease-out)`（≤200ms）
- 移动端 breakpoint: 640px
- 中英文双语支持（I18N 字典）
- 每步独立提交

---

### Step 1: 新建 6 个组件

**说明**: 创建新组件文件，不影响现有 Dashboard。每个组件都是独立的、可测试的单元。

#### Task 1.1: 创建 `decision-card.tsx`

**Files:**
- Create: `app/dashboard/components/decision-card.tsx`

**Props:**

```ts
type Props = {
  t: Record<string, string>;
  lang: 'zh' | 'en';
  signal: Signal | null;
  reportMd: string;
  date: string;
  onAskAI?: () => void;
};
```

**内容**:
- 机会名 + score badge
- 一句话描述
- 证据区（3 信号源，各有平台名 + 讨论量）
- 谁会付费（角色描述）
- 定价锚点 + 验证路径（并排两列）
- "为什么不选另外两个"排除项（callout 样式，左侧 accent 边框）
- 「🤖 问 AI」按钮（右下角，outline 样式，MVP 阶段 disabled 或隐藏）

**空状态**: 当 `signal === null` 时，显示降级文本（`t.decisionNoSignal`）

**骨架屏**: 此组件自带 loading skeleton 变体（通过 `loading` prop 控制）

#### Task 1.2: 创建 `competitor-card.tsx`

**Files:**
- Create: `app/dashboard/components/competitor-card.tsx`

**Props:**

```ts
type Props = {
  t: Record<string, string>;
  intel: CompetitorIntel | null;
  targets: CompetitorTarget[];
  onAddTarget?: () => void;
  onAskAI?: () => void;
};
```

**内容**:
- 无追踪目标 → 空状态 + quick-add 输入框
- 有目标无情报 → "今天没有值得关注的新动作"
- 有情报 → 每个目标一条摘要（对方做了什么 + 你的行动建议）
- 目标名 + 类型 badge
- [+] 添加追踪目标按钮
- 「🤖 问 AI」按钮

#### Task 1.3: 创建 `system-pulse.tsx`

**Files:**
- Create: `app/dashboard/components/system-pulse.tsx`

**Props:**

```ts
type Props = {
  t: Record<string, string>;
  history: HistoryEntry[];
  signals: Signal[];
  date: string;
};
```

**内容**:
- 迷你趋势线（14 天信号量，纯 CSS 或轻量 SVG bar chart）
- 今日信号数 + 最高分
- 跨平台信号计数
- 信源在线状态（全部在线 / 部分异常）
- 「查看完整日报归档 →」链接到 `/reports/`
- 异常状态：黄色边框，标注异常源

#### Task 1.4: 创建 `ai-chat-panel.tsx`

**Files:**
- Create: `app/dashboard/components/ai-chat-panel.tsx`

**Props:**

```ts
type Props = {
  t: Record<string, string>;
  cardType: 'decision' | 'competitor' | 'system';
  cardData: unknown;
  reportMd: string;
  isOpen: boolean;
  onClose: () => void;
};
```

**内容**:
- 从卡片下方展开的 Drawer（非全屏 Modal）
- 消息列表 + 输入框
- 流式输出（预留 SSE 接口，MVP 阶段显示 "Coming soon" placeholder）
- 关闭按钮
- 移动端变为全屏 Drawer（`@media (max-width: 640px)`）

**MVP 简化**: 对话面板只显示 UI 框架 + "AI 助手即将上线" 的 placeholder 文案。完整的流式对话在后续 PR 中实现（需要 `/api/ai-chat/` 端点 + Vercel Function 配置）。

#### Task 1.5: 重写 `dashboard-header.tsx`

**Files:**
- Modify: `app/dashboard/components/dashboard-header.tsx`

**改动**: 移除 Hero 数据展示逻辑，精简为纯导航栏。

**包含**:
- 日期选择器（`<select>` 或简洁的 `<` 今天 `>` 切换）
- 语言切换按钮（zh/en）
- 日期列表从 `archive` 数组构建（比旧版自由文本输入更可靠）

#### Task 1.6: 重写 `dashboard-footer.tsx`

**Files:**
- Modify: `app/dashboard/components/dashboard-footer.tsx`

**改动**: 添加「下次刷新倒计时」，移除无用链接。

**内容**:
- "数据刷新：每日 08:30 CST"
- "下次更新: Xh Ym"（动态倒计时）
- 归档链接

**验证 Step 1**: `npx tsc --noEmit` 编译通过，6 个组件文件存在且类型正确。

---

### Step 2: 重写 `dashboard-client.tsx`

**Files:**
- Modify: `app/dashboard/dashboard-client.tsx`

#### Task 2.1: 更新 I18N 字典

**改动**:
- 保留：`headerTitle`, `ciTitle`, `ciAddTarget`, `ciEmpty`, `ciNoIntel`, `footerRefresh`, `loading`, `noData`, `backToTop`
- 新增：`decisionCardTitle` (zh: '今日决策', en: "Today's Decision"), `decisionNoSignal` (zh: '今日暂无高确定性机会', en: 'No high-confidence opportunity today'), `decisionEvidence` (zh: '证据', en: 'Evidence'), `decisionBuyer` (zh: '谁会付费', en: 'Who Will Pay'), `decisionPricing` (zh: '定价', en: 'Pricing'), `decisionValidation` (zh: '验证路径', en: 'Validation'), `decisionWhyNot` (zh: '为什么不选另外两个', en: 'Why Not the Others'), `decisionAskAI` (zh: '问 AI', en: 'Ask AI'), `competitorCardTitle` (zh: '竞品动态', en: 'Competitor Intel'), `competitorNoIntel` (zh: '今天没有值得关注的新动作', en: 'No notable competitor activity today'), `competitorAction` (zh: '→ 你的行动', en: '→ Your move'), `pulseTitle` (zh: '系统脉搏', en: 'System Pulse'), `pulseSignals` (zh: '今日信号', en: 'Signals Today'), `pulseTopScore` (zh: '最高分', en: 'Top Score'), `pulseCrossPlatform` (zh: '跨平台', en: 'Cross-Platform'), `pulseSourcesOnline` (zh: '信源在线', en: 'Sources Online'), `pulseViewArchive` (zh: '查看完整日报归档', en: 'View Full Report Archive'), `pulseHealthy` (zh: '正常', en: 'Healthy'), `pulseDegraded` (zh: '部分异常', en: 'Degraded')
- 移除旧 key：所有跟 hero、top-signals、trend-charts、daily-report、opportunity-board、bet-drawer 相关的 key（约 30 个）

#### Task 2.2: 更新数据获取逻辑

**保持不变** — `fetch('/dashboard/data/dashboard.json')` 不变，类型定义（`DashboardData`, `Signal`, `HistoryEntry`, 等）不变。竞品相关字段保留。

**新增**：`localStorage` 缓存层——加载成功后写入 `localStorage.setItem('kakaopc_dashboard_cache', JSON.stringify(data))`，网络失败时读缓存。

#### Task 2.3: 替换组件树

旧渲染：
```tsx
<DashboardHero /> → <CompetitorIntel /> → <TopSignals /> → <TrendCharts /> → <DailyReport /> → <OpportunityBoard />
```

新渲染：
```tsx
<DecisionCard /> → <CompetitorCard /> → <SystemPulse />
```

#### Task 2.4: 添加 AI Chat Panel 状态管理

```ts
const [chatOpen, setChatOpen] = useState<'decision' | 'competitor' | 'system' | null>(null);
```

**验证 Step 2**: `npx tsc --noEmit` 通过，`npm run dev` 打开 `/dashboard/` 能看到 3 张卡片布局。

---

### Step 3: 重写 Landing Page（`app/page.tsx`）

**Files:**
- Modify: `app/page.tsx`

#### Task 3.1: 重写内容（7 段结构）

**Layout**: 纯服务端组件，无 client-side JS（除表单）。

| 段 | 元素 |
|----|------|
| Hero | 标题 + 副标题 + email 输入框 + "14 days free" 文案 |
| Pain Cards | 3 张卡片并排（方向浪费 / 竞争盲区 / 趋势滞后），CSS grid，移动端单列 |
| Product Demo | 静态决策卡（硬编码 HTML/CSS，展示日报格式） |
| How It Works | 双列布局：Discovery Engine + Monitoring Engine，箭头汇入日报 |
| Pricing | 单卡片，$19/mo，功能列表，CTA |
| FAQ | 4 个问题（跟钱和时间直接相关） |
| Footer CTA | 重复 value prop + email 输入 + 底部版权/链接 |

#### Task 3.2: 更新 SEO metadata

```ts
export const metadata: Metadata = {
  title: 'AimFast.Dev — Know What Your Market Is Doing, Every Morning',
  description: 'You\'re building. They\'re watching. Are you? — Daily competitive intel and market signals for indie developers who already have revenue.',
};
```

#### Task 3.3: Email CTA

`<form action="/api/signup">` → 暂时指向 Tally.so 或 Google Form 外链。不建 `/signup` 页面和 `/api/signup` 端点。

**验证 Step 3**: `npm run build` 通过，访问 `/` 看到完整 Landing Page。

---

### Step 4: 新建 Reports + Login

#### Task 4.1: Reports 列表页 `/reports/`

**Files:**
- Create: `app/reports/page.tsx`
- Create: `app/reports/[date]/page.tsx`

**列表页** (`/reports/`):
- 静态生成（`generateStaticParams` 读取 archives）
- 日期降序列表，每条 = 日期 + 标题 + 分数
- 点击进入详情

**详情页** (`/reports/[date]/`):
- 展示该日决策卡（`DecisionCard` 组件的只读变体）
- 完整日报 Markdown 渲染（`report-content` class，复用现有 CSS）
- 从 `/dashboard/data/reports/{date}.json` 读取（如果有），否则从 `dashboard.json` 的 archive 中找

**简化方案**：详情页直接渲染完整的 `report_md` Markdown（`dangerouslySetInnerHTML` + 已有的 `report-content` 样式），不做卡片化——这是深度阅读场景。

#### Task 4.2: Login 页面

**Files:**
- Create: `app/login/page.tsx`

**内容**:
- 极简页面：标题 + 密码输入 + 提交按钮
- `"use client"` — POST 到 `/api/login/`（或直接 set cookie）

**简化方案**：不建 `/api/login/` API。Login 页用纯前端实现——输入密码，与 `NEXT_PUBLIC_DASHBOARD_PASSWORD` 环境变量对比，匹配则设置 `document.cookie`，重定向 `/dashboard/`。

#### Task 4.3: Middleware

**Files:**
- Create: `middleware.ts`（根目录）

**逻辑**:
- 检查 `/dashboard/` 路径的 cookie
- 无 cookie → 重定向 `/login/`
- 有 cookie → 放行
- Landing Page (`/`) 和 Reports (`/reports/`) 不受保护

**注意**: `output: 'export'` 不支持 middleware。需要切换到 `output: 'standalone'` 或 hybrid 模式。

**简化方案**：Dashboard 页面改为 `"use client"` 内检查 cookie（客户端重定向到 `/login/`）。虽然安全性较低（HTML 已下载），但对单用户场景可接受。或者直接砍掉登录——Dashboard 不需要密码，因为 Landing Page 上的「Start Free Trial」已经是手动发密码的流程。

**验证 Step 4**: `/reports/` 可访问，历史日报可查看。`/login/` 可访问。

---

### Step 5: 清理旧代码

#### Task 5.1: 删除旧组件

```bash
rm app/dashboard/components/dashboard-hero.tsx
rm app/dashboard/components/top-signals.tsx
rm app/dashboard/components/trend-charts.tsx
rm app/dashboard/components/daily-report.tsx
rm app/dashboard/components/opportunity-board.tsx
rm app/dashboard/components/bet-drawer.tsx
```

#### Task 5.2: 删除旧 HTML Dashboard

```bash
rm public/dashboard/index.html
```

同时删除 `public/dashboard/data/` 中旧 Dashboard 所需的专用数据文件（如果有）。

#### Task 5.3: 清理 `globals.css`

移除 `@import '../public/_ds/dashboard.css';`（如果不再需要），替换为 `@import '../app/dashboard/dashboard-cards.css';`（新卡片样式）。

**验证 Step 5**: `npm run build` 通过，`npx tsc --noEmit` 通过，无未引用文件的 warning。

---

### Step 6: Dashboard CSS 清理

**Files:**
- Create: `app/dashboard/dashboard-cards.css`
- Modify: `app/globals.css`

**说明**: 从 `public/_ds/dashboard.css` 中只提取新 Dashboard 需要的样式规则（约 30%），新建 `app/dashboard/dashboard-cards.css`。

**需要的样式**:
- 卡片基础样式（`.card`, `.card-full`）
- 决策卡样式（`.decision-card`, `.evidence-grid`, `.pricing-validation`, `.why-not`）
- 竞品卡样式（`.competitor-item`, `.competitor-action`）
- 系统脉搏样式（`.pulse-chart`, `.pulse-stats`）
- AI 对话面板样式（`.ai-chat-panel`, `.chat-messages`, `.chat-input`）
- 骨架屏样式（`.skeleton`, `.skeleton-pulse`）
- 移动端响应式（`@media (max-width: 640px)`）

**不需要的样式**:
- 表格样式（Top 10 Signals）
- Chart.js 容器样式（Trend Charts）
- 机会看板样式（Demand Radar, Opportunity Board）
- 下注抽屉样式
- Workbench 相关样式

**如果提取工作太耗时**：保留 `public/_ds/dashboard.css` 不变，只确保新组件不引用其中已删除模块的 class。CSS 体积稍大但不影响功能——可以在后续 PR 中优化。

**验证 Step 6**: `npm run build` 成功，`/dashboard/` 页面加载正常，移动端布局正常。

---

## 验证清单

- [ ] `npx tsc --noEmit` 零错误
- [ ] `npm run build` 成功（static export 完整）
- [ ] `/` 显示 7 段 Landing Page
- [ ] `/dashboard/` 显示 3 张卡片
- [ ] 加载骨架屏出现 → 数据加载后卡片显示
- [ ] 中英文切换正常
- [ ] 移动端（640px）单列布局
- [ ] `/reports/` 可访问，列表显示
- [ ] 8 个 Python 测试仍通过（`pytest tests/`）
- [ ] 无 console error/warning
- [ ] 旧 `public/dashboard/index.html` 已删除
