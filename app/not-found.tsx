import Link from 'next/link';
import { Search, LayoutDashboard } from 'lucide-react';

export default function NotFound() {
  return (
    <main style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      minHeight: '60vh', textAlign: 'center', padding: 'var(--space-6) var(--space-3)',
      maxWidth: '480px', margin: '0 auto',
    }}>
      <Search size={48} style={{ color: 'var(--color-text-muted)', marginBottom: 'var(--space-4)' }} />
      <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 'var(--space-2)', color: 'var(--color-text)' }}>
        Page not found
      </h1>
      <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.95rem', lineHeight: 1.7, marginBottom: 'var(--space-5)' }}>
        This page doesn&apos;t exist (yet). It might be a signal we haven&apos;t picked up —
        or the URL may have changed.
      </p>
      <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap', justifyContent: 'center' }}>
        <Link href="/" className="btn btn-primary">
          <Search size={16} />
          Browse Trends
        </Link>
        <Link href="/dashboard/" className="btn btn-outline">
          <LayoutDashboard size={16} />
          Dashboard
        </Link>
      </div>
    </main>
  );
}
