import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Trend Discovery — AimFast.Dev',
  description:
    'Discover emerging technology terms, concepts, and market signals before they trend.',
  robots: { index: false, follow: true },
  alternates: {
    canonical: 'https://www.aimfast.dev/',
  },
  // Meta refresh is the only redirect option for static export (no middleware).
  // Tradeoff: W3C discourages meta refresh for accessibility reasons; screen readers
  // may not announce the redirect. The fallback link in the body covers this.
  // If the site ever enables SSR/middleware, replace with a 301 permanent redirect.
  other: {
    refresh: '0;url=/',
  },
};

export default function TrendsRedirect() {
  return (
    <main className="trends-page">
      <div className="trends-empty" style={{ textAlign: 'center', padding: 'var(--space-10) 0' }}>
        <h2>Trend Discovery has moved</h2>
        <p>
          The trend discovery page is now the <a href="/">homepage</a>.
        </p>
        <p style={{ marginTop: 'var(--space-3)', color: 'var(--color-text-muted)' }}>
          Redirecting…
        </p>
      </div>
    </main>
  );
}
