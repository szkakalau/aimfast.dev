import type { Metadata } from 'next';
import { TrendingUp, BarChart3, Zap, Globe } from 'lucide-react';

export const metadata: Metadata = {
  title: 'About — AimFast.Dev',
  description:
    'AimFast.Dev is an automated trend discovery platform scanning 30+ sources nightly. Learn about our methodology, pipeline, and the team behind the daily market intelligence.',
  robots: { index: true, follow: true },
  alternates: {
    canonical: 'https://www.aimfast.dev/about/',
  },
  openGraph: {
    title: 'About — AimFast.Dev',
    description: 'Learn about the methodology and pipeline behind AimFast.Dev — automated trend discovery for indie builders.',
    url: 'https://www.aimfast.dev/about/',
    siteName: 'AimFast.Dev',
    locale: 'en',
    images: [
      {
        url: 'https://www.aimfast.dev/og-home.png',
        width: 1200,
        height: 630,
        alt: 'AimFast.Dev — About',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'About — AimFast.Dev',
    description: 'Automated trend discovery for indie builders. Learn about our methodology.',
    images: ['https://www.aimfast.dev/og-home.png'],
  },
};

export default function AboutPage() {
  const jsonLd = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://www.aimfast.dev/' },
          { '@type': 'ListItem', position: 2, name: 'About', item: 'https://www.aimfast.dev/about/' },
        ],
      },
      {
        '@type': 'AboutPage',
        name: 'About AimFast.Dev',
        description:
          'AimFast.Dev is an automated trend discovery platform that scans 30+ sources nightly with an LLM pipeline, tracking 170+ emerging tech terms with proprietary Builder Score and stage classification.',
        url: 'https://www.aimfast.dev/about/',
        about: {
          '@type': 'Organization',
          name: 'AimFast.Dev',
          url: 'https://www.aimfast.dev/',
          logo: 'https://www.aimfast.dev/og-home.png',
          image: 'https://www.aimfast.dev/og-home.png',
          description:
            'Daily market intelligence for indie builders. AI scans 30+ sources to deliver one validated product opportunity every morning.',
          foundingDate: '2026-01-01',
          sameAs: [
            'https://github.com/szkakalau/aimfast.dev',
            'https://twitter.com/aimfastdev',
          ],
          contactPoint: {
            '@type': 'ContactPoint',
            contactType: 'customer support',
            email: 'support@aimfast.dev',
            url: 'https://www.aimfast.dev/about/',
          },
        },
      },
    ],
  };

  return (
    <main>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* ═══════ Hero ═══════ */}
      <section style={{ padding: 'var(--space-10) 0 var(--space-6)', textAlign: 'center' }}>
        <h1 style={{ fontWeight: 700, margin: '0 0 var(--space-3)' }}>
          One Decision Every Morning
        </h1>
        <p style={{ fontSize: '1.125rem', color: 'var(--color-text-secondary)', maxWidth: '600px', margin: '0 auto', lineHeight: 1.6, overflowWrap: 'break-word' }}>
          AimFast.Dev is an automated trend discovery platform.
          Every night, our pipeline scans 30+ global sources, scores emerging tech terms,
          and generates one actionable product opportunity by morning.
        </p>
      </section>

      {/* ═══════ What We Do ═══════ */}
      <section style={{ padding: 'var(--space-8) 0', maxWidth: '720px', margin: '0 auto' }}>
        <div className="section-header">
          <h2>What We Do</h2>
        </div>

        <div style={{ display: 'grid', gap: 'var(--space-5)' }}>
          <div style={{
            display: 'flex', gap: 'var(--space-4)', alignItems: 'flex-start',
            padding: 'var(--space-5)', border: '1px solid var(--color-border)', borderRadius: '10px',
          }}>
            <Globe size={24} style={{ flexShrink: 0, color: 'var(--color-accent, #2563eb)', marginTop: '2px' }} />
            <div>
              <h3 style={{ margin: '0 0 var(--space-1)', fontSize: '1.05rem' }}>Signal Collection</h3>
              <p style={{ color: 'var(--color-text-secondary)', margin: 0, lineHeight: 1.6 }}>
                30+ independent collectors run in parallel every night, pulling data from developer platforms
                (Hacker News, GitHub, DEV, Lobsters), social media (X/Twitter, Reddit, YouTube),
                package registries (npm, PyPI), AI/ML hubs (HuggingFace, ArXiv), and consumer platforms
                (Douban, Xiaohongshu, Product Hunt). One failure never blocks another.
              </p>
            </div>
          </div>

          <div style={{
            display: 'flex', gap: 'var(--space-4)', alignItems: 'flex-start',
            padding: 'var(--space-5)', border: '1px solid var(--color-border)', borderRadius: '10px',
          }}>
            <BarChart3 size={24} style={{ flexShrink: 0, color: 'var(--color-accent, #2563eb)', marginTop: '2px' }} />
            <div>
              <h3 style={{ margin: '0 0 var(--space-1)', fontSize: '1.05rem' }}>Signal Processing & Scoring</h3>
              <p style={{ color: 'var(--color-text-secondary)', margin: 0, lineHeight: 1.6 }}>
                Raw signals are deduplicated, clustered, and scored using our E-P-A framework
                (Evidence × Plain-English × Action). Cross-platform detection flags signals appearing
                in ≥2 independent sources. C-end (consumer) opportunities are auto-detected so
                we don&apos;t miss what developer-only tools overlook.
              </p>
            </div>
          </div>

          <div style={{
            display: 'flex', gap: 'var(--space-4)', alignItems: 'flex-start',
            padding: 'var(--space-5)', border: '1px solid var(--color-border)', borderRadius: '10px',
          }}>
            <TrendingUp size={24} style={{ flexShrink: 0, color: 'var(--color-accent, #2563eb)', marginTop: '2px' }} />
            <div>
              <h3 style={{ margin: '0 0 var(--space-1)', fontSize: '1.05rem' }}>Trend Term Pipeline</h3>
              <p style={{ color: 'var(--color-text-secondary)', margin: 0, lineHeight: 1.6 }}>
                Terms are extracted, normalized, classified by maturity stage (Nascent → Emergent →
                Validating → Rising), and scored with the Builder Score — a 5-factor weighted composite
                that measures source diversity, growth velocity, authority, mention volume, and freshness.
                Only terms validated across multiple independent sources surface on the dashboard.
              </p>
            </div>
          </div>

          <div style={{
            display: 'flex', gap: 'var(--space-4)', alignItems: 'flex-start',
            padding: 'var(--space-5)', border: '1px solid var(--color-border)', borderRadius: '10px',
          }}>
            <Zap size={24} style={{ flexShrink: 0, color: 'var(--color-accent, #2563eb)', marginTop: '2px' }} />
            <div>
              <h3 style={{ margin: '0 0 var(--space-1)', fontSize: '1.05rem' }}>Daily Report Generation</h3>
              <p style={{ color: 'var(--color-text-secondary)', margin: 0, lineHeight: 1.6 }}>
                An LLM (DeepSeek) generates a structured daily report — not a template, but a
                context-aware analysis that follows strict rules: every claim needs evidence,
                every product recommendation names a buyer persona, and every opportunity
                includes a concrete price anchor. A secondary LLM pass extracts structured
                decision data for the Dashboard.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════ Methodology ═══════ */}
      <section style={{ padding: 'var(--space-8) 0', maxWidth: '720px', margin: '0 auto' }}>
        <div className="section-header">
          <h2>Methodology</h2>
        </div>

        <p style={{ color: 'var(--color-text-secondary)', lineHeight: 1.7, marginBottom: 'var(--space-4)' }}>
          The core insight behind AimFast.Dev is simple: a term appearing in 3 unrelated communities
          is a far stronger signal than one with 500 mentions in a single echo chamber.
        </p>

        <p style={{ color: 'var(--color-text-secondary)', lineHeight: 1.7, marginBottom: 'var(--space-4)' }}>
          Our Builder Score formula weights <strong>source_count ×15</strong> above all other factors,
          reflecting this cross-validation principle. Growth velocity (×12) captures momentum direction.
          Freshness decay (×10) ensures the dashboard surfaces what&apos;s happening now, not last month.
        </p>

        <p style={{ color: 'var(--color-text-secondary)', lineHeight: 1.7, marginBottom: 'var(--space-4)' }}>
          Every signal must clear a minimum bar: appear in ≥2 independent sources, survive
          deduplication (85% title similarity threshold), and pass the E-P-A scoring rubric.
          Signals that fail to produce unique insights for 7 consecutive days are flagged
          for review — not silently dropped.
        </p>

        <p style={{ color: 'var(--color-text-secondary)', lineHeight: 1.7 }}>
          For the complete technical reference — including the exact scoring formulas, pipeline
          architecture, and LLM prompt methodology — see{' '}
          <a href="/llms-full.txt">llms-full.txt</a> (2,656 words, AI-readable format).
        </p>
      </section>

      {/* ═══════ Transparency ═══════ */}
      <section style={{ padding: 'var(--space-8) 0', maxWidth: '720px', margin: '0 auto' }}>
        <div className="section-header">
          <h2>Transparency</h2>
        </div>

        <p style={{ color: 'var(--color-text-secondary)', lineHeight: 1.7, marginBottom: 'var(--space-4)' }}>
          All trend data is published as static JSON. The pipeline is open-source.
          We believe the best way to build trust in AI-generated market intelligence
          is to make the raw data and methodology fully inspectable.
        </p>

        <ul style={{ color: 'var(--color-text-secondary)', lineHeight: 1.8, paddingLeft: 'var(--space-4)' }}>
          <li>
            <a href="https://github.com/szkakalau/aimfast.dev">Source code on GitHub</a> — the entire pipeline
          </li>
          <li>
            <a href="/dashboard/data/dashboard.json">Dashboard JSON</a> — daily bundle with signals, reports, and decisions
          </li>
          <li>
            <a href="/llms-full.txt">llms-full.txt</a> — complete AI-readable methodology reference
          </li>
          <li>
            <a href="/llms.txt">llms.txt</a> — concise AI site index
          </li>
          <li>
            <a href="/sitemap.xml">Sitemap</a> — all indexed pages
          </li>
        </ul>
      </section>

      {/* ═══════ Contact ═══════ */}
      <section style={{ padding: 'var(--space-8) 0 var(--space-10)', maxWidth: '720px', margin: '0 auto' }}>
        <div className="section-header">
          <h2>Contact</h2>
        </div>

        <p style={{ color: 'var(--color-text-secondary)', lineHeight: 1.7 }}>
          For questions, feedback, or collaboration inquiries:{' '}
          <a href="mailto:support@aimfast.dev">support@aimfast.dev</a>
        </p>

        <div style={{ display: 'flex', gap: 'var(--space-4)', marginTop: 'var(--space-3)' }}>
          <a href="https://github.com/szkakalau/aimfast.dev" target="_blank" rel="noopener noreferrer">
            GitHub →
          </a>
          <a href="https://twitter.com/aimfastdev" target="_blank" rel="noopener noreferrer">
            X/Twitter →
          </a>
        </div>
      </section>

      {/* ═══════ Footer ═══════ */}
      <footer className="site-footer">
        <div className="footer-links">
          <a href="/">Trends</a>
          <span className="footer-sep">|</span>
          <a href="/dashboard/">Dashboard</a>
          <span className="footer-sep">|</span>
          <a href="/reports/">Reports</a>
          <span className="footer-sep">|</span>
          <a href="/pricing/">Pricing</a>
        </div>
        <div className="footer-copy">
          AimFast.Dev — Daily Market Intelligence for Indie Builders
        </div>
      </footer>
    </main>
  );
}
