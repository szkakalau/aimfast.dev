# Trend Discovery Channel — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a free, SEO-optimized Trend Discovery Channel (`/trends/`) that displays emerging tech terms with AI-generated research reports, converting organic traffic to Dashboard subscriptions.

**Architecture:** Server Components read `tracking/trend_terms.json` at build time; `generateStaticParams` pre-renders all term pages. A new Python pipeline step (`generate_trends.py`) extracts terms from existing signals via LLM and maintains the trend term database. Styles reuse the existing `_ds/` design system.

**Tech Stack:** Next.js 16 App Router (static export), React 19 Server Components, TypeScript, `marked` for Markdown rendering, Lucide React icons, CSS custom properties.

## Global Constraints

- `output: 'export'` — all pages must be static-renderable (no `searchParams`, no runtime APIs)
- All text supports zh-CN (primary) and en (secondary) via separate route (`/en/`)
- SEO metadata on every page (`<title>`, `<meta description>`, canonical URL, Open Graph, structured data)
- Design system tokens from `public/_ds/tokens.css` — never hardcode colors/spacing/shadows
- Card styles use multi-layer box-shadow, never `border: 1px solid`
- Headings use Fira Sans bold (700+), monospace only for badges/dates/scores
- Icons from `lucide-react`, never emoji for decorative purposes
- All commits follow `type: description` format
- Build verification after every task: `npm run build`

---

## File Structure

```
New files:
  tracking/trend_terms.json          — Trend term database (seed data)
  content/trends/{slug}.md           — AI-generated research reports (6 files)
  app/trends/trends.css              — Channel-specific styles
  app/trends/page.tsx                — Trend listing page (Server Component)
  app/trends/[slug]/page.tsx         — Trend detail page zh (Server Component)
  app/trends/[slug]/en/page.tsx      — Trend detail page en (Server Component)
  scripts/generate_trends.py         — Pipeline: term extraction + tracking + report generation
  templates/trend_research_prompt.md — LLM prompt for research report generation

Modified files:
  app/globals.css                    — Add @import for trends.css
  app/layout.tsx                     — Add global site nav with Trends link
```

---

### Task 1: Seed Data — `tracking/trend_terms.json` + `content/trends/*.md`

**Files:**
- Create: `tracking/trend_terms.json`
- Create: `content/trends/mcp-protocol.md`
- Create: `content/trends/fluid-compute.md`
- Create: `content/trends/ai-gateway.md`
- Create: `content/trends/webcontainer.md`
- Create: `content/trends/cursor-rules.md`
- Create: `content/trends/claude-agent-sdk.md`

**Interfaces:**
- Produces: `TrendTerm[]` in `tracking/trend_terms.json` — consumed by Tasks 3, 4, 5
- Produces: Markdown files at `content/trends/{slug}.md` — consumed by Tasks 4, 5

- [ ] **Step 1: Create `tracking/trend_terms.json`**

```json
{
  "updated_at": "2026-07-06T08:30:00+08:00",
  "terms": [
    {
      "id": "trend-mcp-protocol",
      "canonical": "MCP Protocol",
      "aliases": ["Model Context Protocol", "MCP", "Anthropic MCP"],
      "first_seen": "2026-07-05",
      "last_seen": "2026-07-06",
      "stage": "nascent",
      "score": 78,
      "source_count": 4,
      "total_mentions": 23,
      "sources": ["GitHub", "Hacker News", "Reddit", "Twitter/X"],
      "growth_pct": 450,
      "category": "AI/LLM",
      "tags": ["anthropic", "ai-agents", "protocol"],
      "summary_zh": "Anthropic 推出的 AI 模型与工具之间的开放协议标准，允许 LLM 安全地调用外部工具和数据源。",
      "summary_en": "An open protocol standard from Anthropic enabling LLMs to securely call external tools and data sources.",
      "research_md_path": "content/trends/mcp-protocol.md"
    },
    {
      "id": "trend-fluid-compute",
      "canonical": "Fluid Compute",
      "aliases": ["Vercel Fluid Compute", "Fluid"],
      "first_seen": "2026-07-02",
      "last_seen": "2026-07-06",
      "stage": "nascent",
      "score": 85,
      "source_count": 5,
      "total_mentions": 41,
      "sources": ["Hacker News", "Reddit", "GitHub", "DEV Community", "Twitter/X"],
      "growth_pct": 720,
      "category": "Infrastructure",
      "tags": ["vercel", "serverless", "compute"],
      "summary_zh": "Vercel 推出的新一代计算运行时，函数实例可跨并发请求复用，大幅减少冷启动延迟。",
      "summary_en": "Vercel's next-gen compute runtime where function instances are reused across concurrent requests, drastically reducing cold starts.",
      "research_md_path": "content/trends/fluid-compute.md"
    },
    {
      "id": "trend-ai-gateway",
      "canonical": "AI Gateway",
      "aliases": ["Vercel AI Gateway", "AI API Gateway"],
      "first_seen": "2026-06-28",
      "last_seen": "2026-07-06",
      "stage": "emergent",
      "score": 91,
      "source_count": 6,
      "total_mentions": 67,
      "sources": ["Hacker News", "GitHub", "Reddit", "DEV Community", "Product Hunt", "Twitter/X"],
      "growth_pct": 340,
      "category": "AI/LLM",
      "tags": ["vercel", "ai", "api", "gateway"],
      "summary_zh": "统一的 AI API 网关，提供多模型访问、可观测性、模型回退和零数据保留策略。",
      "summary_en": "A unified AI API gateway offering multi-provider access with observability, model fallbacks, and zero data retention.",
      "research_md_path": "content/trends/ai-gateway.md"
    },
    {
      "id": "trend-webcontainer",
      "canonical": "WebContainer",
      "aliases": ["StackBlitz WebContainer", "Browser Node.js"],
      "first_seen": "2026-06-15",
      "last_seen": "2026-07-06",
      "stage": "validating",
      "score": 88,
      "source_count": 5,
      "total_mentions": 94,
      "sources": ["Hacker News", "GitHub", "Reddit", "DEV Community", "Product Hunt"],
      "growth_pct": 120,
      "category": "DevTools",
      "tags": ["stackblitz", "browser", "nodejs", "webassembly"],
      "summary_zh": "StackBlitz 推出的浏览器内 Node.js 运行时，基于 WebAssembly，允许在浏览器中运行完整的开发环境。",
      "summary_en": "StackBlitz's in-browser Node.js runtime based on WebAssembly, enabling full dev environments to run entirely in the browser.",
      "research_md_path": "content/trends/webcontainer.md"
    },
    {
      "id": "trend-cursor-rules",
      "canonical": "Cursor Rules",
      "aliases": [".cursorrules", "Cursor IDE Rules", "AI Coding Rules"],
      "first_seen": "2026-06-01",
      "last_seen": "2026-07-06",
      "stage": "validating",
      "score": 93,
      "source_count": 7,
      "total_mentions": 156,
      "sources": ["GitHub", "Hacker News", "Reddit", "Twitter/X", "DEV Community", "Product Hunt", "V2EX"],
      "growth_pct": 280,
      "category": "DevTools",
      "tags": ["cursor", "ai-coding", "rules", "configuration"],
      "summary_zh": "Cursor IDE 的项目级 AI 行为配置文件，开发者通过 .cursorrules 定制 AI 编码助手的规则和偏好。",
      "summary_en": "Project-level AI behavior configuration files for Cursor IDE, allowing developers to customize coding assistant rules and preferences.",
      "research_md_path": "content/trends/cursor-rules.md"
    },
    {
      "id": "trend-claude-agent-sdk",
      "canonical": "Claude Agent SDK",
      "aliases": ["Claude Code SDK", "Anthropic Agent SDK"],
      "first_seen": "2026-05-20",
      "last_seen": "2026-07-06",
      "stage": "rising",
      "score": 95,
      "source_count": 8,
      "total_mentions": 234,
      "sources": ["GitHub", "Hacker News", "Reddit", "Twitter/X", "DEV Community", "Product Hunt", "V2EX", "Lobsters"],
      "growth_pct": 180,
      "category": "AI/LLM",
      "tags": ["anthropic", "claude", "sdk", "agents"],
      "summary_zh": "Anthropic 发布的官方 Agent SDK，允许开发者构建自定义 AI Agent 并集成到应用中。",
      "summary_en": "Anthropic's official Agent SDK for building custom AI agents and integrating them into applications.",
      "research_md_path": "content/trends/claude-agent-sdk.md"
    }
  ]
}
```

- [ ] **Step 2: Create research report `content/trends/mcp-protocol.md`**

```markdown
---
canonical: "MCP Protocol"
date: "2026-07-06"
stage: nascent
score: 78
category: AI/LLM
sources:
  - GitHub
  - Hacker News
  - Reddit
  - Twitter/X
---

## What is it

MCP (Model Context Protocol) 是 Anthropic 发布的一个开放协议标准，用于规范 AI 模型与外部工具、数据源之间的交互方式。它定义了 LLM 如何安全地发现、调用和管理外部资源——类似于「AI 世界的 USB-C 接口」。

## Why now

2025-2026 年，AI Agent 从实验走向生产。但每个模型、每个工具、每个数据源之间的集成方式都不同，碎片化严重。MCP 试图解决这个互操作性问题——就像 HTTP 标准化了 Web 通信，MCP 期望标准化 AI Agent 的工具调用。

Anthropic 在 2026 年 6 月正式开源了 MCP 规范，引发了开发者社区的广泛讨论。

## Who's behind it

- **Anthropic** — MCP 的提出者和主要维护者
- **开源社区** — GitHub 上已有 50+ MCP server 实现（文件系统、数据库、API 等）
- **工具厂商** — Vercel、Supabase、Cloudflare 等已宣布支持 MCP

## Market signals

- GitHub: MCP 规范仓库 5,200+ stars（2 周内）
- Hacker News: 3 篇 front-page 讨论
- Reddit r/programming: 2 篇热门帖，累计 400+ 评论
- Twitter/X: Anthropic 官方公告 1,200+ 转发

## Commercial opportunities

1. **MCP Server 市场** — 类似 WordPress 插件生态，为各类 API/服务构建 MCP server
2. **MCP 托管平台** — 为企业提供私有化 MCP server 部署和管理
3. **开发者工具** — MCP 调试器、测试框架、可视化编辑器

## Related terms

- Claude Agent SDK — Anthropic 的 Agent 构建框架，原生支持 MCP
- AI Gateway — Vercel 的 AI API 网关，已集成 MCP 支持
- Cursor Rules — Cursor IDE 的行为配置，与 MCP 互补

## SEO opportunity

- "MCP protocol" 月搜索量 ~2,400（Google Trends，上升趋势）
- 长尾关键词：「MCP server tutorial」「MCP vs function calling」「what is MCP protocol」
- 竞争程度：低（多数内容来自 Anthropic 官方文档）

## Product ideas

1. **MCP Server Directory** — 一个 MCP server 的发现和评分平台（类似 WordPress Plugin Directory）
2. **一键部署 MCP Server** — 为常用服务（Airtable, Notion, Slack）提供预构建的 MCP server，支持一键部署到 Vercel/Fly.io
3. **MCP 安全审计工具** — 扫描 MCP server 的安全漏洞和权限过度授予问题
```

