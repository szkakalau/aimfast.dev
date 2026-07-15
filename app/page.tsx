import type { Metadata } from 'next';
import { TrendingUp, BarChart3, Globe, Zap, Search, Shield } from 'lucide-react';
// Trends data module is the single source of truth for types + stage labels.
// The homepage IS the trends discovery page — this cross-route import is intentional.
import { getAllTrendTerms, getTrendStats } from './trends/data';
import TrendFilter from '@/components/TrendFilter';

export const metadata: Metadata = {
  title: 'Trend Discovery — Emerging Tech Terms & Market Signals | AimFast.Dev',
  description:
    'Discover emerging technology terms, concepts, and market signals before they trend. Free daily tracking of nascent tech across 11+ sources. No signup required.',
  robots: { index: true, follow: true },
  alternates: {
    canonical: 'https://www.aimfast.dev/',
    languages: {
      en: 'https://www.aimfast.dev/',
      'zh-CN': 'https://www.aimfast.dev/zh/',
    },
  },
  openGraph: {
    title: 'Trend Discovery — Emerging Tech Terms | AimFast.Dev',
    description:
      'Track emerging tech terms before they trend. Daily updates from 11+ sources. Free. No signup required.',
    url: 'https://www.aimfast.dev/',
    siteName: 'AimFast.Dev',
    images: [
      {
        url: 'https://www.aimfast.dev/og-image.png',
        width: 1200,
        height: 630,
        alt: 'AimFast.Dev — Trend Discovery',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Trend Discovery — Emerging Tech Terms | AimFast.Dev',
    description:
      'Discover emerging tech terms before they trend. Free daily tracking.',
    images: ['https://www.aimfast.dev/og-image.png'],
  },
};

/* ── Page ── */

export default function HomePage() {
  const data = getAllTrendTerms();
  const { terms, updated_at } = data;
  const stats = getTrendStats();

  const jsonLd = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'CollectionPage',
        name: 'Trend Discovery — AimFast.Dev',
        description:
          'Discover emerging technology terms, concepts, and market signals before they trend.',
        url: 'https://www.aimfast.dev/',
        inLanguage: 'en',
        mainEntity: {
          '@type': 'ItemList',
          itemListElement: terms.map((t, i) => ({
            '@type': 'ListItem',
            position: i + 1,
            url: `https://www.aimfast.dev/trends/${t.id.replace('trend-', '')}/`,
            name: t.canonical,
          })),
        },
      },

      // Organization + WebSite declared in root layout head — not duplicated here
    ],
  };

  return (
    <>
      {/* Safe: JSON.stringify escapes all HTML entities. No user input in jsonLd. */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <main className="trends-page">
        {/* ── Compact status bar (replaces hero for returning users) ── */}
        <div className="trends-status-bar" role="status" aria-label="Trend tracking status">
          <h1 className="sr-only">AimFast.Dev — Discover What&apos;s Emerging Before Everyone Else</h1>
          <div className="trends-status-content">
            <span className="trends-status-stat">
              <TrendingUp size={14} aria-hidden="true" />
              <strong>{terms.length}</strong> terms tracked across {stats.totalSources}+ sources
            </span>
            <span className="trends-status-sep" aria-hidden="true" />
            <span className="trends-status-stat">
              Updated daily 08:30 CST
            </span>
          </div>
        </div>

        {/* ── Live Stats Bar ── */}
        {stats.total > 0 && (
          <div className="live-stats" aria-label="Trend tracking statistics">
            <span className="live-stat">
              <TrendingUp size={16} aria-hidden="true" />
              <span className="live-stat-value">{stats.total}</span> terms tracked
            </span>
            <span className="live-stat-sep" aria-hidden="true">·</span>
            <span className="live-stat">
              <Zap size={16} aria-hidden="true" />
              <span className="live-stat-value">{stats.withResearch}</span> research reports
            </span>
            <span className="live-stat-sep" aria-hidden="true">·</span>
            <span className="live-stat">
              <Globe size={16} aria-hidden="true" />
              <span className="live-stat-value">{stats.totalSources}</span>+ sources
            </span>
            <span className="live-stat-sep" aria-hidden="true">·</span>
            <span className="live-stat">Updated daily 08:30 CST</span>
          </div>
        )}

        {/* ── Stage Filter + Trend Grid (client component) ── */}
        <TrendFilter terms={terms} />

        {/* ── Methodology: How Trends Are Ranked & Discovered ── */}
        <section className="methodology-section">
          <div className="section-header">
            <h2>How Trends Are Ranked &amp; Discovered</h2>
            <p>
              Every trend you see below is automatically scored and staged by our pipeline.
              Here&apos;s exactly how it works.
            </p>
          </div>

          <div className="engine-grid">
            {/* Card A: Scoring */}
            <div className="engine-card">
              <h3><BarChart3 size={20} /> How We Score</h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)', marginBottom: 'var(--space-2)' }}>
                Each term gets a 0–100 score from four weighted dimensions:
              </p>
              <div className="score-formula">
                Score = Signal Avg × 0.3<br />
                &nbsp;&nbsp;+ Sources × 8 (max 30)<br />
                &nbsp;&nbsp;+ Engagement × 0.5 (max 20)<br />
                &nbsp;&nbsp;+ Cross-Platform × 10 (max 20)
              </div>

              <p style={{ fontSize: '0.82rem', color: 'var(--color-text-secondary)', marginBottom: 'var(--space-2)' }}>
                <strong>Maturity stages</strong> — based on days since first detection:
              </p>
              <div className="stage-legend">
                <span className="stage-legend-item">
                  <span className="stage-legend-dot nascent" /> Nascent (0–7d)
                </span>
                <span className="stage-legend-item">
                  <span className="stage-legend-dot emergent" /> Emergent (8–30d)
                </span>
                <span className="stage-legend-item">
                  <span className="stage-legend-dot validating" /> Validating (31–90d)
                </span>
                <span className="stage-legend-item">
                  <span className="stage-legend-dot rising" /> Rising (90d+)
                </span>
              </div>

              <p style={{ fontSize: '0.82rem', color: 'var(--color-text-secondary)', marginTop: 'var(--space-2)' }}>
                <strong>Report thresholds:</strong>{' '}
                <span className="threshold-list">
                  <span>≥60</span> deep research report ·{' '}
                  <span>30–59</span> quick brief ·{' '}
                  <span>&lt;30</span> tracking only
                </span>
              </p>
            </div>

            {/* Card B: Discovery */}
            <div className="engine-card">
              <h3><Search size={20} /> How Terms Are Discovered</h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)', marginBottom: 'var(--space-2)' }}>
                Every night, our LLM pipeline scans signals from 11+ sources and extracts emerging terms using 5 rules:
              </p>
              <ul>
                <li>
                  <strong>Cross-source validation</strong> — a term must appear in ≥2 independent sources, not a single isolated post.
                </li>
                <li>
                  <strong>Representative filtering</strong> — new products are only kept if they represent a broader emerging pattern, not one-off launches.
                </li>
                <li>
                  <strong>Discussion volume threshold</strong> — low-score single posts don&apos;t qualify; there must be genuine community interest.
                </li>
                <li>
                  <strong>Generic term blacklist</strong> — known broad terms (AI, React, Python, API, LLM, GPT) are automatically ignored.
                </li>
                <li>
                  <strong>Quality over quantity</strong> — capped at 20 new terms per day; fewer is better than noise.
                </li>
              </ul>
              <p style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)', marginTop: 'var(--space-2)' }}>
                Sources: HN, Reddit, GitHub, Product Hunt, X, DEV Community, V2EX, Lobsters, and more.
              </p>
            </div>
          </div>
        </section>

        {/* ── How It Works (mini) ── */}
        <section className="workflow" style={{ padding: 'var(--space-8) 0' }}>
          <div className="section-header">
            <h2>Two Engines, One Report</h2>
            <p>
              Every night, our dual-engine system scans the internet. Every morning,
              you get one decision.
            </p>
          </div>

          <div className="engine-grid">
            <div className="engine-card">
              <Search size={32} className="engine-icon" />
              <h3>Discovery Engine</h3>
              <p>
                AI scans 11+ sources — HN, Reddit, GitHub, Product Hunt, X, DEV,
                V2EX, and more — for emerging pain points, rising trends, and
                market gaps.
              </p>
              <ul className="engine-list">
                <li>Cross-platform signal validation</li>
                <li>Pain point vs. hype detection</li>
                <li>Actionability scoring</li>
              </ul>
            </div>

            <div className="engine-card">
              <Shield size={32} className="engine-icon" />
              <h3>Monitoring Engine</h3>
              <p>
                Track up to 10 competitors, topics, people, or tech stacks.
                Every day, the AI tells you what they did, and — most importantly
                — what <em>you</em> should do about it.
              </p>
              <ul className="engine-list">
                <li>Competitor pricing & feature changes</li>
                <li>Topic trend tracking</li>
                <li>Actionable alerts, not noise</li>
              </ul>
            </div>
          </div>

          <div className="engine-arrow" aria-hidden="true">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 5v14M5 12l7 7 7-7" />
            </svg>
          </div>

          <div className="engine-output">
            <span className="engine-output-label">Daily Report</span>
            One decision card · Competitor updates · System pulse · 2 minutes to read
          </div>
        </section>

        {/* ── CTA ── */}
        <section className="trends-cta">
          <h2>Want the full picture?</h2>
          <p>
            Every morning, our Discovery Engine scans {stats.totalSources}+ sources and
            distills signals like these into one actionable decision — with
            pricing, validation, and competitor context.
          </p>
          <a
            href="/dashboard/"
            className="btn btn-primary"
            style={{ fontSize: '1rem', padding: '14px 32px' }}
          >
            View Dashboard →
          </a>
        </section>

        {/* ── Footer ── */}
        <footer className="site-footer">
          <div className="footer-links">
            <a href="/dashboard/">Dashboard</a>
            <span className="footer-sep">|</span>
            <a href="/pricing/">Pricing</a>
            <span className="footer-sep">|</span>
            <a href="/reports/">Reports</a>
          </div>
          <div className="footer-copy">
            AimFast.Dev — Updated{' '}
            {updated_at ? updated_at.slice(0, 10) : 'daily'} · Free trend
            discovery
          </div>
        </footer>
      </main>
    </>
  );
}
