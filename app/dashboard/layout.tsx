import { auth } from '@/lib/auth';
import { redirect } from 'next/navigation';
import Link from 'next/link';

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  // auth() 在 layout 和 page 中各调用一次。
  // JWT 策略下每次调用仅解码 token（无 DB 查询），性能影响可忽略（< 1ms）。
  const session = await auth();
  if (!session?.user) {
    redirect('/login?callback=/dashboard');
  }

  return (
    <main className="container" style={{ maxWidth: '960px', margin: '0 auto', padding: 'var(--space-6) var(--space-3)' }}>
      <nav style={{ display: 'flex', gap: 'var(--space-4)', marginBottom: 'var(--space-6)', borderBottom: '1px solid var(--color-border, #e5e7eb)', paddingBottom: 'var(--space-3)' }}>
        <Link href="/dashboard/billing" style={{ color: 'var(--color-accent, #2563eb)', fontWeight: 600, fontSize: '0.875rem', textDecoration: 'none' }}>
          Billing
        </Link>
        <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.875rem' }}>{session.user.email}</span>
        <a href="/api/auth/signout" style={{ marginLeft: 'auto', color: 'var(--color-text-secondary)', fontSize: '0.875rem', textDecoration: 'none' }}>
          Sign out
        </a>
      </nav>
      {children}
    </main>
  );
}
