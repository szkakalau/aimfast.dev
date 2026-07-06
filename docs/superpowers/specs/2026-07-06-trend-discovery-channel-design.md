# Trend Discovery Channel — Design Spec

**Date**: 2026-07-06
**Status**: Draft
**Context**: 基于 EarlyTerms 分析，为 AimFast.Dev 新增「趋势发现」频道

---

## 1. 战略定位

### 1.1 产品角色

趋势频道（`/trends/`）是 AimFast.Dev 的**免费获客层**。它不是独立产品，而是 SEO 驱动的内容营销资产，通过高质量的趋势研究报告吸引独立开发者流量，转化为 Dashboard 订阅用户（$19/mo）。

### 1.2 核心差异化 vs EarlyTerms

| 维度 | EarlyTerms | AimFast Trends |
|------|-----------|----------------|
| 目标用户 | 通用（创业者、营销人） | 聚焦独立开发者 |
| 术语来源 | 公开信源 | 复用 AimFast 的 13 信源管道 |
| 研究报告 | 人工审核 | LLM 自动生成（低分跳过） |
| 变现模式 | 独立订阅 | 免费 → 转化 Dashboard |
| 数据深度 | 通用术语解释 | 每个词附带「Product ideas」和「Commercial opportunities」 |

### 1.3 转化漏斗

```
Google/Bing 搜索 → /trends/claude-science/ (免费、SEO 优化)
  ↓
/trends/ 浏览更多趋势词 (免费，无需登录)
  ↓
内容价值认可 → Landing Page signup
  ↓
14-day free trial → $19/mo Dashboard
```

每个趋势页面底部都有 CTA：「Get daily intel like this → Start free trial」。

---

## 2. 数据层设计

### 2.1 唯一数据源：`tracking/trend_terms.json`

```
tracking/
  trend_terms.json    ← 趋势词累积追踪（新增）
  competitor_targets.json
  opportunities.json
  ...
```

### 2.2 数据模型

```typescript
interface TrendTerm {
  id: string;                  // "trend-claude-science" — slug 来源
  canonical: string;           // "Claude Science" — 规范化名称
  aliases: string[];           // ["ClaudeScience", "Claude Science"]
  first_seen: string;          // "2026-06-30"
  last_seen: string;           // "2026-07-06"
  stage: "nascent" | "emergent" | "validating" | "rising";
  score: number;               // 0-100
  source_count: number;        // 出现在几个不同信源
  total_mentions: number;      // 总提及次数
  sources: string[];           // ["GitHub", "Hacker News", "Reddit", "Twitter/X"]
  growth_pct: number;          // 7 天增长率
  category: string;            // "AI/LLM" | "DevTools" | "Infrastructure" | ...
  tags: string[];              // ["anthropic", "ai-tools"]
  summary_zh: string;          // 一句话中文摘要
  summary_en: string;          // 一句话英文摘要
  research_md_path: string;    // "content/trends/claude-science.md"
}

interface TrendTermsData {
  updated_at: string;          // ISO 8601
  terms: TrendTerm[];
}
```

### 2.3 Stage 计算（按年龄，非搜索量）

| 年龄 | Stage | 含义 |
|------|-------|------|
| 0-7 天 | `nascent` | 刚出现，需持续观察 |
| 8-30 天 | `emergent` | 多信源验证中 |
| 31-90 天 | `validating` | 方向确认 |
| 90+ 天 | `rising` | 已成趋势 |

年龄 = `today - first_seen`，每天 pipeline 运行时重新计算。

### 2.4 Score 计算

复用现有 E-P-A 7 维评分体系，调整权重：

| 维度 | 权重 | 原因 |
|------|------|------|
| freshness | 30% | 趋势频道的核心价值是「新」 |
| cross_platform | 25% | 多平台验证 = 更可能是真实趋势 |
| volume | 15% | 提及总量 |
| actionability | 10% | 是否可 build |
| buyer_clarity | 10% | 谁在关注 |
| consumer_appeal | 5% | C 端关注度 |
| problem_clarity | 5% | 痛点明确度 |

---

## 3. Pipeline 设计

### 3.1 新增步骤：`scripts/generate_trends.py`

在 `daily_run.sh` 的 Step 3（generate_report.py）之后、Step 5（generate_action.py）之前插入。

```
现有 signals.json (已处理、已打分)
    ↓
Step 3.5: generate_trends.py
    ↓ Phase 1: 术语抽取
    LLM 从今日 signals 中提取新术语/概念/产品名
    过滤：近 30 天内首次出现 + 排除通用词汇
    ↓ Phase 2: 合并 & 更新
    与 tracking/trend_terms.json 合并：
      - 新词 → 追加
      - 已有词 → 更新 last_seen、mentions、score、重新计算 stage
    ↓ Phase 3: 研究报告生成
    对 score > 60 且 research_md_path 为空的词
    → LLM 生成研究报告 → 写入 content/trends/{slug}.md
    ↓ Phase 4: 持久化
    更新 tracking/trend_terms.json
```

### 3.2 术语抽取 Prompt 模板

```
从以下今日采集的 signals 中提取新兴技术术语、产品名、或概念。

规则：
1. 只提取近 30 天内首次出现的词
2. 忽略已知通用词汇（如 "AI", "React", "Python"）
3. 每个词返回：canonical 名称、category、一句话摘要（中/英）

Signals:
{signals_json}
```

### 3.3 研究报告 Prompt 模板

新文件 `templates/trend_research_prompt.md`，包含 8 个板块结构（见 4.2）。

### 3.4 不新增采集器

v1 完全复用现有 13 个 collector。术语抽取在「已处理 signals」上做。

