import type { Metadata } from 'next';
import { Clock, Eye, TrendingDown } from 'lucide-react';

export const metadata: Metadata = {
  title: 'Pricing — AimFast.Dev',
  description:
    'One plan, everything included. $19/mo. Daily market intelligence for indie builders — product opportunities, competitor tracking, trend analysis.',
  robots: { index: true, follow: true },
  alternates: {
    canonical: 'https://www.aimfast.dev/pricing/',
    languages: {
      en: 'https://www.aimfast.dev/pricing/',
      'zh-CN': 'https://www.aimfast.dev/pricing/',
    },
  },
  openGraph: {
    title: 'Pricing — AimFast.Dev',
    description: 'Daily market intelligence for indie builders. $19/mo, 14-day free trial.',
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
    description: 'Daily market intelligence for indie builders. $19/mo.',
    images: ['https://www.aimfast.dev/og-pricing.png'],
  },
};

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
    a: 'Yes — that is the Monitoring Engine. Add up to 10 competitors, topics, people, or tech stacks. Every day, you see what they did and what you should do about it. Not just "they launched X" — we tell you "their launch reveals a gap you can fill."',
  },
  {
    q: 'What if I miss a day?',
    a: 'Every report is archived. You can browse past daily decisions and full reports from the dashboard at any time. The value compounds — patterns emerge over weeks, not days.',
  },
  {
    q: 'Is there a long-term contract?',
    a: 'No. Cancel anytime — monthly or annual. If you cancel, you keep access until the end of your billing period. No tricks, no retention calls.',
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

      {/* ═══════ Pain Cards — The Cost of Not Knowing ═══════ */}
      <section className="pain-cards" style={{ padding: 'var(--space-8) 0' }}>
        <div className="section-header">
          <h1>The Cost of Not Knowing</h1>
          <p>
            Every morning without market intel costs you one of three things.
          </p>
        </div>

        <div className="pain-grid">
          <div className="pain-card">
            <Clock size={32} className="pain-icon" />
            <h3>Direction Waste</h3>
            <p>
              You spent 2 weeks building a feature nobody asked for. If you had
              known the demand was fading 10 days ago, you would have built
              something else.
            </p>
            <div className="pain-solution">
              <span className="pain-arrow">→</span>
              Daily decision card tells you what to build — and what to skip
            </div>
          </div>

          <div className="pain-card pain-card-accent">
            <Eye size={32} className="pain-icon" />
            <h3>Competition Blind Spots</h3>
            <p>
              Your competitor changed their pricing 3 days ago. Their free users
              are looking for alternatives. You didn&apos;t know — until now.
            </p>
            <div className="pain-solution">
              <span className="pain-arrow">→</span>
              Monitor up to 10 competitors, topics, or tech stacks
            </div>
          </div>

          <div className="pain-card">
            <TrendingDown size={32} className="pain-icon" />
            <h3>Trend Lag</h3>
            <p>
              A new distribution channel is taking off. Early adopters are
              getting customers at near-zero cost. By the time you hear about it,
              the window is closed.
            </p>
            <div className="pain-solution">
              <span className="pain-arrow">→</span>
              11+ sources scanned daily for emerging signals before they peak
            </div>
          </div>
        </div>
      </section>

      {/* ═══════ Pricing ═══════ */}
      <section className="pricing-section" style={{ padding: 'var(--space-8) 0' }}>
        <div className="section-header">
          <h2>Simple Pricing</h2>
          <p>
            One plan, everything included. No per-seat pricing, no feature gating.
            You either get full value or you cancel — no hard feelings.
          </p>
        </div>

        <div className="pricing-card">
          <div className="pricing-badge">Everything Included</div>

          <div className="pricing-amount-row">
            <span className="pricing-dollar">$</span>
            <span className="pricing-number">19</span>
            <span className="pricing-period">/mo</span>
          </div>
          <div className="pricing-annual">or $190/year — save $38</div>

          <ul className="pricing-features">
            <li>✓ Daily verified product opportunity</li>
            <li>✓ Competitor & topic tracking (up to 10)</li>
            <li>✓ Full report archive</li>
            <li>✓ Signal dashboard with system pulse</li>
            <li>✓ AI assistant (coming soon)</li>
            <li>✓ 14-day free trial</li>
          </ul>

          <a
            href="https://tally.so/r/placeholder"
            className="btn btn-primary pricing-cta"
            target="_blank"
            rel="noopener noreferrer"
          >
            Start Free Trial →
          </a>

          <div className="pricing-cancel">Cancel anytime. No questions asked.</div>
        </div>
      </section>

      {/* ═══════ FAQ ═══════ */}
      <section className="faq-section" style={{ padding: 'var(--space-8) 0', maxWidth: '640px', margin: '0 auto' }}>
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
      <section className="footer-cta" style={{ textAlign: 'center', padding: 'var(--space-8) 0 var(--space-10)' }}>
        <h2>You&apos;re building. They&apos;re watching.</h2>
        <p style={{ color: 'var(--color-text-secondary)', marginBottom: 'var(--space-3)', fontSize: '1rem' }}>
          Start your 14-day free trial. One decision every morning.
        </p>
        <a
          href="https://tally.so/r/placeholder"
          className="btn btn-primary"
          style={{ fontSize: '1rem', padding: '14px 32px' }}
          target="_blank"
          rel="noopener noreferrer"
        >
          Get Early Access →
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