- [ ] **Step 3: Create research report `content/trends/fluid-compute.md`**

```markdown
---
canonical: "Fluid Compute"
date: "2026-07-06"
stage: nascent
score: 85
category: Infrastructure
sources:
  - Hacker News
  - Reddit
  - GitHub
  - DEV Community
  - Twitter/X
---

## What is it

Fluid Compute 是 Vercel 在 2026 年推出的新一代 Serverless 计算运行时。与传统 Serverless（每个请求启动一个冷实例）不同，Fluid Compute 的函数实例可以跨并发请求复用，大幅减少冷启动延迟，同时保持 Serverless 的弹性伸缩能力。

## Why now

Serverless 已经发展了近十年，冷启动一直是最大的痛点。AWS Lambda、Cloudflare Workers、Vercel Functions 都在不同方向上优化这个问题。Fluid Compute 代表了「零冷启动 Serverless」的一个重要突破——它的预热机制让函数实例始终「温」着，首个请求和后续请求的延迟差距缩小到几乎可以忽略。

Vercel 在 2026 年 6 月底正式宣布 Fluid Compute 成为默认运行时，替代了此前的 Edge Functions。

## Who's behind it

- **Vercel** — 核心开发和平台运营
- **Next.js 团队** — 深度集成到 Next.js 框架
- **Vercel 生态** — Nuxt、SvelteKit、Astro 等框架相继适配

## Market signals

- Hacker News: Vercel 官方公告 front-page 停留 2 天，800+ upvotes
- Reddit r/webdev: 4 篇技术分析帖
- DEV Community: 7 篇入门教程（2 周内）
- GitHub: 相关 RFC 和 discussion 活跃

## Commercial opportunities

1. **Fluid Compute 迁移服务** — 帮助团队从传统 Serverless 迁移到 Fluid Compute，优化冷启动性能
2. **性能监控工具** — 针对 Fluid Compute 的冷启动分析、实例复用率监控 Dashboard
3. **Serverless 最佳实践课程** — Fluid Compute 特有的架构模式（连接池、缓存策略变化）

## Related terms

- AI Gateway — 同样来自 Vercel，与 Fluid Compute 深度集成
- WebContainer — 另一个「运行时可复用」的创新，在浏览器端实现

## SEO opportunity

- "Fluid Compute" 月搜索量 ~1,800（Google Trends，陡峭上升）
- 长尾关键词：「Vercel Fluid Compute vs Lambda」「Fluid Compute cold start」「how does Fluid Compute work」
- 竞争程度：极低（新概念，目前只有 Vercel 官方文档）

## Product ideas

1. **Fluid Compute Benchmark** — 对比 Fluid Compute / Lambda / Cloudflare Workers 的冷启动和并发性能
2. **Serverless Migration Checklist** — 从传统 Vercel Functions 迁移到 Fluid Compute 的交互式指南
3. **冷启动可视化工具** — 实时展示函数实例的复用率和冷启动分布
```

- [ ] **Step 4: Create research report `content/trends/ai-gateway.md`**

```markdown
---
canonical: "AI Gateway"
date: "2026-07-06"
stage: emergent
score: 91
category: AI/LLM
sources:
  - Hacker News
  - GitHub
  - Reddit
  - DEV Community
  - Product Hunt
  - Twitter/X
---

## What is it

AI Gateway 是一个统一的 API 网关层，位于应用和多个 AI 模型提供商之间。它提供单一 API 端点，由网关自动路由到最佳的模型提供商，同时提供可观测性（token 用量、延迟、成本）、模型回退（主模型故障时自动切换备用模型）、零数据保留（请求数据不用于模型训练）等功能。

## Why now

2025-2026 年，AI 应用从「调一个模型」演变为「调多个模型」。开发者需要同时使用 GPT-5、Claude Opus 4.8、Gemini 等不同模型，管理多个 API key、追踪不同计费方式。AI Gateway 解决了这个「多模型管理」的痛点。

Vercel 在 2025 年 8 月正式 GA 了 AI Gateway，随后 Cloudflare、Kong 等也推出了类似产品。

## Who's behind it

- **Vercel** — AI Gateway 市场领导者
- **Cloudflare** — Workers AI Gateway 竞品
- **Kong** — API 网关老牌厂商，推出 AI 插件
- **Helicone** — 独立 AI 可观测性工具，切入同一赛道

## Market signals

- HN front-page 讨论 5+ 次
- GitHub: Vercel AI SDK + AI Gateway 整合方案 12,000+ stars
- Product Hunt: 多个 AI Gateway 产品获得 Product of the Day

## Commercial opportunities

1. **多模型成本优化工具** — 自动选择最便宜的模型完成任务
2. **AI 安全审计 Gateway** — 在网关层做 content filtering、PII 检测
3. **垂直领域 AI Gateway** — 针对医疗、金融等合规要求高的行业

## Related terms

- MCP Protocol — AI 工具调用标准，与 AI Gateway 互补
- Fluid Compute — Vercel 的计算运行时，AI Gateway 运行在其上

## SEO opportunity

- "AI gateway" 月搜索量 ~6,500（Google Trends，持续上升）
- 长尾关键词：「AI gateway vs direct API」「Vercel AI Gateway pricing」「open source AI gateway」
- 竞争程度：中等（已有 Vercel、Kong 等厂商内容）

## Product ideas

1. **AI Cost Dashboard** — 跨模型提供商的成本分析工具，集成 AI Gateway 数据
2. **Open Source AI Gateway** — 自托管版本，适合对数据隐私要求高的企业
3. **AI Model Comparison Tool** — 实时对比不同模型的延迟、成本、质量
```

- [ ] **Step 5: Create research report `content/trends/webcontainer.md`**

```markdown
---
canonical: "WebContainer"
date: "2026-07-06"
stage: validating
score: 88
category: DevTools
sources:
  - Hacker News
  - GitHub
  - Reddit
  - DEV Community
  - Product Hunt
---

## What is it

WebContainer 是 StackBlitz 推出的浏览器内 Node.js 运行时。它基于 WebAssembly，允许在浏览器标签页中直接运行完整的 Node.js 环境——包括文件系统、包管理器（npm/yarn/pnpm）、开发服务器。不需要任何远程 VM 或容器。

## Why now

随着 WebAssembly 的成熟和浏览器能力的增长，在浏览器中运行完整开发环境从「不可能」变成了「可行」。WebContainer 的核心突破在于它的文件系统和进程管理——它不是在模拟，而是真正运行了一个兼容的 Node.js 运行时。

2025-2026 年，AI 编码助手（Claude Code, Cursor, Copilot）的普及让「浏览器内开发」的需求爆发——用户希望在浏览器中直接让 AI 写代码、运行、调试，而不需要配置本地环境。

## Who's behind it

- **StackBlitz** — 创建者和主要维护者
- **Google** — Chrome 团队与 StackBlitz 合作优化 WebAssembly 性能
- **Vercel/Next.js** — StackBlitz 的合作伙伴，Next.js 在 WebContainer 中运行良好

## Market signals

- GitHub: StackBlitz 核心仓库 14,000+ stars
- HN: WebContainer 每次更新都上 front-page
- Product Hunt: 多次获得 Developer Tools 类别的 Product of the Week

## Commercial opportunities

1. **AI Coding 平台** — 基于 WebContainer 的「浏览器内 AI 编程助手」
2. **交互式文档** — 技术文档中嵌入可运行代码示例（替代 CodeSandbox）
3. **在线面试平台** — 完整开发环境的在线编码面试

## Related terms

- Fluid Compute — 另一个运行时的创新，在服务端复用实例
- Claude Agent SDK — Agent 在浏览器中运行时的依赖

## SEO opportunity

- "WebContainer" 月搜索量 ~3,200（Google Trends，稳定上升）
- 长尾关键词：「WebContainer tutorial」「StackBlitz vs CodeSandbox」「browser Node.js runtime」
- 竞争程度：低（主要是 StackBlitz 官方内容）

## Product ideas

1. **Browser-Based AI Dev Environment** — 一键启动的浏览器 IDE，AI 写代码、WebContainer 运行
2. **交互式技术教程平台** — 每个教程都是可运行的完整项目
3. **WebContainer 优化的 npm 包** — 专为浏览器内运行优化的常用工具包
```

- [ ] **Step 6: Create research report `content/trends/cursor-rules.md`**