---

## 4. 前端设计

### 4.1 路由

| 路由 | 文件 | 渲染 |
|------|------|------|
| `/trends/` | `app/trends/page.tsx` | Server Component, static export |
| `/trends/[slug]/` | `app/trends/[slug]/page.tsx` | Server Component, generateStaticParams |
| `/trends/[slug]/en/` | `app/trends/[slug]/en/page.tsx` | Server Component |

### 4.2 趋势列表页 (`/trends/`)

**Hero 区**：
- h1: "Discover What's Emerging — Before Everyone Else"
- 副标题: "Daily tracking of new tech terms, concepts, and market signals. Free. No signup required."
- 数据徽章: "Tracking 47 terms · 12 new this week · Updated daily 08:30 CST"
- 顶栏导航：Header 里增加 "Trends" 链接（和 Dashboard、Reports 并列）

**Stage 筛选栏**（4 tab）：
- All · Nascent (0-7d) · Emergent (8-30d) · Validating (31-90d) · Rising (90d+)

**趋势词网格**（3 列 → 响应式缩为 2 → 1）：

每个卡片：
- Stage 徽章（nascent = 绿色 + 脉冲动画，emergent = 黄色，validating = 蓝色，rising = 紫色）
- canonical 名称（h3 加粗）
- summary_zh（一行截断）
- 底部元数据：first_seen + source_count sources + total_mentions mentions + score

**底部 CTA section**：
- "Every morning, our Discovery Engine scans 11+ sources and distills signals like these into one actionable decision." → Start free trial 按钮

### 4.3 趋势详情页 (`/trends/[slug]/`)

**面包屑**：`← Back to all trends`

**Hero**：
- Stage badge + canonical（h1）
- 指标行：First seen · Last seen · Score · N sources · N mentions · Growth +X%
- 来源图标行：各 source 的 badge

**研究报告**（AI 生成 Markdown 渲染），8 个板块：

1. **What is it** — 术语/概念定义
2. **Why now** — 为什么这个时间点出现
3. **Who's behind it** — 相关公司/人物
4. **Market signals** — 跨平台数据
5. **Commercial opportunities** — 商业化可能
6. **Related terms** — 相关趋势词（交叉链接）
7. **SEO opportunity** — 关键词搜索量
8. **Product ideas** — 适合 build 什么

**侧边栏**（桌面端 sticky，平板以下内联）：
- 概况卡片：「Tracking X terms daily. This is one of them.」
- CTA：「Get the full picture — competitor intel, daily decisions.」
- → Start free trial 按钮

**底部 CTA banner**：和列表页一致

### 4.4 SEO

- 每个趋势页独立 `<title>`：`{canonical} — Trend Report | AimFast.Dev`
- 独立 `<meta description>`：使用 summary_en
- `generateStaticParams` 从 `trend_terms.json` 读取所有 `id`
- 面包屑 `BreadcrumbList` structured data
- 列表页 `ItemList` structured data
- `/trends/` sitemap 注册

---

## 5. 样式设计

### 5.1 架构

新建 `app/trends/trends.css`，在 `app/layout.tsx` 中 import。复用现有 `public/_ds/tokens.css` 的 CSS 变量。

### 5.2 新增语义色

```css
:root {
  --stage-nascent:    oklch(60% 0.18 160);
  --stage-emergent:   oklch(65% 0.16 80);
  --stage-validating: oklch(55% 0.15 250);
  --stage-rising:     oklch(50% 0.18 290);
}
```

### 5.3 设计原则

- 卡片使用 multi-layer shadow（和现有 `.card` 一致）
- 标题 Fira Sans bold
- JetBrains Mono 仅用于 stage badge、日期、分数、meta 数据
- Icon 用 Lucide React
- Hero 径向渐变光晕（和首页 `.hero::before` 同模式）
- hover 浮起 + 阴影加深
- 动画 `duration-200 ease-out`

### 5.4 响应式

- 列表网格：`grid-template-columns: repeat(3, 1fr)` → 平板 `repeat(2, 1fr)` → 手机 `1fr`（和 `.pain-grid` 一致）
- 详情页侧边栏：桌面 sticky → 平板 inline

---

## 6. 种子数据

上线时手动准备 5-8 个趋势词 + 完整研究报告，从现有 historical signals 中回溯提取。确保页面不是空的。

---

## 7. v1 实现范围

### 要做（9 个文件）

**前端**：
- `app/trends/page.tsx` — 趋势列表页
- `app/trends/[slug]/page.tsx` — 趋势详情页
- `app/trends/[slug]/en/page.tsx` — 英文版详情页
- `app/trends/trends.css` — 频道样式

**修改**：
- `app/globals.css` — 引入 trends.css
- `app/layout.tsx` — 导航栏加 Trends 入口

**数据层**：
- `scripts/generate_trends.py` — 术语抽取 + 追踪 + 报告生成
- `tracking/trend_terms.json` — 种子数据（5-8 个词）

**模板**：
- `templates/trend_research_prompt.md` — 研究报告生成 prompt

### 不做

- 独立信源管道
- 实时更新（跟 daily pipeline 节奏）
- 用户自定义追踪
- 趋势预测/forecast
- 登录/收藏/订阅
- 改动现有 Dashboard 或 landing page

---

## 8. 后续演进（v2/v3 方向）

- v2：术语抽取从「LLM 日结」升级为「持续累积追踪」— stage 演进、score 变化的时间线视图
- v2：Embedding + Alias Table 的自动去重
- v3：独立信源管道（Google Trends API, Twitter/X API）
- v3：Trend forecast + Product opportunity scoring
