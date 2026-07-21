/**
 * 从 NextAuth session 中提取 userId。
 * 避免 (session.user as any).id 在代码库中重复出现。
 */
export function getUserId(session: { user?: { id?: string } } | null): string | undefined {
  return (session?.user as any)?.id ?? undefined;
}
