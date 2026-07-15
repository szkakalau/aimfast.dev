import type { Metadata } from 'next';
import { Check, Star } from 'lucide-react';

export const metadata: Metadata = {
  title: 'Pricing — AimFast.Dev',
  description:
    'Three plans for indie builders. Starter $19/mo for trend discovery. Builder $39/mo with daily decisions + competitor monitoring. Team $79/mo with shared boards + API.',
  robots: { index: true, follow: true },
  alternates: {
    canonical: 'https://www.aimfast.dev/pricing/',
    languages: {
      en: 'https://www.aimfast.dev/pricing/',
      'zh-CN': 'https://www.aimfast.dev/pricing/',
    },
  },
  other: { 'last-modified': new Date().toISOString().slice(0, 10) },
  openGraph: {
    title: 'Pricing — AimFast.Dev',
    description: 'Three plans for indie builders. Starter $19/mo, Builder $39/mo, Team $79/mo. 14-day free trial on all plans.',
    url: 'https://www.aimfast.dev/pricing/',
    siteName: 'AimFast.Dev',
    locale: 'en',
    images: [
      {
        url: 'https://www.aimfast.dev/og-pricing.png',
        width: 1200,
        height: 630,
        alt: 'AimFast.Dev — Pricing',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Pricing — AimFast.Dev',
    description: 'Three plans for indie builders. Starter $19/mo, Builder $39/mo, Team $79/mo.',
    images: ['https://www.aimfast.dev/og-pricing.png'],
  },
};

interface Plan {
  id: string;
  name: string;
  badge?: string;
  monthly: number;
  yearly: number;
  description: string;
  features: string[];
  cta: string;
  highlight?: boolean;
}

const PLANS: Plan[] = [
  {
    id: 'starter',
    name: 'Starter',
    monthly: 19,
    yearly: 190,
    description: 'Trend discovery for curious builders. See what\'s emerging before it peaks.',
    features: [
      'Daily trend discovery (11+ sources)',
      'Browse all tracked terms',
      'Stage & category filtering',
      'Basic term tracking (3 terms)',
      'Weekly email digest',
      '14-day free trial',
    ],
    cta: 'Start Free Trial',
  },
  {
    id: 'builder',
    name: 'Builder',
    badge: 'Most Popular',
    monthly: 39,
    yearly: 390,
    description: 'One decision every morning. Build with confidence, not guesswork.',
    features: [
      'Everything in Starter',
      'Daily verified decision card',
      'Competitor & topic monitoring (up to 10)',
      'Full deep research reports (≥60 score)',
      'AI scoring & cross-platform validation',
      'Full report archive',
      'Track unlimited terms',
      'Priority email support',
      '14-day free trial',
    ],
    cta: 'Start Free Trial',
    highlight: true,
  },
  {
    id: 'team',
    name: 'Team',
    badge: 'For Teams',
    monthly: 79,
    yearly: 790,
    description: 'Shared intelligence for small teams. Align on what to build next.',
    features: [
      'Everything in Builder',
      '3 team seats',
      'Shared monitoring boards',
      'CSV export',
      'API access (coming soon)',
      'Early access to new features',
      '14-day free trial',
    ],
    cta: 'Start Free Trial',
  },
];

const FAQ_ITEMS = [
  {
    q: 'How is this different from setting up Google Alerts?',
    a: 'Google Alerts gives you links. We give you a decision. Our AI reads 300+ signals across 11 platforms, cross-references them, scores them, and tells you "build this, skip that." Google Alerts cannot tell you that a Reddit complaint and a GitHub star spike are the same unmet need.',
  },
  {
    q: 'What sources do you scan?',
    a: 'HN, Reddit (r/programming, r/MachineLearning, r/SideProject, r/Entrepreneur, r/digitalnomad), GitHub Trending, DEV Community, Lobsters, V2EX, X/Twitter, Product Hunt, HuggingFace, Arxiv, Indie Hackers, and more — 11+ sources, daily.',
  },
  {
    q: 'Can I track my competitors?',
    a: 'Yes — on the Builder plan and above. Add up to 10 competitors, topics, people, or tech stacks. Every day, you see what they did and what you should do about it. Not just "they launched X" — we tell you "their launch reveals a gap you can fill."',
  },
  {
    q: 'What if I miss a day?',
    a: 'Every report is archived. You can browse past daily decisions and full reports from the dashboard at any time. The value compounds — patterns emerge over weeks, not days.',
  },
  {
    q: 'Is there a long-term contract?',
    a: 'No. Cancel anytime — monthly or annual. If you cancel, you keep access until the end of your billing period. No tricks, no retention calls.',
  },
  {
    q: 'Can I upgrade or downgrade later?',
    a: 'Yes — switch plans anytime. Upgrading takes effect immediately with prorated billing. Downgrading applies at the end of your current billing cycle.',
  },
];

export default function PricingPage() {
  const faqJsonLd = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://www.aimfast.dev/' },
          { '@type': 'ListItem', position: 2, name: 'Pricing', item: 'https://www.aimfast.dev/pricing/' },
        ],
      },
      {
        '@type': 'FAQPage',
        mainEntity: FAQ_ITEMS.map(({ q, a }) => ({
          '@type': 'Question',
          name: q,
          acceptedAnswer: { '@type': 'Answer', text: a },
        })),
      },
    ],
  };

  return (
    <main>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }}
      />

      {/* ═══════ Hero ═══════ */}
      <section style={{ padding: 'var(--space-10) 0 var(--space-6)', textAlign: 'center' }}>
        <h1 style={{ fontSize: '2.25rem', fontWeight: 700, margin: '0 0 var(--space-3)' }}>
          One Decision Every Morning
        </h1>
        <p style={{ fontSize: '1.125rem', color: 'var(--color-text-secondary)', maxWidth: '560px', margin: '0 auto', lineHeight: 1.6 }}>
          Three plans. Same core promise: stop guessing what to build.
          All plans include a 14-day free trial — no credit card required.
        </p>
      </section>

      {/* ═══════ Pricing Cards ═══════ */}
      <section style={{ padding: '0 0 var(--space-8)', maxWidth: '960px', margin: '0 auto' }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 'var(--space-5)',
          alignItems: 'start',
        }}>
          {PLANS.map((plan) => (
            <div
              key={plan.id}
              style={{
                position: 'relative',
                border: plan.highlight
                  ? '2px solid var(--color-accent, #2563eb)'
                  : '1px solid var(--color-border, #e5e7eb)',
                borderRadius: '12px',
                padding: 'var(--space-6)',
                background: plan.highlight
                  ? 'var(--color-surface, #fff)'
                  : 'var(--color-bg, #f9fafb)',
                boxShadow: plan.highlight
                  ? '0 4px 24px rgba(37, 99, 235, 0.12)'
                  : 'none',
              }}
            >
              {/* Badge */}
              {plan.badge && (
                <div style={{
                  position: 'absolute',
                  top: '-13px',
                  left: '50%',
                  transform: 'translateX(-50%)',
                  background: plan.highlight ? 'var(--color-accent, #2563eb)' : 'var(--color-text-secondary, #6b7280)',
                  color: '#fff',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  padding: '4px 14px',
                  borderRadius: '999px',
                  whiteSpace: 'nowrap',
                }}>
                  {plan.badge === 'Most Popular' && (
                    <Star size={12} style={{ display: 'inline', marginRight: '4px', verticalAlign: '-1px' }} />
                  )}
                  {plan.badge}
                </div>
              )}

              {/* Plan Name */}
              <h2 style={{
                fontSize: '1.25rem',
                fontWeight: 700,
                margin: plan.badge ? 'var(--space-3) 0 var(--space-1)' : '0 0 var(--space-1)',
              }}>
                {plan.name}
              </h2>

              {/* Description */}
              <p style={{
                fontSize: '0.85rem',
                color: 'var(--color-text-secondary)',
                margin: '0 0 var(--space-4)',
                minHeight: '2.5em',
                lineHeight: 1.4,
              }}>
                {plan.description}
              </p>

              {/* Price */}
              <div style={{ marginBottom: 'var(--space-4)' }}>
                <span style={{ fontSize: '2.5rem', fontWeight: 800, lineHeight: 1 }}>
                  ${plan.monthly}
                </span>
                <span style={{ fontSize: '0.95rem', color: 'var(--color-text-secondary)' }}>
                  /mo
                </span>
                <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted, #9ca3af)', marginTop: '2px' }}>
                  or ${plan.yearly}/year — save ${plan.monthly * 12 - plan.yearly}
                </div>
              </div>

              {/* CTA */}
              <a
                href="https://tally.so/r/placeholder"
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: 'block',
                  textAlign: 'center',
                  padding: '12px 0',
                  borderRadius: '8px',
                  fontWeight: 600,
                  fontSize: '0.95rem',
                  textDecoration: 'none',
                  marginBottom: 'var(--space-5)',
                  transition: 'all 150ms ease-out',
                  background: plan.highlight
                    ? 'var(--color-accent, #2563eb)'
                    : 'var(--color-bg, #f3f4f6)',
                  color: plan.highlight ? '#fff' : 'var(--color-text, #111827)',
                  border: plan.highlight ? 'none' : '1px solid var(--color-border, #d1d5db)',
                }}
              >
                {plan.cta} →
              </a>

              {/* Features */}
              <ul style={{
                listStyle: 'none',
                padding: 0,
                margin: 0,
                fontSize: '0.875rem',
                lineHeight: 1.6,
              }}>
                {plan.features.map((f) => (
                  <li
                    key={f}
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: 'var(--space-2)',
                      marginBottom: 'var(--space-2)',
                    }}
                  >
                    <Check
                      size={16}
                      style={{
                        flexShrink: 0,
                        marginTop: '4px',
                        color: plan.highlight
                          ? 'var(--color-accent, #2563eb)'
                          : 'var(--color-text-secondary, #6b7280)',
                      }}
                    />
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Money-back note */}
        <p style={{
          textAlign: 'center',
          fontSize: '0.85rem',
          color: 'var(--color-text-muted, #9ca3af)',
          marginTop: 'var(--space-4)',
        }}>
          All plans include a 14-day free trial. Cancel anytime — no questions asked.
        </p>
      </section>

      {/* ═══════ FAQ ═══════ */}
      <section style={{ padding: 'var(--space-8) 0', maxWidth: '640px', margin: '0 auto' }}>
        <div className="section-header">
          <h2>Frequently Asked Questions</h2>
        </div>

        <dl className="faq-list">
          {FAQ_ITEMS.map(({ q, a }) => (
            <div key={q} className="faq-item">
              <dt>{q}</dt>
              <dd>{a}</dd>
            </div>
          ))}
        </dl>
      </section>

      {/* ═══════ Footer CTA ═══════ */}
      <section style={{ textAlign: 'center', padding: 'var(--space-8) 0 var(--space-10)' }}>
        <h2>14 days free. One decision every morning.</h2>
        <p style={{ color: 'var(--color-text-secondary)', marginBottom: 'var(--space-4)', fontSize: '1rem' }}>
          No credit card required. Cancel anytime.
        </p>
        <a
          href="https://tally.so/r/placeholder"
          className="btn btn-primary"
          style={{ fontSize: '1rem', padding: '14px 32px' }}
          target="_blank"
          rel="noopener noreferrer"
        >
          Start Building →
        </a>
      </section>

      {/* ═══════ Footer ═══════ */}
      <footer className="site-footer">
        <div className="footer-links">
          <a href="/">Trends</a>
          <span className="footer-sep">|</span>
          <a href="/dashboard/">Dashboard</a>
          <span className="footer-sep">|</span>
          <a href="/reports/">Reports</a>
        </div>
        <div className="footer-copy">
          AimFast.Dev — Daily Market Intelligence for Indie Builders
        </div>
      </footer>
    </main>
  );
}
