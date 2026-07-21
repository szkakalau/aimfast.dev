'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export function CancelButton() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [confirming, setConfirming] = useState(false);

  async function handleCancel() {
    setLoading(true);
    const res = await fetch('/api/stripe/cancel', { method: 'POST' });
    if (res.ok) {
      router.refresh();
    }
    setLoading(false);
  }

  if (!confirming) {
    return (
      <button onClick={() => setConfirming(true)}
        style={{ padding: '8px 16px', border: '1px solid #dc2626', color: '#dc2626', background: 'transparent', borderRadius: '8px', fontSize: '0.8125rem', fontWeight: 500, cursor: 'pointer' }}>
        Cancel subscription
      </button>
    );
  }

  return (
    <div style={{ textAlign: 'right' }}>
      <p style={{ fontSize: '0.8125rem', color: '#dc2626', marginBottom: 'var(--space-2)' }}>
        Cancel subscription? Access continues until period end.
      </p>
      <div style={{ display: 'flex', gap: 'var(--space-2)', justifyContent: 'flex-end' }}>
        <button onClick={() => setConfirming(false)}
          style={{ padding: '6px 12px', border: '1px solid var(--color-border, #d1d5db)', background: 'transparent', borderRadius: '6px', fontSize: '0.8125rem', cursor: 'pointer' }}>
          Keep
        </button>
        <button onClick={handleCancel} disabled={loading}
          style={{ padding: '6px 12px', background: '#dc2626', color: '#fff', border: 'none', borderRadius: '6px', fontSize: '0.8125rem', fontWeight: 500, cursor: 'pointer', opacity: loading ? 0.6 : 1 }}>
          {loading ? 'Canceling...' : 'Yes, cancel'}
        </button>
      </div>
    </div>
  );
}
