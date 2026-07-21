import NextAuth from 'next-auth';
import Credentials from 'next-auth/providers/credentials';
import bcrypt from 'bcryptjs';
import { checkRateLimit, resetRateLimit } from '@/lib/rate-limit';
import { authConfig } from '@/lib/auth.config';

// 启动时校验关键环境变量
if (!process.env.AUTH_SECRET) {
  throw new Error('AUTH_SECRET environment variable is required. Generate: openssl rand -base64 32');
}

const LOGIN_MAX_ATTEMPTS = 5;
const LOGIN_WINDOW_MS = 15 * 60 * 1000; // 15 分钟

export const { handlers, auth, signIn, signOut } = NextAuth({
  ...authConfig,
  providers: [
    Credentials({
      name: 'credentials',
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null;

        const email = credentials.email as string;

        // 暴力破解防护：按邮箱限流
        const rateLimit = checkRateLimit(`login:${email}`, LOGIN_MAX_ATTEMPTS, LOGIN_WINDOW_MS);
        if (!rateLimit.allowed) return null;

        // 动态导入 — 仅在 Node.js Runtime 执行，Edge Middleware 不会触发
        const { prisma } = await import('@/lib/prisma');
        const user = await prisma.user.findUnique({
          where: { email },
        });

        if (!user || !user.hashedPassword) return null;

        const passwordMatch = await bcrypt.compare(
          credentials.password as string,
          user.hashedPassword,
        );

        if (!passwordMatch) return null;

        // 登录成功 → 清除失败计数
        resetRateLimit(`login:${email}`);

        return { id: user.id, name: user.name, email: user.email };
      },
    }),
  ],
});