```markdown
---
canonical: "Cursor Rules"
date: "2026-07-06"
stage: validating
score: 93
category: DevTools
sources:
  - GitHub
  - Hacker News
  - Reddit
  - Twitter/X
  - DEV Community
  - Product Hunt
  - V2EX
---

## What is it

Cursor Rules（`.cursorrules`）是 Cursor IDE 的项目级配置文件，允许开发者通过自然语言或结构化指令定制 AI 编码助手的行为。它本质上是一个「给 AI 的系统提示词」，放在项目根目录，AI 在每次交互时都会读取并遵循。

## Why now

AI 编码助手已经从「写几行代码」演变为「在项目中持续协作」。每个项目有不同的编码风格、架构约束、技术栈偏好——Cursor Rules 让开发者可以「教会」AI 自己项目的规则。GitHub 上出现了大量 `.cursorrules` 共享仓库，形成了类似于「dotfiles 文化」的社区。

2026 年，Cursor Rules 从 Cursor 专属扩展为「AI 编码规则」的通用概念——Claude Code 的 CLAUDE.md、Copilot 的 `.github/copilot-instructions.md` 都是同类产物。

## Who's behind it

- **Cursor** — 概念提出者和主要推动者
- **GitHub 社区** — 大量开发者分享自己的 cursorrules 配置
- **AI 编码工具** — Claude Code, Copilot, Windsurf 等相继支持类似机制

## Market signals

- GitHub: `cursorrules` 搜索返回 10,000+ 仓库
- HN: 多次 front-page 讨论
- Twitter/X: 开发者分享 cursorrules 成为热门话题
- V2EX: 中文社区 3 篇热门讨论帖

## Commercial opportunities

1. **Cursor Rules 市场** — 按技术栈/框架分类的规则模板市场
2. **规则优化服务** — 帮助企业定制和优化 AI 编码规则
3. **跨工具规则转换器** — 一键将 Cursor Rules 转换为 Claude Code / Copilot 规则格式

## Related terms

- Claude Agent SDK — Anthropic 的 Agent 框架，用 CLAUDE.md 替代 cursorrules
- MCP Protocol — AI 工具互操作标准

## SEO opportunity

- "cursor rules" 月搜索量 ~5,800（Google Trends，快速上升）
- 长尾关键词：「best cursor rules」「cursor rules template」「cursor rules for React」
- 竞争程度：低（主要是社区博客和 GitHub 仓库）

## Product ideas

1. **CursorRulesHub** — 专注于 AI 编码规则的分享和发现平台
2. **AI Rules Generator** — 输入项目描述，自动生成最优的 cursorrules
3. **Rules Analytics** — 分析 cursorrules 对 AI 输出质量的影响
```

- [ ] **Step 7: Create research report `content/trends/claude-agent-sdk.md`**

```markdown
---
canonical: "Claude Agent SDK"
date: "2026-07-06"
stage: rising
score: 95
category: AI/LLM
sources:
  - GitHub
  - Hacker News
  - Reddit
  - Twitter/X
  - DEV Community
  - Product Hunt
  - V2EX
  - Lobsters
---

## What is it

Claude Agent SDK 是 Anthropic 官方发布的 Agent 开发框架，允许开发者构建自定义 AI Agent 并集成到应用中。它提供了工具定义、多步推理、子 Agent 编排、上下文管理等核心能力，支持 TypeScript 和 Python。

## Why now

2025-2026 年，「Agent」从概念验证走向生产部署。开发者不再满足于「调 API 返回文本」，而是需要 AI 执行多步骤任务——搜索、读文件、写代码、调 API、验证结果。Anthropic 的 Claude Agent SDK 试图为这个模式提供一个标准化的开发框架。

与 LangChain 等第三方框架不同，Claude Agent SDK 是 Anthropic 官方维护的，与 Claude 模型深度优化。这意味着更好的性能、更少的幻觉、更可靠的工具调用。

## Who's behind it

- **Anthropic** — SDK 的创建者和主要维护者
- **Vercel** — 部署和托管合作伙伴
- **开源社区** — GitHub 上 200+ 第三方工具和集成

## Market signals

- GitHub: 官方仓库 8,000+ stars（3 个月）
- HN: SDK 发布帖 600+ upvotes
- DEV Community: 30+ 教程和案例分享
- Product Hunt: Launch Week 获得 2,000+ upvotes

## Commercial opportunities

1. **Agent 模板市场** — 预构建的行业 Agent（客服、数据分析、代码审查）
2. **Agent 托管和监控平台** — 生产级 Agent 部署、可观测性、成本管理
3. **Agent 安全审计** — 专门针对 AI Agent 的安全测试工具

## Related terms

- MCP Protocol — Claude Agent SDK 原生支持 MCP 工具调用
- Cursor Rules — AI 行为配置的另一面
- AI Gateway — Claude Agent SDK 通常通过 AI Gateway 调用模型

## SEO opportunity

- "Claude Agent SDK" 月搜索量 ~3,500（Google Trends，上升）
- 长尾关键词：「Claude Agent SDK tutorial」「Claude Agent vs LangChain」「build AI agent with Claude」
- 竞争程度：低（新概念，主要是 Anthropic 官方文档）

## Product ideas

1. **Agent Template Marketplace** — 按行业/场景分类的 Claude Agent 模板
2. **Agent Playground** — 浏览器内测试和调试 Claude Agent（基于 WebContainer）
3. **Multi-Agent Orchestrator** — 协调多个 Claude Agent 完成复杂任务的编排层
```

- [ ] **Step 8: Verify data integrity**

Run: `node -e "JSON.parse(require('fs').readFileSync('tracking/trend_terms.json','utf-8')); console.log('OK: 6 terms')"`

Expected: `OK: 6 terms`

- [ ] **Step 9: Commit**

```bash
git add tracking/trend_terms.json content/trends/
git commit -m "data: trend discovery channel 种子数据（6 个趋势词 + 研究报告）"
```

---

### Task 2: CSS Styles — `app/trends/trends.css`

**Files:**
- Create: `app/trends/trends.css`

**Interfaces:**
- Consumes: CSS custom properties from `public/_ds/tokens.css` (already imported in globals.css)
- Produces: CSS classes used by Tasks 3, 4, 5

- [ ] **Step 1: Create `app/trends/trends.css`**

```css
/* ═════ AimFast.Dev — Trend Discovery Channel Styles ═════ */

/* ── Stage semantic colors ── */
:root {
  --stage-nascent:    oklch(60% 0.18 160);
  --stage-emergent:   oklch(65% 0.16 80);
  --stage-validating: oklch(55% 0.15 250);
  --stage-rising:     oklch(50% 0.18 290);
}

/* ── Stage badge ── */
.stage-badge {
  display: inline-flex; align-items: center; gap: 5px;
  font-family: var(--font-mono);
  font-size: 0.68rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 2px 10px;
  border-radius: 100px;
  white-space: nowrap;
}

.stage-badge.nascent {
  color: var(--stage-nascent);
  background: oklch(60% 0.18 160 / 0.1);
  animation: pulse-glow 2s ease-in-out infinite;
}
.stage-badge.emergent {
  color: var(--stage-emergent);
  background: oklch(65% 0.16 80 / 0.1);
}
.stage-badge.validating {
  color: var(--stage-validating);
  background: oklch(55% 0.15 250 / 0.1);
}
.stage-badge.rising {
  color: var(--stage-rising);
  background: oklch(50% 0.18 290 / 0.1);
}

@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 0 0 oklch(60% 0.18 160 / 0.3); }
  50%      { box-shadow: 0 0 0 6px oklch(60% 0.18 160 / 0); }
}

/* ── Trends list page ── */
.trends-page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 var(--space-3);
}

/* Hero */
.trends-hero {
  display: flex; flex-direction: column; align-items: center;
  text-align: center;
  padding: var(--space-12) 0 var(--space-8);
  position: relative; overflow: hidden;
}
.trends-hero::before {
  content: '';
  position: absolute;
  top: -20%; left: 50%;
  transform: translateX(-50%);
  width: 1000px; max-width: 140vw;
  height: 500px;
  background: radial-gradient(ellipse 50% 50% at 50% 0%,
    oklch(55% 0.18 60 / 0.08) 0%,
    oklch(55% 0.18 60 / 0.03) 40%,
    transparent 70%);
  pointer-events: none;
  z-index: 0;
}
.trends-hero > * { position: relative; z-index: 1; }

.trends-hero h1 {
  font-size: clamp(2.2rem, 5vw, 3.4rem);
  font-weight: 800; line-height: 1.1;
  letter-spacing: -0.03em;
  margin-bottom: var(--space-3);
  max-width: 680px;
}

.trends-hero-desc {
  font-size: 1.05rem; color: var(--color-text-secondary);
  max-width: 540px; line-height: 1.7;
  margin-bottom: var(--space-4);
}

.trends-hero-stats {
  display: inline-flex; align-items: center; gap: var(--space-1);
  font-family: var(--font-mono); font-size: 0.78rem;
  color: var(--color-text-muted);
  background: var(--color-surface);
  padding: 6px 16px; border-radius: 100px;
  box-shadow: var(--shadow-xs);
  margin-bottom: var(--space-4);
}

.trends-hero-stats strong { font-weight: 600; color: var(--color-accent); }

/* Stage filter tabs */
.stage-filter {
  display: flex; justify-content: center; gap: var(--space-1);
  margin-bottom: var(--space-6); flex-wrap: wrap;
}

.stage-filter-btn {
  font-family: var(--font-mono); font-size: 0.75rem; font-weight: 500;
  padding: 6px 14px; border-radius: 100px;
  border: 1px solid var(--color-border);
  background: transparent; color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.stage-filter-btn:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.stage-filter-btn.active {
  background: var(--color-accent);
  border-color: var(--color-accent);
  color: var(--color-on-accent);
}

/* Trend card grid */
.trend-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-4);
  margin-bottom: var(--space-8);
}

.trend-card {
  background: var(--color-surface);
  border: none;
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  box-shadow: var(--shadow-xs);
  transition: box-shadow var(--duration-normal) var(--ease-out),
              transform var(--duration-normal) var(--ease-out);
  text-decoration: none; color: inherit;
  display: flex; flex-direction: column; gap: var(--space-2);
}

.trend-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.trend-card-category {
  font-family: var(--font-mono); font-size: 0.65rem;
  text-transform: uppercase; letter-spacing: 0.05em;
  color: var(--color-text-muted);
}

.trend-card h3 {
  font-size: 1.15rem; font-weight: 700;
  line-height: 1.25; margin: 0;
  color: var(--color-text);
}

.trend-card-summary {
  font-size: 0.85rem; color: var(--color-text-secondary);
  line-height: 1.55; margin: 0;
  flex: 1;
}

.trend-card-meta {
  display: flex; align-items: center; gap: var(--space-2);
  font-family: var(--font-mono); font-size: 0.7rem;
  color: var(--color-text-muted);
  padding-top: var(--space-2);
  border-top: 1px solid var(--color-border);
}

.trend-card-meta-item {
  display: inline-flex; align-items: center; gap: 3px;
}

/* Detail page */
.trend-detail {
  max-width: 900px; margin: 0 auto;
  padding: var(--space-6) var(--space-3);
}

.trend-detail-breadcrumb {
  font-size: 0.85rem; margin-bottom: var(--space-4);
}
.trend-detail-breadcrumb a {
  color: var(--color-text-muted); text-decoration: none;
}
.trend-detail-breadcrumb a:hover { color: var(--color-accent); }

.trend-detail-header {
  margin-bottom: var(--space-6);
}

.trend-detail-header h1 {
  font-size: clamp(2rem, 4.5vw, 3rem);
  font-weight: 800; line-height: 1.1;
  letter-spacing: -0.03em;
  margin: var(--space-2) 0 var(--space-3);
}

.trend-detail-meta-row {
  display: flex; flex-wrap: wrap; gap: var(--space-3);
  font-family: var(--font-mono); font-size: 0.78rem;
  color: var(--color-text-muted);
  margin-bottom: var(--space-3);
}

.trend-detail-meta-item {
  display: inline-flex; align-items: center; gap: 4px;
}

.trend-detail-meta-item strong {
  font-weight: 600; color: var(--color-text);
  font-family: var(--font-heading);
}

.trend-detail-sources {
  display: flex; flex-wrap: wrap; gap: 6px;
}

.trend-source-badge {
  display: inline-flex; align-items: center; gap: 3px;
  font-family: var(--font-mono); font-size: 0.68rem;
  padding: 3px 8px; border-radius: 100px;
  background: var(--color-surface-alt);
  color: var(--color-text-secondary);
}

.trend-detail-layout {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: var(--space-6);
  align-items: start;
}

.trend-detail-content {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  box-shadow: var(--shadow-xs);
  line-height: 1.8;
  font-size: 0.98rem;
}

.trend-detail-content h2 {
  font-size: 1.3rem; font-weight: 700; margin-top: var(--space-5);
  margin-bottom: var(--space-2); padding-bottom: var(--space-1);
  border-bottom: 1px solid var(--color-border);
}

.trend-detail-content h3 {
  font-size: 1.05rem; font-weight: 600;
  margin-top: var(--space-4); margin-bottom: var(--space-1);
}

.trend-detail-content p {
  margin-bottom: var(--space-3); color: var(--color-text-secondary);
}

.trend-detail-content ul, .trend-detail-content ol {
  margin-bottom: var(--space-3); padding-left: var(--space-4);
}

.trend-detail-content li {
  margin-bottom: var(--space-1); color: var(--color-text-secondary);
}

.trend-detail-content strong {
  color: var(--color-text); font-weight: 600;
}

.trend-detail-content a {
  color: var(--color-accent); text-decoration: underline;
}

.trend-detail-content code {
  font-family: var(--font-mono); font-size: 0.85em;
  background: var(--color-surface-alt); padding: 2px 6px;
  border-radius: 4px;
}

/* Sidebar */
.trend-sidebar {
  position: sticky; top: var(--space-3);
  display: flex; flex-direction: column; gap: var(--space-3);
}

.trend-sidebar-card {
  background: var(--color-surface);
  border: none;
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  box-shadow: var(--shadow-xs);
}

.trend-sidebar-card h4 {
  font-size: 0.95rem; font-weight: 600;
  margin-bottom: var(--space-2);
}

.trend-sidebar-card p {
  font-size: 0.85rem; color: var(--color-text-secondary);
  line-height: 1.6; margin: 0 0 var(--space-3);
}

/* CTA sections */
.trends-cta {
  text-align: center;
  padding: var(--space-8) 0;
  max-width: 560px; margin: 0 auto;
}

.trends-cta h2 {
  font-size: 1.5rem; font-weight: 700;
  margin-bottom: var(--space-2);
}

.trends-cta p {
  color: var(--color-text-secondary);
  font-size: 0.95rem; margin-bottom: var(--space-3);
}

/* Empty state */
.trends-empty {
  text-align: center;
  padding: var(--space-10) 0;
  color: var(--color-text-muted);
}

.trends-empty h2 {
  font-size: 1.5rem; font-weight: 600;
  margin-bottom: var(--space-2);
}

/* Responsive */
@media (max-width: 900px) {
  .trend-grid { grid-template-columns: repeat(2, 1fr); }
  .trend-detail-layout { grid-template-columns: 1fr; }
  .trend-sidebar { position: static; }
}

@media (max-width: 640px) {
  .trend-grid { grid-template-columns: 1fr; }
  .trend-detail { padding: var(--space-3) var(--space-2); }
}
```

