'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import type { Session } from 'next-auth';

interface Props {
  planId: string;
  session: Session | null;
  highlight?: boolean;
  cta: string;
}

export function PricingCTA({ planId, session, highlight, cta }: Props) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleClick() {
    setError('');

    if (!session) {
      router.push(`/login?callback=/pricing`);
      return;
    }

    setLoading(true);
    const res = await fetch('/api/stripe/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ planId }),
    });

    const data = await res.json();

    if (data.url) {
      window.location.href = data.url;
    } else {
      setError(data.error || 'Something went wrong.');
      setLoading(false);
    }
  }

  const buttonLabel = !session ? 'Sign in to Start →' : loading ? 'Redirecting...' : `${cta} →`;

  return (
    <div>
      <button onClick={handleClick} disabled={loading}
        style={{
          display: 'block', width: '100%', textAlign: 'center', padding: '12px 0', borderRadius: '8px',
          fontWeight: 600, fontSize: '0.95rem', textDecoration: 'none', marginBottom: error ? 'var(--space-2)' : 'var(--space-5)',
          border: 'none', cursor: 'pointer', transition: 'all 150ms ease-out',
          background: highlight ? 'var(--color-accent, #2563eb)' : 'var(--color-bg, #f3f4f6)',
          color: highlight ? '#fff' : 'var(--color-text, #111827)',
          boxShadow: highlight ? 'none' : 'inset 0 0 0 1px var(--color-border, #d1d5db)',
          opacity: loading ? 0.6 : 1,
        }}>
        {buttonLabel}
      </button>
      {error && (
        <p style={{ fontSize: '0.8125rem', color: '#dc2626', marginBottom: 'var(--space-5)', textAlign: 'center' }}>
          {error}
        </p>
      )}
    </div>
  );
}
