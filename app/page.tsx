import type { Metadata } from 'next';
import { TrendingUp, BarChart3, Globe, Zap, Search, Shield, Mail, ArrowUpRight, Download, Bell, FileText } from 'lucide-react';
// Trends data module is the single source of truth for types + stage labels.
// The homepage IS the trends discovery page — this cross-route import is intentional.
import { getAllTrendTerms, getTrendStats } from './trends/data';
import TrendFilter from './trends/TrendFilter';

export const metadata: Metadata = {
  title: 'Signal Over Hype — AI-Curated Tech Trends & Market Signals | AimFast.Dev',
  description:
    'AI scans 30+ channels daily, cross-validates every term, and ranks by builder relevance — so you see what\'s worth acting on, not what\'s just loud. Free. No signup.',
  robots: { index: true, follow: true },
  alternates: {
    canonical: 'https://www.aimfast.dev/',
    languages: {
      en: 'https://www.aimfast.dev/',
      'zh-CN': 'https://www.aimfast.dev/zh/',
      'x-default': 'https://www.aimfast.dev/',
    },
  },
  openGraph: {
    title: 'Signal Over Hype — Tech Trends | AimFast.Dev',
    description:
      'AI ranks tech terms by builder relevance — not by hype. Free daily tracking.',
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
    title: 'Signal Over Hype — Tech Trends | AimFast.Dev',
    description:
      'Signal over hype — AI-cross-validated tech terms ranked by builder relevance. Free daily tracking.',
    images: ['https://www.aimfast.dev/og-home.png'],
  },
};

/* ── Page ── */

