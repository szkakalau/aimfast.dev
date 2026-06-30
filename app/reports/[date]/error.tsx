'use client';

import { useEffect } from 'react';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('Page error:', error);
  }, [error]);

  return (
    <main className="container">
      <div style={{ padding: 'var(--space-10) 0', textAlign: 'center' }}>
        <h1>Something went wrong</h1>
        <p style={{ color: 'var(--color-text-muted)', marginBottom: 'var(--space-4)' }}>
          An unexpected error occurred while rendering this page.
        </p>
        <button
          onClick={reset}
          className="btn btn-primary"
          style={{ marginRight: 'var(--space-2)' }}
        >
          Try again
        </button>
        <a href="/" className="btn btn-outline">
          Back to home
        </a>
      </div>
    </main>
  );
}
