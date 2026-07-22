/**
 * 从 NextAuth session 中提取 userId。
 * 避免 (session.user as any).id 在代码库中重复出现。
 */
export function getUserId(session: { user?: { id?: string } } | null): string | undefined {
  return (session?.user as any)?.id ?? undefined;
}

/**
 * 从 NextAuth session 中提取用户角色。
 * 返回 "admin" | "user"，默认为 "user"。
 */
export function getUserRole(session: { user?: { role?: string } } | null): string {
  return (session?.user as any)?.role ?? 'user';
}

/** 是否管理员 */
export function isAdmin(session: { user?: { role?: string } } | null): boolean {
  return getUserRole(session) === 'admin';
}