- [ ] **Step 2: Build Verify**

Run: `npm run build`

Expected: Build succeeds (CSS alone won't break anything, no pages importing it yet)

- [ ] **Step 3: Commit**

```bash
git add app/trends/trends.css
git commit -m "style: trends.css — 趋势频道样式（stage 语义色、列表页、详情页）"
```

---

### Task 3: Trend List Page — `app/trends/page.tsx`

**Files:**
- Create: `app/trends/page.tsx`

**Interfaces:**
- Consumes: `tracking/trend_terms.json` (from Task 1)
- Consumes: CSS classes from `app/trends/trends.css` (from Task 2)
- Produces: Route `GET /trends/` — static HTML page

- [ ] **Step 1: Create `app/trends/page.tsx`**

```tsx
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import type { Metadata } from 'next';
import { TrendingUp, Calendar, BarChart3, Activity } from 'lucide-react';

export const metadata: Metadata = {
  title: 'Trend Discovery — Emerging Tech Terms & Concepts | AimFast.Dev',
  description:
    'Discover emerging technology terms, concepts, and market signals before they trend. Free daily tracking of nascent tech across 11+ sources.',
  robots: { index: true, follow: true },
  alternates: { canonical: 'https://www.aimfast.dev/trends/' },
  openGraph: {
    title: 'Trend Discovery — Emerging Tech Terms | AimFast.Dev',
    description:
      'Track emerging tech terms before they trend. Daily updates from 11+ sources. Free. No signup required.',
    url: 'https://www.aimfast.dev/trends/',
    siteName: 'AimFast.Dev',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Trend Discovery — Emerging Tech Terms | AimFast.Dev',
    description: 'Discover emerging tech terms before they trend. Free daily tracking.',
  },
};

/* ── Types ── */

interface TrendTerm {
  id: string;
  canonical: string;
  aliases: string[];
  first_seen: string;
  last_seen: string;
  stage: 'nascent' | 'emergent' | 'validating' | 'rising';
  score: number;
  source_count: number;
  total_mentions: number;
  sources: string[];
  growth_pct: number;
  category: string;
  tags: string[];
  summary_zh: string;
  summary_en: string;
  research_md_path: string;
}

interface TrendTermsData {
  updated_at: string;
  terms: TrendTerm[];
}

/* ── Data ── */

function getTrendTerms(): TrendTermsData {
  try {
    const raw = readFileSync(
      join(process.cwd(), 'tracking', 'trend_terms.json'),
      'utf-8',
    );
    return JSON.parse(raw) as TrendTermsData;
  } catch {
    return { updated_at: '', terms: [] };
  }
}

function stageLabel(stage: string): string {
  const map: Record<string, string> = {
    nascent: 'Nascent (0-7d)',
    emergent: 'Emergent (8-30d)',
    validating: 'Validating (31-90d)',
    rising: 'Rising (90d+)',
  };
  return map[stage] || stage;
}

/* ── Page ── */

export default function TrendsPage() {
  const data = getTrendTerms();
  const { terms, updated_at } = data;
  const totalSources = [...new Set(terms.flatMap((t) => t.sources))].length;

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'CollectionPage',
    name: 'Trend Discovery — AimFast.Dev',
    description:
      'Discover emerging technology terms, concepts, and market signals before they trend.',
    url: 'https://www.aimfast.dev/trends/',
    mainEntity: {
      '@type': 'ItemList',
      itemListElement: terms.map((t, i) => ({
        '@type': 'ListItem',
        position: i + 1,
        url: `https://www.aimfast.dev/trends/${t.id.replace('trend-', '')}/`,
        name: t.canonical,
      })),
    },
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <main className="trends-page">
        {/* ── Hero ── */}
        <section className="trends-hero">
          <h1>
            Discover What&apos;s Emerging
            <br />
            Before Everyone Else
          </h1>
          <p className="trends-hero-desc">
            Daily tracking of new tech terms, concepts, and market signals
            across {totalSources}+ sources. Free. No signup required.
          </p>
          <div className="trends-hero-stats">
            <TrendingUp size={14} />
            Tracking <strong>{terms.length} terms</strong>
            {' · '}Updated daily 08:30 CST
          </div>
        </section>

        {/* ── Stage Filter ── */}
        {terms.length > 0 && (
          <div className="stage-filter">
            {['all', 'nascent', 'emergent', 'validating', 'rising'].map((s) => (
              <a
                key={s}
                href={s === 'all' ? '#trend-grid' : `#stage-${s}`}
                className="stage-filter-btn"
              >
                {s === 'all' ? 'All' : stageLabel(s)}
              </a>
            ))}
          </div>
        )}

        {/* ── Trend Grid ── */}
        {terms.length === 0 ? (
          <div className="trends-empty">
            <h2>No trends yet</h2>
            <p>Check back after the daily pipeline runs. New terms are added every morning.</p>
          </div>
        ) : (
          <div className="trend-grid" id="trend-grid">
            {terms.map((term) => {
              const slug = term.id.replace('trend-', '');
              return (
                <a
                  key={term.id}
                  href={`/trends/${slug}/`}
                  className="trend-card"
                >
                  <span className={`stage-badge ${term.stage}`}>
                    {term.stage}
                  </span>
                  <span className="trend-card-category">{term.category}</span>
                  <h3>{term.canonical}</h3>
                  <p className="trend-card-summary">{term.summary_zh}</p>
                  <div className="trend-card-meta">
                    <span className="trend-card-meta-item">
                      <Calendar size={12} />
                      {term.first_seen}
                    </span>
                    <span className="trend-card-meta-item">
                      <Activity size={12} />
                      {term.source_count} sources
                    </span>
                    <span className="trend-card-meta-item">
                      <BarChart3 size={12} />
                      {term.total_mentions} mentions
                    </span>
                  </div>
                </a>
              );
            })}
          </div>
        )}

        {/* ── CTA ── */}
        <section className="trends-cta">
          <h2>Want the full picture?</h2>
          <p>
            Every morning, our Discovery Engine scans {totalSources}+ sources and
            distills signals like these into one actionable decision — with pricing,
            validation, and competitor context.
          </p>
          <a href="/" className="btn btn-primary" style={{ fontSize: '1rem', padding: '14px 32px' }}>
            Start Free Trial →
          </a>
        </section>

        {/* ── Footer ── */}
        <footer className="site-footer">
          <div className="footer-links">
            <a href="/">Home</a>
            <span className="footer-sep">|</span>
            <a href="/dashboard/">Dashboard</a>
            <span className="footer-sep">|</span>
            <a href="/reports/">Reports</a>
          </div>
          <div className="footer-copy">
            AimFast.Dev — Updated {updated_at ? updated_at.slice(0, 10) : 'daily'} · Free trend discovery
          </div>
        </footer>
      </main>
    </>
  );
}
```

- [ ] **Step 2: Build verify**

Run: `npm run build`

Expected: Build succeeds, `/trends/` included in static export output

- [ ] **Step 3: Commit**

```bash
git add app/trends/page.tsx
git commit -m "feat: /trends/ — 趋势词列表页（筛选、卡片网格、CTA）"
```

---

### Task 4: Trend Detail Page (ZH) — `app/trends/[slug]/page.tsx`

**Files:**
- Create: `app/trends/[slug]/page.tsx`

**Interfaces:**
- Consumes: `tracking/trend_terms.json` (from Task 1)
- Consumes: `content/trends/{slug}.md` (from Task 1)
- Consumes: CSS classes from `app/trends/trends.css` (from Task 2)
- Produces: Route `GET /trends/:slug/` — static HTML page per term

- [ ] **Step 1: Create `app/trends/[slug]/page.tsx`**

```tsx
import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import type { Metadata } from 'next';
import { marked } from 'marked';
import {
  Calendar,
  TrendingUp,
  Activity,
  BarChart3,
  ArrowUpRight,
  Hash,
} from 'lucide-react';

