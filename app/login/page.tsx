'use client';

import { useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { signIn } from 'next-auth/react';

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const callback = searchParams.get('callback') || '/dashboard/billing';
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const result = await signIn('credentials', { email, password, redirect: false });

      if (result?.error) {
        setError('Invalid email or password.');
      } else {
        router.push(callback);
      }
    } catch {
      setError('Something went wrong. Please try again.');
    }

    setLoading(false);
  }

  return (
    <div>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 'var(--space-6)' }}>Sign in to AimFast</h1>

      {error && (
        <div style={{ padding: 'var(--space-3)', marginBottom: 'var(--space-4)', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '8px', color: '#dc2626', fontSize: '0.875rem' }}>
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
        <div>
          <label htmlFor="email" style={{ display: 'block', marginBottom: 'var(--space-1)', fontWeight: 500, fontSize: '0.875rem' }}>Email</label>
          <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required
            style={{ width: '100%', padding: '10px 12px', border: '1px solid var(--color-border, #d1d5db)', borderRadius: '8px', fontSize: '0.95rem' }} />
        </div>
        <div>
          <label htmlFor="password" style={{ display: 'block', marginBottom: 'var(--space-1)', fontWeight: 500, fontSize: '0.875rem' }}>Password</label>
          <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required
            style={{ width: '100%', padding: '10px 12px', border: '1px solid var(--color-border, #d1d5db)', borderRadius: '8px', fontSize: '0.95rem' }} />
        </div>
        <button type="submit" disabled={loading}
          style={{ padding: '12px', background: 'var(--color-accent, #2563eb)', color: '#fff', border: 'none', borderRadius: '8px', fontWeight: 600, fontSize: '0.95rem', cursor: 'pointer', opacity: loading ? 0.6 : 1 }}>
          {loading ? 'Signing in...' : 'Sign in →'}
        </button>
      </form>

      <p style={{ textAlign: 'center', marginTop: 'var(--space-4)', fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>
        Don&apos;t have an account? <a href="/register" style={{ color: 'var(--color-accent, #2563eb)' }}>Create one</a>
      </p>
    </div>
  );
}

export default function LoginPage() {
  return (
    <main className="container" style={{ maxWidth: '400px', margin: '0 auto', padding: 'var(--space-10) var(--space-3)' }}>
      <Suspense fallback={<div style={{ textAlign: 'center', padding: 'var(--space-8)' }}>Loading...</div>}>
        <LoginForm />
      </Suspense>
    </main>
  );
}
