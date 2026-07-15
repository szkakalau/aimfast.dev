'use client';

import { useEffect } from 'react';
import { RefreshCw, LayoutDashboard } from 'lucide-react';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('[App Error]', error);
  }, [error]);

  return (
    <main style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      minHeight: '60vh', textAlign: 'center', padding: 'var(--space-6) var(--space-3)',
      maxWidth: '480px', margin: '0 auto',
    }}>
      <RefreshCw size={48} style={{ color: 'var(--color-text-muted)', marginBottom: 'var(--space-4)' }} />
      <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 'var(--space-2)', color: 'var(--color-text)' }}>
        Something went wrong
      </h1>
      <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.95rem', lineHeight: 1.7, marginBottom: 'var(--space-5)' }}>
        An unexpected error occurred while loading this page.
        Our data pipeline runs daily — this might be a transient issue.
      </p>
      <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap', justifyContent: 'center' }}>
        <button type="button" onClick={reset} className="btn btn-primary">
          <RefreshCw size={16} />
          Try Again
        </button>
        <a href="/dashboard/" className="btn btn-outline">
          <LayoutDashboard size={16} />
          Dashboard
        </a>
      </div>
    </main>
  );
}