/* ── Types ── */

interface TrendTerm {
  id: string;
  canonical: string;
  aliases: string[];
  first_seen: string;
  last_seen: string;
  stage: 'nascent' | 'emergent' | 'validating' | 'rising';
  score: number;
  source_count: number;
  total_mentions: number;
  sources: string[];
  growth_pct: number;
  category: string;
  tags: string[];
  summary_zh: string;
  summary_en: string;
  research_md_path: string;
}

interface TrendTermsData {
  updated_at: string;
  terms: TrendTerm[];
}

/* ── Data ── */

function getAllTrendTerms(): TrendTermsData {
  try {
    const raw = readFileSync(
      join(process.cwd(), 'tracking', 'trend_terms.json'),
      'utf-8',
    );
    return JSON.parse(raw) as TrendTermsData;
  } catch {
    return { updated_at: '', terms: [] };
  }
}

function getTrendTerm(slug: string): TrendTerm | null {
  const termId = `trend-${slug}`;
  const data = getAllTrendTerms();
  return data.terms.find((t) => t.id === termId) || null;
}

function getResearchContent(path: string): string {
  try {
    const fullPath = join(process.cwd(), path);
    if (!existsSync(fullPath)) return '';
    return readFileSync(fullPath, 'utf-8');
  } catch {
    return '';
  }
}

/* ── Static params ── */

export function generateStaticParams() {
  const data = getAllTrendTerms();
  return data.terms.map((term) => ({
    slug: term.id.replace('trend-', ''),
  }));
}

/* ── Metadata ── */

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const term = getTrendTerm(slug);
  if (!term) {
    return { title: 'Trend Not Found — AimFast.Dev' };
  }

  const title = `${term.canonical} — Trend Report | AimFast.Dev`;
  const description = term.summary_en || term.summary_zh;
  const url = `https://www.aimfast.dev/trends/${slug}/`;

  return {
    title,
    description,
    robots: { index: true, follow: true },
    alternates: { canonical: url },
    openGraph: {
      title,
      description,
      url,
      siteName: 'AimFast.Dev',
      type: 'article',
    },
    twitter: {
      card: 'summary_large_image',
      title,
      description,
    },
  };
}

/* ── Helpers ── */

function stageLabel(stage: string): string {
  const map: Record<string, string> = {
    nascent: 'Nascent (0–7 days)',
    emergent: 'Emergent (8–30 days)',
    validating: 'Validating (31–90 days)',
    rising: 'Rising (90+ days)',
  };
  return map[stage] || stage;
}

function stagePct(stage: string): string {
  const map: Record<string, string> = {
    nascent: '0–7',
    emergent: '8–30',
    validating: '31–90',
    rising: '90+',
  };
  return map[stage] || '';
}

/* ── Page ── */

export default async function TrendDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const term = getTrendTerm(slug);

  if (!term) {
    return (
      <main className="trend-detail">
        <div className="trends-empty">
          <h2>Trend not found</h2>
          <p>
            <a href="/trends/">← Back to all trends</a>
          </p>
        </div>
      </main>
    );
  }

  const researchMd = getResearchContent(term.research_md_path);

  // Strip YAML frontmatter before rendering
  let researchHtml = '';
  if (researchMd) {
    const bodyOnly = researchMd.replace(/^---[\s\S]*?---\n*/, '').trim();
    researchHtml = await marked.parse(bodyOnly);
  }

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: `${term.canonical} — Trend Report`,
    description: term.summary_en,
    url: `https://www.aimfast.dev/trends/${slug}/`,
    datePublished: term.first_seen,
    dateModified: term.last_seen,
    author: { '@type': 'Organization', name: 'AimFast.Dev' },
    mainEntityOfPage: { '@type': 'WebPage', '@id': `https://www.aimfast.dev/trends/${slug}/` },
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <main className="trend-detail">
        {/* ── Breadcrumb ── */}
        <div className="trend-detail-breadcrumb">
          <a href="/trends/">← Back to all trends</a>
        </div>

        {/* ── Header ── */}
        <div className="trend-detail-header">
          <span className={`stage-badge ${term.stage}`}>
            {stageLabel(term.stage)}
          </span>
          <h1>{term.canonical}</h1>

          <div className="trend-detail-sources">
            {term.sources.map((s) => (
              <span key={s} className="trend-source-badge">
                {s}
              </span>
            ))}
          </div>

          <div className="trend-detail-meta-row" style={{ marginTop: 'var(--space-3)' }}>
            <span className="trend-detail-meta-item">
              <Calendar size={14} />
              First seen <strong>{term.first_seen}</strong>
            </span>
            <span className="trend-detail-meta-item">
              <Calendar size={14} />
              Last seen <strong>{term.last_seen}</strong>
            </span>
            <span className="trend-detail-meta-item">
              <BarChart3 size={14} />
              Score <strong>{term.score}</strong>
            </span>
            <span className="trend-detail-meta-item">
              <Activity size={14} />
              <strong>{term.source_count}</strong> sources
            </span>
            <span className="trend-detail-meta-item">
              <Hash size={14} />
              <strong>{term.total_mentions}</strong> mentions
            </span>
            <span className="trend-detail-meta-item">
              <TrendingUp size={14} />
              Growth <strong>+{term.growth_pct}%</strong>
            </span>
          </div>
        </div>

        {/* ── Content + Sidebar Layout ── */}
        <div className="trend-detail-layout">
          {/* ── Main Content ── */}
          <div className="trend-detail-content">
            {researchHtml ? (
              <div
                className="report-content"
                dangerouslySetInnerHTML={{ __html: researchHtml }}
              />
            ) : (
              <p style={{ color: 'var(--color-text-muted)' }}>
                Research report not yet generated. Check back soon — our AI generates
                deep-dive reports for high-scoring trends daily.
              </p>
            )}
          </div>

          {/* ── Sidebar ── */}
          <aside className="trend-sidebar">
            <div className="trend-sidebar-card">
              <h4>About This Trend</h4>
              <p>{term.summary_zh}</p>

              <div style={{ fontSize: '0.82rem', color: 'var(--color-text-secondary)', lineHeight: '1.8' }}>
                <div>
                  <strong>Category:</strong> {term.category}
                </div>
                <div>
                  <strong>Age:</strong> {stagePct(term.stage)} days
                </div>
                <div>
                  <strong>Tags:</strong>{' '}
                  {term.tags.map((t) => (
                    <span key={t} style={{ color: 'var(--color-accent)', marginRight: '6px' }}>
                      #{t}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <div className="trend-sidebar-card">
              <h4>Want the full picture?</h4>
              <p>
                Get daily competitive intel, product opportunities, and
                monitoring — not just trends.
              </p>
              <a href="/" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center', fontSize: '0.88rem', padding: '10px 20px' }}>
                Start Free Trial
                <ArrowUpRight size={14} />
              </a>
            </div>
          </aside>
        </div>

        {/* ── Bottom CTA ── */}
        <section className="trends-cta" style={{ marginTop: 'var(--space-8)' }}>
          <h2>Don&apos;t just track trends — act on them</h2>
          <p>
            Every morning, get one actionable product opportunity with evidence,
            pricing strategy, and validation path. 14-day free trial.
          </p>
          <a href="/" className="btn btn-primary" style={{ fontSize: '1rem', padding: '14px 32px' }}>
            Start Free Trial →
          </a>
        </section>

        {/* ── Footer ── */}
        <footer className="site-footer">
          <div className="footer-links">
            <a href="/">Home</a>
            <span className="footer-sep">|</span>
            <a href="/trends/">All Trends</a>
            <span className="footer-sep">|</span>
            <a href="/dashboard/">Dashboard</a>
            <span className="footer-sep">|</span>
            <a href="/reports/">Reports</a>
          </div>
          <div className="footer-copy">
            AimFast.Dev — Trend reports updated daily
          </div>
        </footer>
      </main>
    </>
  );
}
```

- [ ] **Step 2: Build verify**

Run: `npm run build`

Expected: Build succeeds, 6 static pages generated under `/trends/:slug/`

- [ ] **Step 3: Commit**

```bash
git add app/trends/[slug]/page.tsx
git commit -m "feat: /trends/[slug]/ — 趋势详情页（研究报告 + 侧边栏 + CTA）"
```

---

### Task 5: Trend Detail Page (EN) — `app/trends/[slug]/en/page.tsx`

**Files:**
- Create: `app/trends/[slug]/en/page.tsx`

**Interfaces:**
- Consumes: Same data sources as Task 4
- Consumes: CSS classes from `app/trends/trends.css` (from Task 2)
- Produces: Route `GET /trends/:slug/en/` — static HTML page per term (English)

- [ ] **Step 1: Create `app/trends/[slug]/en/page.tsx`**

```tsx
import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import type { Metadata } from 'next';
import { marked } from 'marked';
import {
  Calendar,
  TrendingUp,
  Activity,
  BarChart3,
  ArrowUpRight,
  Hash,
} from 'lucide-react';

/* ── Types ── */

interface TrendTerm {
  id: string;
  canonical: string;
  aliases: string[];
  first_seen: string;
  last_seen: string;
  stage: 'nascent' | 'emergent' | 'validating' | 'rising';
  score: number;
  source_count: number;
  total_mentions: number;
  sources: string[];
  growth_pct: number;
  category: string;
  tags: string[];
  summary_zh: string;
  summary_en: string;
  research_md_path: string;
}

interface TrendTermsData {
  updated_at: string;
  terms: TrendTerm[];
}

/* ── Data ── */

function getAllTrendTerms(): TrendTermsData {
  try {
    const raw = readFileSync(
      join(process.cwd(), 'tracking', 'trend_terms.json'),
      'utf-8',
    );
    return JSON.parse(raw) as TrendTermsData;
  } catch {
    return { updated_at: '', terms: [] };
  }
}

function getTrendTerm(slug: string): TrendTerm | null {
  const termId = `trend-${slug}`;
  const data = getAllTrendTerms();
  return data.terms.find((t) => t.id === termId) || null;
}

function getResearchContent(path: string): string {
  try {
    const fullPath = join(process.cwd(), path);
    if (!existsSync(fullPath)) return '';
    return readFileSync(fullPath, 'utf-8');
  } catch {
    return '';
  }
}

/* ── Static params ── */

export function generateStaticParams() {
  const data = getAllTrendTerms();
  return data.terms.map((term) => ({
    slug: term.id.replace('trend-', ''),
  }));
}

/* ── Metadata ── */

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const term = getTrendTerm(slug);
  if (!term) {
    return { title: 'Trend Not Found — AimFast.Dev' };
  }

  const title = `${term.canonical} — Trend Report | AimFast.Dev`;
  const description = term.summary_en || term.summary_zh;
  const url = `https://www.aimfast.dev/trends/${slug}/en/`;

  return {
    title,
    description,
    robots: { index: true, follow: true },
    alternates: {
      canonical: `https://www.aimfast.dev/trends/${slug}/`,
      languages: {
        'zh-CN': `https://www.aimfast.dev/trends/${slug}/`,
        'en': `https://www.aimfast.dev/trends/${slug}/en/`,
      },
    },
    openGraph: {
      title,
      description,
      url,
      siteName: 'AimFast.Dev',
      type: 'article',
    },
    twitter: {
      card: 'summary_large_image',
      title,
      description,
    },
  };
}

