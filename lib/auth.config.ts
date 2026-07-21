import type { NextAuthConfig } from 'next-auth';

/**
 * Edge-safe auth config — 不依赖 Prisma、bcrypt 等 Node.js API。
 * 供 middleware 使用，middleware 中的 auth() 只做 JWT 解码，不会触发 authorize()。
 */
export const authConfig: NextAuthConfig = {
  session: { strategy: 'jwt' },
  pages: {
    signIn: '/login',
  },
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        (session.user as any).id = token.id;
      }
      return session;
    },
  },
  providers: [],
};