export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string }>;
}) {
  const sp = await searchParams;
  const initialPage = Math.max(1, parseInt(sp.page || '1', 10) || 1);
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
          'AI scans 30+ channels daily, cross-validates every term, and ranks by builder relevance — signal over hype.',
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
          'Every trend is automatically scored and staged by our pipeline across 30+ platforms.',
        step: [
          {
            '@type': 'HowToStep',
            position: 1,
            name: 'Cross-platform validation',
            text: 'A term must appear in 2 or more independent platforms — not a single isolated post.',
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
              text: `Our AI scans 30+ platforms daily — HN, Reddit, GitHub, DEV Community, Lobsters, V2EX, X/Twitter, Product Hunt, HuggingFace, Arxiv, npm, PyPI, Stack Overflow, YouTube, and more — cross-referencing emerging terms and scoring them by signal strength, channel diversity, and community engagement.`,
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
              text: `Yes — trend discovery and monitoring is completely free. Paid plans (from $19/mo) add daily decision briefs and full pipeline access. 14-day free trial, no credit card required.`,
            },
          },
        ],
      },

      {
        '@type': 'Person',
        name: 'Kakalau',
        url: 'https://github.com/szkakalau',
        sameAs: [
          'https://github.com/szkakalau',
          'https://twitter.com/aimfastdev',
        ],
        jobTitle: 'Founder & Builder',
        worksFor: {
          '@type': 'Organization',
          name: 'AimFast.Dev',
          url: 'https://www.aimfast.dev/',
        },
        description:
          'Independent builder behind AimFast.Dev — automated trend discovery and market intelligence for indie builders.',
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
        {/* ── Hero — Value Ladder: Free Discovery → Pro Deep Analysis ── */}
        <section className="trends-hero">
          <h1>Stop Guessing What to Build.</h1>
          <p className="trends-hero-desc">
            Every morning, AI scans 28 platforms, cross-validates signals, and ranks
            emerging tech trends by builder relevance. <strong>Free tier</strong> shows
            you what&apos;s trending. <strong>Pro</strong> gives you the full business
            case — TAM, MVP blueprint, pricing strategy, and risk assessment — so you
            know exactly what to build and how.
          </p>

          <div className="hero-cta-row">
            <a href="/register/" className="btn btn-primary" style={{ fontSize: '1rem', padding: '14px 32px' }}>
              Start Free Trial <ArrowUpRight size={16} />
            </a>
            <a href="#trend-grid" className="btn btn-secondary" style={{ fontSize: '0.95rem', padding: '14px 28px' }}>
              Browse Trends ↓
            </a>
          </div>

          <div className="trends-hero-stats">
            <TrendingUp size={14} aria-hidden="true" />
            <strong>{terms.length} terms</strong> tracked across 28 sources
            {' · '}Updated daily 08:30 CST
            {' · '}<span style={{ color: 'var(--color-green)' }}>14-day free trial, no card required</span>
          </div>
        </section>

        {/* ── Newsletter Subscribe ── */}
        <section className="newsletter-section">
          <div className="newsletter-card">
            <div className="newsletter-text">
              <Mail size={20} aria-hidden="true" />
              <div>
                <h3>Weekly Founder's Letter</h3>
                <p>The real thinking behind the scores — what the pipeline found, why it matters, and what to build next. One email per week.</p>
              </div>
            </div>
            <a
              href="https://buttondown.com/aimfast"
              target="_blank"
              rel="noopener noreferrer"
              className="newsletter-submit"
              style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', textDecoration: 'none' }}
            >
              Subscribe Free →
            </a>
          </div>
        </section>

        {/* ── Live Stats Bar — AimFast.Dev Proprietary Data ── */}
        {stats.total > 0 && (
          <div className="live-stats" aria-label="Trend tracking statistics" data-source="AimFast.Dev proprietary">
            <span className="live-stat">
              <TrendingUp size={16} aria-hidden="true" />
              <span className="live-stat-value">{stats.total}</span> terms monitored
            </span>
            <span className="live-stat-sep" aria-hidden="true">·</span>
            <span className="live-stat">
              <Zap size={16} aria-hidden="true" />
              <span className="live-stat-value">{stats.withResearch}</span> research reports
            </span>
            <span className="live-stat-sep" aria-hidden="true">·</span>
            <span className="live-stat">
              <Globe size={16} aria-hidden="true" />
              <span className="live-stat-value">30</span>+ platforms
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
        <div id="trend-grid">
          <TrendFilter terms={terms} initialPage={initialPage} />
        </div>

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
                Score = weighted composite of four dimensions:<br />
                &nbsp;&nbsp;• Channel diversity (highest weight)<br />
                &nbsp;&nbsp;• Signal strength across independent platforms<br />
                &nbsp;&nbsp;• Community engagement velocity<br />
                &nbsp;&nbsp;• Cross-platform propagation
              </div>

              <p style={{ fontSize: '0.82rem', color: 'var(--color-text-secondary)', marginBottom: 'var(--space-2)' }}>
                <strong>Maturity stages</strong> — based on age since first detection:
              </p>
              <div className="stage-legend">
                <span className="stage-legend-item">
                  <span className="stage-legend-dot nascent" /> Nascent
                </span>
                <span className="stage-legend-item">
                  <span className="stage-legend-dot emergent" /> Emergent
                </span>
                <span className="stage-legend-item">
                  <span className="stage-legend-dot validating" /> Validating
                </span>
                <span className="stage-legend-item">
                  <span className="stage-legend-dot rising" /> Rising
                </span>
              </div>

              <p style={{ fontSize: '0.82rem', color: 'var(--color-text-secondary)', marginTop: 'var(--space-2)' }}>
                <strong>Report thresholds:</strong>{' '}
                <span className="threshold-list">
                  <span>Top tier</span> deep research report ·{' '}
                  <span>Mid range</span> quick brief ·{' '}
                  <span>Lower range</span> monitoring only
                </span>
              </p>
            </div>

            {/* Card B: Discovery */}
            <div className="engine-card">
              <h3><Search size={20} /> How Terms Are Discovered</h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)', marginBottom: 'var(--space-2)' }}>
                Every night, our LLM pipeline scans signals from 30+ platforms and extracts emerging terms using 5 rules:
              </p>
              <ul>
                <li>
                  <strong>Cross-platform validation</strong> — a term must appear in ≥2 independent platforms, not a single isolated post.
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
                Sources:{' '}
                <a href="https://news.ycombinator.com" target="_blank" rel="noopener noreferrer" style={{ color: 'inherit', textDecoration: 'underline' }}>HN</a>,{' '}
                <a href="https://reddit.com" target="_blank" rel="noopener noreferrer" style={{ color: 'inherit', textDecoration: 'underline' }}>Reddit</a>,{' '}
                <a href="https://github.com/trending" target="_blank" rel="noopener noreferrer" style={{ color: 'inherit', textDecoration: 'underline' }}>GitHub</a>,{' '}
                <a href="https://www.producthunt.com" target="_blank" rel="noopener noreferrer" style={{ color: 'inherit', textDecoration: 'underline' }}>Product Hunt</a>,{' '}
                <a href="https://x.com" target="_blank" rel="noopener noreferrer" style={{ color: 'inherit', textDecoration: 'underline' }}>X</a>,{' '}
                <a href="https://dev.to" target="_blank" rel="noopener noreferrer" style={{ color: 'inherit', textDecoration: 'underline' }}>DEV Community</a>,{' '}
                <a href="https://www.v2ex.com" target="_blank" rel="noopener noreferrer" style={{ color: 'inherit', textDecoration: 'underline' }}>V2EX</a>,{' '}
                <a href="https://lobste.rs" target="_blank" rel="noopener noreferrer" style={{ color: 'inherit', textDecoration: 'underline' }}>Lobsters</a>, and more.
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
              you get one decision — validated, priced, and ready to execute.
            </p>
          </div>

          <div className="engine-grid">
            <div className="engine-card">
              <Search size={32} className="engine-icon" />
              <h3>Discovery Engine</h3>
              <p>
                AI scans 30+ platforms — HN, Reddit, GitHub, Product Hunt, X, DEV,
                V2EX, and more — for emerging pain points, rising trends, and
                market gaps. Every term is cross-validated across independent sources
                before it reaches your dashboard.
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
                Follow up to 10 topics, people, or tech stacks.
                Every day, the AI tells you what's happening, and — most importantly
                — what <em>you</em> should do about it. Track competitors, spot
                shifts in developer sentiment, and catch opportunities before
                they hit the mainstream.
              </p>
              <ul className="engine-list">
                <li>Topic trend analysis</li>
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
            One decision card · Trend signals · Competitive analysis · 2 minutes to read
          </div>
        </section>

        {/* ── Pro Features Showcase ── */}
        <section className="pro-showcase">
          <div className="section-header">
            <h2>What You Get with Pro</h2>
            <p>
              Free tier shows you what&apos;s trending. Pro gives you the full
              business case — TAM, MVP blueprint, pricing, risk assessment, and
              a concrete action plan. Built for builders who want to stop
              reading and start building.
            </p>
          </div>

          <div className="pro-grid">
            <div className="pro-card">
              <FileText size={28} className="pro-card-icon" />
              <h3>Deep Analysis Reports</h3>
              <p>
                Full business cases for the top 25% of trends. Each report
                includes TAM estimation, competitive landscape, business model
                recommendations, MVP blueprint, risk assessment, and concrete
                next steps — 3,000+ words of actionable intelligence.
              </p>
              <span className="pro-card-stat">19 reports · Updated daily</span>
            </div>

            <div className="pro-card">
              <Download size={28} className="pro-card-icon" />
              <h3>CSV & JSON Export</h3>
              <p>
                Download the full trend database for your own analysis. Feed it
                into your spreadsheet, notebook, or custom tooling. All 280+
                terms with scores, categories, stages, and growth metrics.
              </p>
              <span className="pro-card-stat">CSV + JSON · One click</span>
            </div>

            <div className="pro-card">
              <Bell size={28} className="pro-card-icon" />
              <h3>Custom Trend Alerts</h3>
              <p>
                Set keyword and category alerts. Get notified when a trend
                matching your criteria crosses your score threshold. Never miss
                an opportunity in your domain again.
              </p>
              <span className="pro-card-stat">Up to 10 alerts</span>
            </div>
          </div>

          <div className="pro-cta-center">
            <a href="/register/" className="btn btn-primary" style={{ fontSize: '1rem', padding: '14px 36px' }}>
              Start 14-Day Free Trial — No Card Required <ArrowUpRight size={16} />
            </a>
            <p className="pro-cta-sub">
              $19/month after trial. Cancel anytime.
            </p>
          </div>
        </section>

        {/* ── CTA ── */}
        <section className="trends-cta">
          <h2>Ready to stop guessing?</h2>
          <p>
            Join indie builders who start every morning with one verified
            product opportunity — not fifty things to read, but one thing to
            build.
          </p>
          <a
            href="/register/"
            className="btn btn-primary"
            style={{ fontSize: '1rem', padding: '14px 32px' }}
          >
            Start Free Trial →
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