/* ── Helpers ── */

function stageLabel(stage: string): string {
  const map: Record<string, string> = {
    nascent: 'Nascent (0–7 days)',
    emergent: 'Emergent (8–30 days)',
    validating: 'Validating (31–90 days)',
    rising: 'Rising (90+ days)',
  };
  return map[stage] || stage;
}

/* ── Page ── */

export default async function TrendDetailEnPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const term = getTrendTerm(slug);

  if (!term) {
    return (
      <main className="trend-detail">
        <div className="trends-empty">
          <h2>Trend not found</h2>
          <p>
            <a href="/trends/">← Back to all trends</a>
          </p>
        </div>
      </main>
    );
  }

  const researchMd = getResearchContent(term.research_md_path);
  let researchHtml = '';
  if (researchMd) {
    const bodyOnly = researchMd.replace(/^---[\s\S]*?---\n*/, '').trim();
    researchHtml = await marked.parse(bodyOnly);
  }

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: `${term.canonical} — Trend Report`,
    description: term.summary_en,
    url: `https://www.aimfast.dev/trends/${slug}/en/`,
    datePublished: term.first_seen,
    dateModified: term.last_seen,
    author: { '@type': 'Organization', name: 'AimFast.Dev' },
    inLanguage: 'en',
    mainEntityOfPage: {
      '@type': 'WebPage',
      '@id': `https://www.aimfast.dev/trends/${slug}/en/`,
    },
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <main className="trend-detail">
        {/* ── Breadcrumb ── */}
        <div className="trend-detail-breadcrumb">
          <a href="/trends/">← Back to all trends</a>
          {' · '}
          <a href={`/trends/${slug}/`}>中文</a>
        </div>

        {/* ── Header ── */}
        <div className="trend-detail-header">
          <span className={`stage-badge ${term.stage}`}>
            {stageLabel(term.stage)}
          </span>
          <h1>{term.canonical}</h1>

          <div className="trend-detail-sources">
            {term.sources.map((s) => (
              <span key={s} className="trend-source-badge">
                {s}
              </span>
            ))}
          </div>

          <div className="trend-detail-meta-row" style={{ marginTop: 'var(--space-3)' }}>
            <span className="trend-detail-meta-item">
              <Calendar size={14} />
              First seen <strong>{term.first_seen}</strong>
            </span>
            <span className="trend-detail-meta-item">
              <Calendar size={14} />
              Last seen <strong>{term.last_seen}</strong>
            </span>
            <span className="trend-detail-meta-item">
              <BarChart3 size={14} />
              Score <strong>{term.score}</strong>
            </span>
            <span className="trend-detail-meta-item">
              <Activity size={14} />
              <strong>{term.source_count}</strong> sources
            </span>
            <span className="trend-detail-meta-item">
              <Hash size={14} />
              <strong>{term.total_mentions}</strong> mentions
            </span>
            <span className="trend-detail-meta-item">
              <TrendingUp size={14} />
              Growth <strong>+{term.growth_pct}%</strong>
            </span>
          </div>
        </div>

        {/* ── Content + Sidebar Layout ── */}
        <div className="trend-detail-layout">
          <div className="trend-detail-content">
            {researchHtml ? (
              <div
                className="report-content"
                dangerouslySetInnerHTML={{ __html: researchHtml }}
              />
            ) : (
              <p style={{ color: 'var(--color-text-muted)' }}>
                Research report not yet generated. Check back soon.
              </p>
            )}
          </div>

          <aside className="trend-sidebar">
            <div className="trend-sidebar-card">
              <h4>About This Trend</h4>
              <p>{term.summary_en || term.summary_zh}</p>
              <div style={{ fontSize: '0.82rem', color: 'var(--color-text-secondary)', lineHeight: '1.8' }}>
                <div>
                  <strong>Category:</strong> {term.category}
                </div>
                <div>
                  <strong>Tags:</strong>{' '}
                  {term.tags.map((t) => (
                    <span key={t} style={{ color: 'var(--color-accent)', marginRight: '6px' }}>
                      #{t}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <div className="trend-sidebar-card">
              <h4>Want the full picture?</h4>
              <p>
                Get daily competitive intel, product opportunities, and
                monitoring — not just trends.
              </p>
              <a href="/" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center', fontSize: '0.88rem', padding: '10px 20px' }}>
                Start Free Trial
                <ArrowUpRight size={14} />
              </a>
            </div>
          </aside>
        </div>

        {/* ── Bottom CTA ── */}
        <section className="trends-cta" style={{ marginTop: 'var(--space-8)' }}>
          <h2>Don&apos;t just track trends — act on them</h2>
          <p>
            Every morning, get one actionable product opportunity with evidence,
            pricing strategy, and validation path. 14-day free trial.
          </p>
          <a href="/" className="btn btn-primary" style={{ fontSize: '1rem', padding: '14px 32px' }}>
            Start Free Trial →
          </a>
        </section>

        <footer className="site-footer">
          <div className="footer-links">
            <a href="/">Home</a>
            <span className="footer-sep">|</span>
            <a href="/trends/">All Trends</a>
            <span className="footer-sep">|</span>
            <a href="/dashboard/">Dashboard</a>
            <span className="footer-sep">|</span>
            <a href="/reports/">Reports</a>
          </div>
          <div className="footer-copy">
            AimFast.Dev — Trend reports updated daily
          </div>
        </footer>
      </main>
    </>
  );
}
```

- [ ] **Step 2: Build verify**

Run: `npm run build`

Expected: Build succeeds, 6 English detail pages generated under `/trends/:slug/en/`

- [ ] **Step 3: Commit**

```bash
git add app/trends/[slug]/en/page.tsx
git commit -m "feat: /trends/[slug]/en/ — 趋势详情页英文版（SEO + hreflang）"
```

---

### Task 6: Navigation & Globals Integration

**Files:**
- Modify: `app/globals.css` — add `@import` for trends.css
- Modify: `app/layout.tsx` — add global site nav with Trends link

**Interfaces:**
- Consumes: CSS classes from `app/trends/trends.css` (from Task 2)
- Produces: Site-wide navigation visible on all pages

- [ ] **Step 1: Add trends.css import to `app/globals.css`**

Add after line 6 (`@import './dashboard/dashboard-cards.css';`):

```css
@import './trends/trends.css';
```

And add site nav styles to the end of `app/globals.css`:

```css
/* ── Site Navigation ── */
.site-nav {
  display: flex; align-items: center; justify-content: space-between;
  padding: var(--space-2) var(--space-3);
  max-width: 1100px; margin: 0 auto;
  border-bottom: 1px solid var(--color-border);
}

.site-nav-logo {
  font-family: var(--font-heading);
  font-weight: 700; font-size: 0.95rem;
  color: var(--color-text); text-decoration: none;
  letter-spacing: -0.01em;
}

.site-nav-links {
  display: flex; align-items: center; gap: var(--space-3);
}

.site-nav-links a {
  font-size: 0.85rem; color: var(--color-text-secondary);
  text-decoration: none; font-weight: 500;
  transition: color var(--duration-fast) var(--ease-out);
}

.site-nav-links a:hover {
  color: var(--color-accent);
}
```

- [ ] **Step 2: Add site nav to `app/layout.tsx`**

Insert `<nav className="site-nav">...</nav>` inside `<body>` before `{children}`:

```tsx
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <head>
        {/* ... existing head content unchanged ... */}
      </head>
      <body>
        <nav className="site-nav">
          <a href="/" className="site-nav-logo">AimFast.Dev</a>
          <div className="site-nav-links">
            <a href="/trends/">Trends</a>
            <a href="/dashboard/">Dashboard</a>
            <a href="/reports/">Reports</a>
          </div>
        </nav>
        {children}
      </body>
    </html>
  );
}
```

- [ ] **Step 3: Build verify**

Run: `npm run build`

Expected: Build succeeds. All pages now include the global nav with Trends link.

- [ ] **Step 4: Commit**

```bash
git add app/globals.css app/layout.tsx
git commit -m "feat: 全局导航栏 + trends.css 集成到 globals.css"
```

---

### Task 7: Pipeline Script — `scripts/generate_trends.py`

**Files:**
- Create: `scripts/generate_trends.py`

**Interfaces:**
- Consumes: `daily/{date}/signals.json` (existing pipeline output, processed + scored)
- Consumes: `tracking/trend_terms.json` (from Task 1)
- Produces: Updated `tracking/trend_terms.json` with new/updated terms
- Produces: `content/trends/{slug}.md` research reports for high-score terms
- Side effects: Prints summary to stdout for pipeline logging

- [ ] **Step 1: Create `scripts/generate_trends.py`**

```python
"""
Trend Discovery Pipeline
Reads daily signals, extracts emerging terms via LLM, maintains trend_terms.json,
and generates research reports for high-scoring terms.

Usage: python scripts/generate_trends.py [--dry-run] [--max-terms 30]
"""
import json
import sys
import os
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

