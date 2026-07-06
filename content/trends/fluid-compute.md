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
