# Landing Page + Dashboard 重新设计

**Date**: 2026-07-05
**Status**: Approved
**Scope**: LP (`app/page.tsx`) + Dashboard (`app/dashboard/`) + Reports (`app/reports/`) + AI Chat API (`app/api/ai-chat/`)

---

## 1. 背景与动机

### 1.1 战略定位转变

当前系统以「副业探索者」为目标用户——帮开发者找到下一个 side project。但这类用户付费意愿低、留存不稳定。

**重新定位**：核心付费用户 = **已经在赚钱的独立开发者**（年收入 $10k+）。他们的痛点不是「找不到想法」，而是「在自己的市场里被竞争对手偷袭」——花两周做了没人要的功能、竞品改了定价自己三天后才知道、新渠道红利被吃完了才发现。

### 1.2 设计原则

- **30 秒扫完** — Dashboard 打开即读完，不做情报指挥中心
- **卡片 > 表格** — 日报以决策卡片呈现，不是 Markdown 长文
- **AI 增强但不替代** — 卡片满足 80% 日常需求，AI 对话服务 20% 深度追问
- **砍掉的勇气** — 机会看板、下注系统、Top 10 信号表格、趋势图表独立页全部移除

### 1.3 保留内容

- **日报**（Daily Report）— 这是产品的心脏，数据格式不变，前端呈现方式升级
- **双引擎架构**（Discovery + Monitoring）— 后端零改动
- **设计系统**（`public/_ds/` tokens + base + components）— 继续使用现有 design tokens
- **数据流** — `dashboard.json` 格式不变

---

## 2. Landing Page 设计

### 2.1 核心叙事

旧：*"One validated product opportunity. Every single morning."*
新：*"You're building. They're watching. Are you?"*

定位转变：从「我们帮你找方向」→「你的竞争对手已经在做了，你差的是情报」。

### 2.2 页面结构（7 段）

| 段 | 内容 | 目的 |
|----|------|------|
| Hero | 标题 + 副标题 + email CTA | 3 秒传达价值 + 捕获邮件 |
| 痛点三卡 | 方向浪费 / 竞争盲区 / 趋势滞后 | 让用户识别自己的问题 |
| 产品 Demo | 真实每日决策卡（静态截图风格） | 让未付费用户看到实际交付物 |
| How It Works | Discovery Engine + Monitoring Engine 双列 | 解释差异化（双引擎 = 发现 + 监控） |
| Pricing | $19/mo，单计划，全功能 | 简单定价，无选择负担 |
| FAQ | 4-5 个跟钱/时间直接相关的问题 | 消除购买顾虑 |
| Footer CTA | 重复 value prop + 邮箱输入 | 末次转化机会 |

### 2.3 删除的旧元素

- Stats Bar（11 sources / 300+ signals）— 对在营开发者无用
- "How is this different from reading Hacker News?" FAQ — 目标用户不会问
- "What if I don't like the daily insight?" FAQ — 显得产品不自信

### 2.4 Landing Page 语言

纯英文（目标用户是全球独立开发者，非中国特供）。

---

## 3. Dashboard 设计

### 3.1 单页布局（3 张卡片）

```
HEADER: 日期切换 / 语言切换 / 设置

CARD 1: 今日决策（Decision Card）
  - 机会名 + 分数
  - 一句话描述
  - 证据（3 个信号源 + 数据）
  - 谁会付费
  - 定价锚点 + 验证路径
  - "为什么不选另外两个"排除项
  - [🤖 问 AI] 按钮

CARD 2: 竞品动态（Competitor Card）
  - 每个追踪目标一条摘要
  - 对方做了什么 + 你的行动建议
  - 无情报时显示"今天没有值得关注的动作"
  - [+ 添加追踪目标] 入口
  - [🤖 问 AI] 按钮

CARD 3: 系统脉搏（System Pulse）
  - 14 天迷你趋势线
  - 今日信号数 + 最高分
  - 跨平台信号数 + 信源在线状态
  - [查看完整日报归档 →] 入口

FOOTER: 下次刷新倒计时 + "数据刷新: 每日 08:30 CST"
```

### 3.2 AI 对话面板

- **触发**：点击任意卡片的「🤖 问 AI」按钮
- **呈现**：卡片下方展开对话 Drawer（不遮挡其他卡片，可同时展开多个或只允许一个取决于开发复杂度——MVP 阶段只允许一个）
- **输出**：流式打字效果（SSE streaming）
- **上下文**：自动附带当前卡片数据 + 日报全文 + 历史关键词
- **持久化**：不持久化，关闭即消失
- **移动端**：全屏 Drawer 从底部滑上

