import type { NextConfig } from 'next';

/**
 * 架构说明：
 * 项目原为 static export（output: 'export'），2026-07 Stripe 支付集成后切换为 SSR。
 *
 * 必要原因：
 * - API Routes（/api/stripe/*, /api/auth/*）需要服务端运行时
 * - pricing 页面需要 auth() 判断登录状态以展示正确的 CTA
 * - webhook 端点必须实时处理 Stripe 事件
 *
 * SEO 补偿措施：
 * - 每个页面导出独立 metadata（title, description, canonical, openGraph, twitter）
 * - pricing 页面内嵌 JSON-LD 结构化数据（FAQPage, SoftwareApplication + Offers）
 * - 价格页面已在 sitemap 中注册
 *
 * 性能影响：可接受。核心页面（pricing）渲染时间 < 200ms，auth() 仅为 JWT 解码（无 DB 查询）。
 */
const nextConfig: NextConfig = {
  trailingSlash: true,
};

export default nextConfig;
