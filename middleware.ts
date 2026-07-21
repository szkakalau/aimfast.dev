import NextAuth from 'next-auth';
import { authConfig } from '@/lib/auth.config';
import { NextResponse } from 'next/server';

/**
 * Middleware 使用独立的 Edge-safe auth 实例（authConfig 不含 Prisma 依赖）。
 * auth() 在 middleware 中只做 JWT 解码，不会触发 Credentials provider 的 authorize()。
 */
const { auth } = NextAuth(authConfig);

export default auth((req) => {
  const { pathname } = req.nextUrl;

  // /dashboard/* 和 /reports/* 需要登录
  const protectedRoutes = ['/dashboard', '/reports'];
  const needsAuth = protectedRoutes.some((route) => pathname.startsWith(route));

  if (needsAuth && !req.auth) {
    const loginUrl = new URL('/login', req.url);
    loginUrl.searchParams.set('callback', pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
});

export const config = {
  matcher: ['/dashboard/:path*', '/reports/:path*'],
};