### 3.3 多语言

- Dashboard UI 框架保持 zh/en 双语（日期标签、按钮文案等 I18N 键）
- 日报内容由后端 `report_md` / `report_md_en` 决定语言
- AI 对话：用户用什么语言问，AI 用什么语言答

---

## 4. 日报归档（Reports）

### 4.1 列表页 `/reports/`

- 按日期降序排列
- 每条显示：日期 + 当日决策卡标题 + 分数
- 无分页（全部加载，目前数据量小）
- 纯静态生成

### 4.2 单日报 `/reports/[date]/`

- 只读模式展示该日决策卡
- 包含完整 `report_md` 渲染（保留 Markdown 长文格式，作为深度阅读选项）
- 无 AI 对话（归档不提供追问——追问应该针对今天的决策）

---

## 5. 路由 & 组件树

### 5.1 路由

```
/                          Landing Page（静态服务端组件）
/dashboard/                Dashboard（客户端组件，需登录）
/reports/                  日报归档列表
/reports/[date]/           单日历史日报
/api/ai-chat/              AI 对话 API（POST → SSE stream）
/login/                    密码门（简单认证）
```

### 5.2 组件树

```
app/
├── layout.tsx
├── page.tsx                          Landing Page（单文件，无子组件）
│
├── dashboard/
│   ├── page.tsx                      Server component（metadata）
│   ├── dashboard-client.tsx          "use client" 主组件
│   └── components/
│       ├── dashboard-header.tsx      日期 + 语言切换
│       ├── decision-card.tsx         今日决策卡
│       ├── competitor-card.tsx       竞品动态卡
│       ├── system-pulse.tsx          系统脉搏卡
│       ├── ai-chat-panel.tsx         AI 对话 Drawer
│       └── dashboard-footer.tsx      刷新时间
│
├── reports/
│   ├── page.tsx                      归档列表
│   └── [date]/
│       └── page.tsx                  单日只读视图
│
├── login/
│   └── page.tsx                      简单密码登录
│
└── api/
    └── ai-chat/
        └── route.ts                  POST handler (streaming)
```

### 5.3 砍掉的组件

| 旧组件 | 处理 |
|--------|------|
| `dashboard-hero.tsx` | 合并到 decision-card |
| `top-signals.tsx` | 关键指标入 system-pulse |
| `trend-charts.tsx` | 压缩为 system-pulse 迷你线 |
| `daily-report.tsx` | 重写为 decision-card |
| `opportunity-board.tsx` | 整个模块砍掉 |
| `bet-drawer.tsx` | 整个模块砍掉 |

---

## 6. 数据流

```
Python 后端（每日定时，不变）
├── process_signals.py
├── generate_report.py        → report_md / report_md_en
├── generate_dashboard.py     → public/dashboard/data/dashboard.json
└── generate_competitor_intel.py
       │
       ▼
public/dashboard/data/
├── dashboard.json             ← 前端唯一数据源（格式不变）
│
/ (Landing Page)              /dashboard/                /api/ai-chat/
静态 HTML                     客户端 fetch()             POST → SSE stream
无数据依赖                     dashboard.json            需要运行时（Vercel Function）
```

### 6.1 AI Chat API

```
POST /api/ai-chat/
Content-Type: application/json

{
  "messages": [{ "role": "user", "content": "用Tauri替代Electron可以吗？" }],
  "context": {
    "card_type": "decision",
    "card_data": { /* 当前卡片的完整数据 */ },
    "report_md": "今日日报全文...",
    "today_date": "2026-07-05"
  }
}

Response: text/event-stream (SSE)
  data: {"delta": "可以用 Tauri。"}
  data: {"delta": "实际上这个场景..."}
  ...
  data: [DONE]
```

- LLM：DeepSeek V4 或 Vercel AI Gateway
- 每次对话附带完整日报上下文（~2000 tokens）
- 无对话历史持久化
- 超时：30s

### 6.2 部署调整

当前 `next.config.ts` 使用 `output: 'export'`（全静态）。`/api/ai-chat/` 需要运行时。

**方案**：保持 `output: 'export'`，AI Chat API 作为独立的 Vercel Function（通过 `vercel.json` functions 配置或在 Vercel 上手动添加）。或者直接去掉 AI Chat 的前端入口，在 MVP 阶段不实现 AI 对话——先用静态卡片交付核心价值。

MVP 阶段建议：先不实现 `/api/ai-chat/`。卡片体验本身已经比旧版好 10 倍，AI 对话可以在卡片上线后再加。

---

## 7. 状态处理

### 7.1 加载状态

