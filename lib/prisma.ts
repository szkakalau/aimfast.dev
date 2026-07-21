import { PrismaClient } from '@prisma/client';
import { PrismaNeonHttp } from '@prisma/adapter-neon';

// PrismaNeonHttp 走 HTTPS fetch，绕过 GFW 对 WebSocket 的 DPI 拦截
const adapter = new PrismaNeonHttp(process.env.DATABASE_URL!);

const globalForPrisma = globalThis as unknown as { prisma: PrismaClient };

export const prisma = globalForPrisma.prisma ?? new PrismaClient({ adapter });

if (process.env.NODE_ENV !== 'production') {
  globalForPrisma.prisma = prisma;
}
