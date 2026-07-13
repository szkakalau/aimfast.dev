import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: '趋势发现 — AimFast.Dev',
  description:
    '在新兴技术术语和概念流行之前，先人一步发现它们。',
  robots: { index: false, follow: true },
  alternates: {
    canonical: 'https://www.aimfast.dev/',
  },
  // Meta refresh is the only redirect option for static export (no middleware).
  // Tradeoff: W3C discourages meta refresh for accessibility reasons.
  // If the site enables SSR/middleware, replace with a 301 permanent redirect.
  other: {
    refresh: '0;url=/',
  },
};

export default function TrendsZhRedirect() {
  return (
    <main className="trends-page">
      <div className="trends-empty" style={{ textAlign: 'center', padding: 'var(--space-10) 0' }}>
        <h2>趋势发现已迁移</h2>
        <p>
          趋势发现页面现在是<a href="/">首页</a>。
        </p>
        <p style={{ marginTop: 'var(--space-3)', color: 'var(--color-text-muted)' }}>
          正在跳转…
        </p>
      </div>
    </main>
  );
}