- Dashboard：3 张卡片骨架屏（等高、灰色脉冲动画，`duration-200 ease-out`）
- Reports 列表：列表项骨架屏
- 加载超时（10s）→ 显示错误状态

### 7.2 空状态

| 场景 | 处理 |
|------|------|
| 今日无强信号（score < 阈值） | 决策卡降级：「今日暂无高确定性机会。以下是过去 7 天热度最高的信号」 |
| 无竞品追踪目标 | 「添加你的第一个追踪目标」+ quick-add 输入框 |
| 竞品存在但今日无新情报 | 「今天你的追踪目标没有值得关注的新动作」 |
| 系统脉搏异常 | 黄色边框 + 「部分数据源未更新」+ 具体源列表 |

### 7.3 错误状态

- `dashboard.json` fetch 失败 → 卡片区显示错误提示 + 上次成功时间 + 重试按钮
- 网络断开 → 静默使用 `localStorage` 缓存的上次数据

### 7.4 边界情况

- 数据异常（`signals: []`、`bets: null`）→ 前端兜底，不崩溃
- 日期切换至无数据日期 → 显示「该日期无报告」
- 移动端（≤640px）→ 单列，AI 对话全屏 Drawer

---

## 8. 认证方案

MVP 认证：**简单密码门**。

```
/login/ → 输入密码 → 设置 httpOnly cookie → 重定向 /dashboard/
/dashboard/ → middleware 检查 cookie → 无 cookie 则重定向 /login/
```

- 密码存储在 Vercel Environment Variable `DASHBOARD_PASSWORD`
- 不做用户注册、OAuth、邮箱验证
- Landing Page「Start Free Trial」→ 指向 Tally/Google Form 收集邮箱，手动发密码

---

## 9. 移动端适配

- 单列布局，卡片全宽
- 决策卡内：证据 3 信号源 → 一行 tag；定价 + 验证 → 上下堆叠
- 竞品动态：每个目标一条，堆叠
- AI 对话：全屏 Drawer 从底部滑上
- 字号不缩放（保持可读性）
- Breakpoint: 640px

---

## 10. 迁移路径（6 步）

```
Step 1: 新建 6 个组件（不影响现有系统）
    decision-card.tsx, competitor-card.tsx, system-pulse.tsx,
    ai-chat-panel.tsx, dashboard-header.tsx, dashboard-footer.tsx

Step 2: 重写 dashboard-client.tsx
    - 替换 7 模块 → 3 卡片
    - I18N 字典新增/裁剪
    - 数据 fetch 逻辑不变

Step 3: 重写 app/page.tsx（Landing Page）
    - 7 段结构
    - 英文内容

Step 4: 新建 /reports/ 页面
    - page.tsx（列表）+ [date]/page.tsx（详情）

Step 5: 新建 /login/ + middleware

Step 6: 清理
    - 删除 6 个旧组件
    - 删除 public/dashboard/index.html（旧版 3800 行 HTML）
    - 清理 dashboard.css 中未使用的样式
```

每步独立提交。Dashboard JSON 数据格式不变，Python 后端零改动。

---

## 11. 设计系统约束

继续使用 `public/_ds/` 中的 design tokens：
- `tokens.css`（CSS 变量：颜色、间距、字体、圆角、动画）
- `base.css`（reset + 排版）
- `components.css`（通用组件：按钮、卡片、标签）

**关键视觉原则**（Material Design）：
- 纯粹性：靠间距和字重建立层级，非边框和阴影
- 自然过渡：`duration-200 ease-out`，严禁突变
- 不引入新颜色变量，全部使用现有 tokens

### 11.1 新增 CSS 范围

Dashboard 卡片样式新建 `app/dashboard/dashboard-cards.css`（约为 `dashboard.css` 的 30%，约 200 行），不再依赖 `public/_ds/dashboard.css`。

主要原因：旧 `dashboard.css` 包含 7 模块的全部样式（表格、Chart 包装器、机会看板、下注抽屉等），大量样式规则新 Dashboard 不再需要。

---

## 12. 不做的优化（有意识的选择）

1. **AI 对话在 MVP 阶段不实现** — 卡片体验本身已充分差异化，AI Chat API 在卡片上线后作为 v2 功能
2. **不建用户系统** — 当前就一个用户，密码门足够
3. **不改变数据格式** — `dashboard.json` 保持现状，减少后端改动
4. **不做实时更新** — 每日批处理是正确的节奏
5. **不接入支付** — 现阶段手动处理订阅
6. **不重新设计设计系统** — 现有 tokens 充分，只新增卡片级 CSS