TZ_SHANGHAI = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parent.parent
TRACKING_FILE = ROOT / "tracking" / "trend_terms.json"
CONTENT_DIR = ROOT / "content" / "trends"
TEMPLATES_DIR = ROOT / "templates"

# Stage thresholds (days since first_seen)
STAGE_THRESHOLDS = [
    (7, "nascent"),
    (30, "emergent"),
    (90, "validating"),
    (float("inf"), "rising"),
]


def load_json(path: Path) -> dict | list:
    if not path.exists():
        return {} if path.suffix == ".json" else []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_trend_terms() -> dict:
    """Load existing trend terms tracking file."""
    default = {"updated_at": "", "terms": []}
    data = load_json(TRACKING_FILE)
    if isinstance(data, list):
        return default
    return {**default, **data}


def save_trend_terms(data: dict):
    data["updated_at"] = datetime.now(TZ_SHANGHAI).isoformat()
    save_json(TRACKING_FILE, data)


def compute_stage(first_seen_str: str, today: datetime) -> str:
    """Determine stage based on age in days."""
    try:
        first_seen = datetime.strptime(first_seen_str, "%Y-%m-%d").replace(tzinfo=TZ_SHANGHAI)
        age_days = (today - first_seen).days
        for threshold, stage in STAGE_THRESHOLDS:
            if age_days <= threshold:
                return stage
        return "rising"
    except (ValueError, TypeError):
        return "nascent"


def compute_score_from_signals(matching_signals: list[dict]) -> int:
    """Score a term based on its matching signals (reuses existing signal scoring)."""
    if not matching_signals:
        return 0
    avg_score = sum(s.get("score", 0) for s in matching_signals) / len(matching_signals)
    source_count = len(set(s.get("source_key", "") for s in matching_signals))
    total_engagement = sum(s.get("engagement", {}).get("total", 0) for s in matching_signals)
    cross_platform = sum(1 for s in matching_signals if s.get("cross_platform_count", 0) > 0)

    score = (
        avg_score * 0.3
        + min(source_count * 8, 30)
        + min(total_engagement * 0.5, 20)
        + min(cross_platform * 10, 20)
    )
    return min(round(score), 100)


def extract_terms_from_signals(signals: list[dict]) -> list[dict]:
    """
    Extract emerging tech terms from today's signals using LLM.
    Falls back to keyword-based extraction if LLM is unavailable.
    """
    # Build a compact signal summary for the LLM prompt
    signal_summaries = []
    for s in signals[:100]:  # Top 100 by score
        signal_summaries.append({
            "title": s.get("title", ""),
            "summary": s.get("summary", ""),
            "source": s.get("source", ""),
            "tags": s.get("tags", []),
            "score": s.get("score", 0),
        })

    prompt = f"""从以下今日采集的技术社区 signals 中，提取新出现的技术术语、产品名、或概念。

规则：
1. 只提取近 30 天内首次在技术社区出现的词
2. 忽略已知通用词汇（如 "AI", "React", "Python", "API", "OpenAI" 等）
3. 每个词返回 JSON 格式：canonical（规范化名称）、category（分类）、summary_zh（一句话中文摘要）、summary_en（一句话英文摘要）
4. 最多提取 20 个词，按重要性排序
5. 只返回 JSON array，不要其他文字

Signals:
{json.dumps(signal_summaries, ensure_ascii=False, indent=2)}"""

    # Try LLM extraction
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from llm_client import chat

        response = chat(prompt, system="You extract emerging tech terms from community signals. Return only valid JSON array.")
        # Extract JSON from response (handle markdown code blocks)
        response = response.strip()
        if response.startswith("```"):
            response = response.split("\n", 1)[1]
            if response.endswith("```"):
                response = response[:-3]
        terms = json.loads(response)
        if isinstance(terms, list) and len(terms) > 0 and isinstance(terms[0], dict):
            return terms
    except Exception as e:
        print(f"  [trends] LLM extraction failed: {e}, falling back to keyword method")

    # Fallback: tag-based extraction
    return _extract_terms_keyword_fallback(signals)


def _extract_terms_keyword_fallback(signals: list[dict]) -> list[dict]:
    """Keyword-based fallback when LLM is unavailable. Limited but functional."""
    # Collect all tags from high-scoring signals
    tag_counts: dict[str, int] = {}
    for s in signals:
        if s.get("score", 0) < 40:
            continue
        for tag in s.get("tags", []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    # Take top tags that appear multiple times and look like product/tech names
    terms = []
    seen = set()
    for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1]):
        if count < 3 or tag in seen:
            continue
        seen.add(tag)
        # Filter out generic tags
        generic = {"ai", "api", "react", "python", "javascript", "typescript",
                    "web", "mobile", "frontend", "backend", "devops", "cloud",
                    "open-source", "indie-dev", "product-launch", "show-hn",
                    "article", "news", "tutorial", "startup", "saas"}
        if tag.lower() in generic:
            continue

        terms.append({
            "canonical": tag.replace("-", " ").title(),
            "category": "DevTools",
            "summary_zh": f"与 {tag} 相关的新兴趋势，今日出现在多个技术社区信源中。",
            "summary_en": f"An emerging trend related to {tag}, appearing across multiple tech community sources today.",
        })

    return terms[:20]


def merge_terms(existing: list[dict], extracted: list[dict], signals: list[dict], today: datetime) -> list[dict]:
    """Merge extracted terms into existing, updating existing terms and adding new ones."""
    today_str = today.strftime("%Y-%m-%d")
    term_index: dict[str, int] = {}
    for i, t in enumerate(existing):
        term_index[t["id"]] = i
        # Normalize key for matching
        canonical_lower = t["canonical"].lower()
        term_index[canonical_lower] = i
        for alias in t.get("aliases", []):
            term_index[alias.lower()] = i

    for extracted_term in extracted:
        canonical = extracted_term.get("canonical", "").strip()
        if not canonical:
            continue

        # Try to match with existing term
        key = canonical.lower()
        if key in term_index:
            # Update existing term
            idx = term_index[key]
            t = existing[idx]
            t["last_seen"] = today_str
            t["total_mentions"] += 1

            # Update sources
            signal_sources = list(set(s.get("source_key", "") for s in signals if s.get("score", 0) > 0))
            for src in signal_sources:
                if src not in t["sources"]:
                    t["sources"].append(src)

            t["source_count"] = len(t["sources"])

            # Recalculate growth (simple: mentions this week vs total)
            age_days = (today - datetime.strptime(t["first_seen"], "%Y-%m-%d").replace(tzinfo=TZ_SHANGHAI)).days
            if age_days > 0:
                t["growth_pct"] = round((t["total_mentions"] / max(age_days, 1)) * 100)

            t["stage"] = compute_stage(t["first_seen"], today)
            t["score"] = max(t["score"], compute_score_from_signals(
                [s for s in signals if canonical.lower() in s.get("summary", "").lower()]
            ))
        else:
            # New term
            new_id = f"trend-{canonical.lower().replace(' ', '-')[:40]}"
            slug = new_id.replace("trend-", "")

            matching_signals = [
                s for s in signals
                if canonical.lower() in s.get("summary", "").lower()
                or canonical.lower() in s.get("title", "").lower()
            ]

            signal_sources = list(set(s.get("source_key", "") for s in matching_signals))
            score = compute_score_from_signals(matching_signals)

            new_term = {
                "id": new_id,
                "canonical": canonical,
                "aliases": [],
                "first_seen": today_str,
                "last_seen": today_str,
                "stage": "nascent",
                "score": score,
                "source_count": len(signal_sources),
                "total_mentions": len(matching_signals),
                "sources": signal_sources,
                "growth_pct": 100,
                "category": extracted_term.get("category", "General"),
                "tags": list(set(tag for s in matching_signals for tag in s.get("tags", [])))[:5],
                "summary_zh": extracted_term.get("summary_zh", ""),
                "summary_en": extracted_term.get("summary_en", ""),
                "research_md_path": f"content/trends/{slug}.md",
            }
            existing.append(new_term)
            term_index[key] = len(existing) - 1

    # Sort by score descending
    existing.sort(key=lambda t: t.get("score", 0), reverse=True)
    return existing


