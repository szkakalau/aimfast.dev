import type { Metadata } from 'next';
import { TrendingUp, BarChart3, Globe, Zap, Search, Shield } from 'lucide-react';
// Trends data module is the single source of truth for types + stage labels.
// The homepage IS the trends discovery page — this cross-route import is intentional.
import { getAllTrendTerms, getTrendStats } from './trends/data';
import TrendFilter from './trends/TrendFilter';

export const metadata: Metadata = {
  title: 'Trend Discovery — Emerging Tech Terms & Market Signals | AimFast.Dev',
  description:
    'Discover emerging technology terms, concepts, and market signals before they trend. Free daily tracking of nascent tech across 21+ sources. No signup required.',
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
      'Track emerging tech terms before they trend. Daily updates from 21+ sources. Free. No signup required.',
    url: 'https://www.aimfast.dev/',
    siteName: 'AimFast.Dev',
    locale: 'en',
    images: [
      {
        url: 'https://www.aimfast.dev/og-home.png',
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
    images: ['https://www.aimfast.dev/og-home.png'],
  },
};

/* ── Page ── */

export default function HomePage() {
  const data = getAllTrendTerms();
  const { terms, updated_at } = data;
  const stats = getTrendStats();

  // Compute stage distribution for first-party data display
  const stageCounts = { nascent: 0, emergent: 0, validating: 0, rising: 0 };
  for (const t of terms) {
    const s = t.stage as keyof typeof stageCounts;
    if (s in stageCounts) stageCounts[s]++;
  }
  const topTerms = [...terms].sort((a, b) => b.score - a.score).slice(0, 5);
  const avgScore = terms.length > 0 ? Math.round(terms.reduce((sum, t) => sum + t.score, 0) / terms.length) : 0;
  const updatedAtFormatted = updated_at
    ? updated_at.slice(0, 16).replace('T', ' ') + ' CST'
    : '';

  const jsonLd = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://www.aimfast.dev/' },
        ],
      },
      {
        '@type': 'CollectionPage',
        name: 'Trend Discovery — AimFast.Dev',
        description:
          'Discover emerging technology terms, concepts, and market signals before they trend.',
        url: 'https://www.aimfast.dev/',
        inLanguage: 'en',
        dateModified: updated_at || new Date().toISOString().slice(0, 10),
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
      {
        '@type': 'HowTo',
        name: 'How Trends Are Scored & Discovered',
        description:
          'Every trend is automatically scored and staged by our pipeline across 21+ sources.',
        step: [
          {
            '@type': 'HowToStep',
            position: 1,
            name: 'Cross-source validation',
            text: 'A term must appear in 2 or more independent sources — not a single isolated post.',
          },
          {
            '@type': 'HowToStep',
            position: 2,
            name: 'Representative filtering',
            text: 'New products are kept only if they represent a broader emerging pattern, not one-off launches.',
          },
          {
            '@type': 'HowToStep',
            position: 3,
            name: 'Discussion volume threshold',
            text: 'Low-score single posts don\'t qualify; there must be genuine community interest.',
          },
          {
            '@type': 'HowToStep',
            position: 4,
            name: 'Generic term blacklist',
            text: 'Known broad terms like AI, React, Python, API, LLM, GPT are automatically ignored.',
          },
          {
            '@type': 'HowToStep',
            position: 5,
            name: 'Quality over quantity',
            text: 'Quality over quantity — only terms with genuine cross-source validation are accepted. No numeric cap.',
          },
        ],
      },
      {
        '@type': 'FAQPage',
        mainEntity: [
          {
            '@type': 'Question',
            name: 'How are trends discovered?',
            acceptedAnswer: {
              '@type': 'Answer',
              text: `Our AI scans 21+ sources daily — HN, Reddit, GitHub, DEV Community, Lobsters, V2EX, X/Twitter, Product Hunt, HuggingFace, Arxiv, npm, PyPI, Stack Overflow, YouTube, and more — cross-referencing emerging terms and scoring them by signal strength, source diversity, and community engagement.`,
            },
          },
          {
            '@type': 'Question',
            name: 'How often is the data updated?',
            acceptedAnswer: {
              '@type': 'Answer',
              text: `Daily at 08:30 CST. New terms are discovered, existing terms are rescored, and market intelligence reports are regenerated every morning.`,
            },
          },
          {
            '@type': 'Question',
            name: 'Is AimFast.Dev free?',
            acceptedAnswer: {
              '@type': 'Answer',
              text: `Yes — trend discovery and tracking is completely free. Paid plans (from $19/mo) add daily decision briefs and full pipeline access. 14-day free trial, no credit card required.`,
            },
          },
        ],
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
        {/* ── Compact Hero ── */}
        <section className="trends-hero">
          <h1>Discover What&apos;s Emerging Before Everyone Else</h1>
          <p className="trends-hero-desc">
            Daily tracking of new tech terms, concepts, and market signals
            across {stats.totalSources}+ sources. Free. No signup required.
          </p>
          <div className="trends-hero-stats">
            <TrendingUp size={14} aria-hidden="true" />
            Tracking <strong>{terms.length} terms</strong>
            {' · '}Updated daily 08:30 CST
          </div>
        </section>

        {/* ── Live Stats Bar — AimFast.Dev Proprietary Data ── */}
        {stats.total > 0 && (
          <div className="live-stats" aria-label="Trend tracking statistics" data-source="AimFast.Dev proprietary">
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
            <span className="live-stat">
              <BarChart3 size={16} aria-hidden="true" />
              Avg Score <span className="live-stat-value">{avgScore}</span>
            </span>
            <span className="live-stat-sep" aria-hidden="true">·</span>
            <span className="live-stat">Updated {updatedAtFormatted || 'daily 08:30 CST'}</span>
          </div>
        )}

        {/* ── Proprietary Data Provenance Note ── */}
        <div style={{
          textAlign: 'center', fontSize: '0.75rem', color: 'var(--color-text-muted, #9ca3af)',
          marginTop: 'calc(var(--space-1) * -1)', marginBottom: 'var(--space-5)',
          overflowWrap: 'break-word',
        }}>
          <span style={{ fontWeight: 600, color: 'var(--color-accent, #2563eb)' }}>AimFast.Dev Proprietary Data</span>
          {' — '}Stage distribution: Nascent {stageCounts.nascent} · Emergent {stageCounts.emergent} · Validating {stageCounts.validating} · Rising {stageCounts.rising}
          {' — '}Top terms: {topTerms.map((t) => t.canonical).join(', ')}
        </div>

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
                  <span>Top 25%</span> deep research report ·{' '}
                  <span>30–59</span> quick brief ·{' '}
                  <span>&lt;30</span> tracking only
                </span>
              </p>
            </div>

            {/* Card B: Discovery */}
            <div className="engine-card">
              <h3><Search size={20} /> How Terms Are Discovered</h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)', marginBottom: 'var(--space-2)' }}>
                Every night, our LLM pipeline scans signals from 21+ sources and extracts emerging terms using 5 rules:
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
                  <strong>Quality over quantity</strong> — only terms with genuine cross-source validation are accepted. No numeric cap.
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
                AI scans 21+ sources — HN, Reddit, GitHub, Product Hunt, X, DEV,
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
                Track up to 10 topics, people, or tech stacks.
                Every day, the AI tells you what's happening, and — most importantly
                — what <em>you</em> should do about it.
              </p>
              <ul className="engine-list">
                <li>Topic trend tracking</li>
                <li>Pricing & feature change signals</li>
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
            One decision card · Trend signals · 2 minutes to read
          </div>
        </section>

        {/* ── CTA ── */}
        <section className="trends-cta">
          <h2>Want the full picture?</h2>
          <p>
            Every morning, our Discovery Engine scans {stats.totalSources}+ sources and
            distills signals like these into one actionable decision — with
            pricing, validation, and market context.
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
