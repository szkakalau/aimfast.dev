# AimFast.Dev — Design Debt & Deferred Items

## Deferred from 2026-07-15 Design Review

- [ ] **D1 (P3)** — 768-900px 响应式盲区：Trend Detail 2-col 布局在此区间 sidebar 占比 31%，应提前堆叠断点
  - Why: 平板竖屏用户（iPad mini/Surface Go）内容区被挤压
  - Pros: 提升平板用户体验
  - Cons: 需要测试 768-900px 区间的所有页面
  - Context: `app/trends/trends.css:636` — `@media (max-width: 900px)` 改为 `@media (max-width: 920px)` 或新增 `@media (max-width: 768px)` 调整 sidebar

- [ ] **D2 (P3)** — Dashboard 移动端快捷导航：5 个 section 线性堆叠，无快速跳转（anchor nav 或 sticky TOC）
  - Why: 移动端用户需滚动 5 个完整 section 才能到达 FullReport
  - Pros: 大幅提升移动端 Dashboard 可用性
  - Cons: 需设计 sticky TOC 或 section collapse 机制，可能增加复杂度
  - Context: `app/dashboard/dashboard-client.tsx` — Watchlist/DecisionCard/Serendipity/CompetitorCard/FullReport 顺序

- [ ] **D3 (P3)** — prefers-reduced-motion 适配：全站动画（fade-up、skeleton shimmer、pulse-glow、translateY hover）缺少 reduced-motion 媒体查询
  - Why: 前庭障碍用户和偏好减少动画的用户受到影响
  - Pros: WCAG 合规，包容性提升
  - Cons: 需要给每处动画添加 `@media (prefers-reduced-motion: reduce)` 覆盖
  - Context: `public/_ds/components.css`（skeleton, fade-up）、`public/_ds/homepage.css`（fade-up）、`app/trends/trends.css`（pulse-glow）、所有 hover: translateY