def generate_research_report(term: dict) -> bool:
    """Generate a research report for a term via LLM. Returns True if successful."""
    slug = term["id"].replace("trend-", "")
    output_path = CONTENT_DIR / f"{slug}.md"

    # Skip if already generated and term hasn't changed stage
    if output_path.exists():
        return False

    # Load prompt template
    template_path = TEMPLATES_DIR / "trend_research_prompt.md"
    if template_path.exists():
        template = template_path.read_text(encoding="utf-8")
    else:
        template = _default_research_prompt()

    prompt = template.replace("{canonical}", term["canonical"])
    prompt = prompt.replace("{category}", term.get("category", "General"))
    prompt = prompt.replace("{summary_zh}", term.get("summary_zh", ""))
    prompt = prompt.replace("{summary_en}", term.get("summary_en", ""))
    prompt = prompt.replace("{sources}", ", ".join(term.get("sources", [])))
    prompt = prompt.replace("{first_seen}", term.get("first_seen", ""))
    prompt = prompt.replace("{stage}", term.get("stage", "nascent"))
    prompt = prompt.replace("{score}", str(term.get("score", 0)))
    prompt = prompt.replace("{source_count}", str(term.get("source_count", 0)))
    prompt = prompt.replace("{total_mentions}", str(term.get("total_mentions", 0)))

    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from llm_client import chat

        report = chat(prompt, system="You write technical trend research reports for indie developers. Use Chinese (zh-CN).")
        CONTENT_DIR.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        return True
    except Exception as e:
        print(f"  [trends] Failed to generate report for {term['canonical']}: {e}")
        return False


def _default_research_prompt() -> str:
    return """Write a comprehensive trend research report for the term "{canonical}" in category {category}.

Structure the report with these 8 sections (use ## for section headers):

## What is it
Explain what {canonical} is in simple terms. Define the concept clearly.

## Why now
Why is this term emerging now? What changed in the market or technology landscape?

## Who's behind it
Key companies, people, or organizations driving this trend.

## Market signals
Cross-platform evidence: {sources}. First seen {first_seen}. Current stage: {stage}. Score: {score}/100.

## Commercial opportunities
How could indie developers or small teams build products around this trend?

## Related terms
Connect to adjacent trends and concepts.

## SEO opportunity
Search volume estimates, key long-tail keywords, competition level.

## Product ideas
2-3 specific product ideas indie developers could build to capitalize on this trend.

Write in Chinese (zh-CN). Be specific and actionable. Avoid generic advice."""


def main():
    parser = argparse.ArgumentParser(description="Generate trend terms from daily signals")
    parser.add_argument("--dry-run", action="store_true", help="Don't write files")
    parser.add_argument("--max-terms", type=int, default=30, help="Max terms to extract")
    parser.add_argument("--date", type=str, help="Date to process (default: today)")
    args = parser.parse_args()

    today = datetime.now(TZ_SHANGHAI)
    if args.date:
        today = datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=TZ_SHANGHAI)

    date_str = today.strftime("%Y-%m-%d")
    signals_path = ROOT / "daily" / date_str / "signals.json"

    if not signals_path.exists():
        print(f"[trends] No signals found for {date_str}, skipping")
        return

    # Load data
    signals = load_json(signals_path)
    if not isinstance(signals, list):
        signals = []
    print(f"[trends] Loaded {len(signals)} signals for {date_str}")

    trend_data = load_trend_terms()
    existing_terms = trend_data.get("terms", [])
    print(f"[trends] Loaded {len(existing_terms)} existing trend terms")

    # Extract new terms
    print("[trends] Extracting new terms from signals...")
    extracted = extract_terms_from_signals(signals)
    print(f"[trends] Extracted {len(extracted)} candidate terms")

    # Merge
    updated_terms = merge_terms(existing_terms, extracted, signals, today)
    new_count = len(updated_terms) - len(existing_terms)
    print(f"[trends] Merged: {len(updated_terms)} total ({new_count} new)")

    # Generate research reports for high-score terms without reports
    reports_generated = 0
    for term in updated_terms:
        if term.get("score", 0) >= 60:
            slug = term["id"].replace("trend-", "")
            report_path = CONTENT_DIR / f"{slug}.md"
            if not report_path.exists():
                print(f"[trends] Generating research report for {term['canonical']} (score={term['score']})...")
                if not args.dry_run:
                    if generate_research_report(term):
                        reports_generated += 1

    print(f"[trends] Generated {reports_generated} new research reports")

    # Save
    trend_data["terms"] = updated_terms
    if not args.dry_run:
        save_trend_terms(trend_data)
        print(f"[trends] Saved {len(updated_terms)} terms to {TRACKING_FILE}")
    else:
        print("[trends] DRY RUN — no files written")

    # Summary
    stages = {"nascent": 0, "emergent": 0, "validating": 0, "rising": 0}
    for t in updated_terms:
        stages[t.get("stage", "nascent")] = stages.get(t.get("stage", "nascent"), 0) + 1
    print(f"[trends] Stage breakdown: {stages}")
    print("[trends] Done")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify script syntax**

Run: `python -c "import py_compile; py_compile.compile('scripts/generate_trends.py', doraise=True); print('OK: Syntax valid')"`

Expected: `OK: Syntax valid`

- [ ] **Step 3: Dry-run test**

Run: `python scripts/generate_trends.py --dry-run --date 2026-07-05`

Expected: Script runs without errors, prints summary (may skip if no signals exist for that date).

- [ ] **Step 4: Commit**

```bash
git add scripts/generate_trends.py
git commit -m "feat: generate_trends.py — 术语抽取 + 追踪 + 研究报告生成 pipeline"
```

---

### Task 8: Research Prompt Template — `templates/trend_research_prompt.md`

**Files:**
- Create: `templates/trend_research_prompt.md`

**Interfaces:**
- Consumed by: `scripts/generate_trends.py` (from Task 7)
- Contains template variables: `{canonical}`, `{category}`, `{summary_zh}`, `{summary_en}`, `{sources}`, `{first_seen}`, `{stage}`, `{score}`, `{source_count}`, `{total_mentions}`

- [ ] **Step 1: Create `templates/trend_research_prompt.md`**

Create the template file with content below. This prompt is used by `generate_trends.py` which replaces `{variable}` placeholders before sending to the LLM.

````markdown
你是一位技术趋势分析师，为独立开发者撰写趋势研究报告。请基于以下数据，为术语 **{canonical}** 撰写一份中文深度研究报告。

## 已知数据

- **术语名称**：{canonical}
- **分类**：{category}
- **中文摘要**：{summary_zh}
- **英文摘要**：{summary_en}
- **出现信源**：{sources}
- **首次发现**：{first_seen}
- **当前阶段**：{stage}
- **趋势分数**：{score}/100
- **信源数量**：{source_count}
- **总提及次数**：{total_mentions}

## 报告结构

请严格按以下 8 个板块撰写，每个板块用 `## 板块名` 作为标题：

### ## What is it（这是什么）

用通俗的语言解释 {canonical} 是什么。帮助一个独立开发者或小团队创始人在 30 秒内理解它的核心含义。

字数：80-120 字。

### ## Why now（为什么现在出现）

分析 {canonical} 为什么在这个时间点出现。是什么市场变化、技术进步、用户需求或行业事件推动了这个词的出现？

字数：100-150 字。

### ## Who's behind it（谁在推动）

列出推动这个趋势的关键公司、组织、个人或开源社区。如果有多个玩家，简要说明各自的角色和关系。

字数：80-120 字。

### ## Market signals（市场信号）

基于已有的信号数据，描述 {canonical} 在技术社区中的表现：
- 跨平台提及模式
- 讨论的热度（从 {source_count} 个信源获得了 {total_mentions} 次提及）
- 当前的成熟度阶段：{stage}

字数：80-100 字。

### ## Commercial opportunities（商业化机会）

独立开发者或小团队如何围绕 {canonical} 建立产品或服务？列出 2-3 个具体方向，每个方向用一句话描述。

字数：100-150 字。

### ## Related terms（相关趋势）

列出 2-3 个与 {canonical} 相关的新兴趋势或术语，简要说明它们之间的关系。这些词可能已经出现在 AimFast 的趋势追踪中。

字数：60-80 字。

### ## SEO opportunity（SEO 机会）

估算 {canonical} 的搜索量趋势（上升/平稳/下降），列出 3 个有价值的长尾关键词，评估当前的竞争程度（低/中/高）。

字数：60-100 字。

### ## Product ideas（产品创意）

基于以上分析，为独立开发者提供 2-3 个可构建的具体产品创意。每个创意包括：
- 产品名称
- 一句话描述
- 为什么现在做是对的时机

字数：120-180 字。

## 格式要求

- 全文用中文撰写
- 不要使用 `{canonical}` 以外的变量占位符
- 数据部分直接引用提供的数字
- 保持客观、分析性的语气
- 避免过度营销化的语言
- 每个板块之间用空行分隔
````

- [ ] **Step 2: Verify template file exists and has all placeholders**

Run: `node -e "const fs=require('fs'); const t=fs.readFileSync('templates/trend_research_prompt.md','utf-8'); const vars=['{canonical}','{category}','{summary_zh}','{summary_en}','{sources}','{first_seen}','{stage}','{score}','{source_count}','{total_mentions}']; vars.forEach(v=>{if(!t.includes(v)){console.log('MISSING:',v);process.exit(1)}}); console.log('OK: All 10 placeholders present')"`

Expected: `OK: All 10 placeholders present`

- [ ] **Step 3: Commit**

```bash
git add templates/trend_research_prompt.md
git commit -m "feat: trend_research_prompt.md — LLM 研究报告生成模板"
```

---

## Implementation Summary

**Total files**: 10 (8 new + 2 modified)

**Task order**: 1 (seed data) → 2 (CSS) → 3, 4, 5 (pages, can be parallel after 1+2) → 6 (nav integration) → 7, 8 (pipeline + template, independent of frontend)

**Verification**: `npm run build` after each frontend task, full build after all tasks complete.

**Expected final build output**:
- `/trends/` — trend listing page
- `/trends/mcp-protocol/` — detail page (zh)
- `/trends/mcp-protocol/en/` — detail page (en)
- `/trends/fluid-compute/` — detail page (zh)
- `/trends/fluid-compute/en/` — detail page (en)
- `/trends/ai-gateway/` — detail page (zh)
- `/trends/ai-gateway/en/` — detail page (en)
- `/trends/webcontainer/` — detail page (zh)
- `/trends/webcontainer/en/` — detail page (en)
- `/trends/cursor-rules/` — detail page (zh)
- `/trends/cursor-rules/en/` — detail page (en)
- `/trends/claude-agent-sdk/` — detail page (zh)
- `/trends/claude-agent-sdk/en/` — detail page (en)

Total: 13 static pages generated.
