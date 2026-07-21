import { PrismaClient } from '@prisma/client';
import { PrismaNeonHttp } from '@prisma/adapter-neon';

/**
 * PrismaNeonHttp — 为什么不用默认的 PrismaClient？
 *
 * 默认 Prisma Client 使用 TCP/TLS 直连 PostgreSQL，在中国大陆环境中
 * Neon 的 WebSocket 端口被 GFW 的 DPI（深度包检测）阻断。
 *
 * PrismaNeonHttp 通过 HTTPS fetch 发送 SQL 查询（HTTP 443 端口），
 * 走标准的 TLS 加密通道，绕过 DPI 拦截。
 *
 * 代价：HTTP 协议比原生 TCP 慢约 5-10ms/query（可接受）。
 * 如果需要迁回直连（如非 GFW 环境），只需移除 adapter 参数即可。
 *
 * 配套脚本：scripts/node_proxy_setup.mjs（Node.js fetch 代理配置）
 */
const adapter = new PrismaNeonHttp(process.env.DATABASE_URL!);

const globalForPrisma = globalThis as unknown as { prisma: PrismaClient };

export const prisma = globalForPrisma.prisma ?? new PrismaClient({ adapter });

if (process.env.NODE_ENV !== 'production') {
  globalForPrisma.prisma = prisma;
}
