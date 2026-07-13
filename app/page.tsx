import type { Metadata } from 'next';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { TrendingUp, Calendar, BarChart3, Activity, Globe, Zap, Search, Shield } from 'lucide-react';
// Trends data module is the single source of truth for types + stage labels.
// The homepage IS the trends discovery page — this cross-route import is intentional.
import type { TrendTermsData } from './trends/types';
import { stageLabel } from './trends/data';

export const metadata: Metadata = {
  title: 'Trend Discovery — Emerging Tech Terms & Market Signals | AimFast.Dev',
  description:
    'Discover emerging technology terms, concepts, and market signals before they trend. Free daily tracking of nascent tech across 11+ sources. No signup required.',
  robots: { index: true, follow: true },
  alternates: {
    canonical: 'https://www.aimfast.dev/',
    languages: {
      en: 'https://www.aimfast.dev/',
      'zh-CN': 'https://www.aimfast.dev/',
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

/* ── Data ── */

function getTrendTerms(): TrendTermsData {
  try {
    const raw = readFileSync(
      join(process.cwd(), 'tracking', 'trend_terms.json'),
      'utf-8',
    );
    return JSON.parse(raw) as TrendTermsData;
  } catch {
    return { updated_at: '', terms: [] };
  }
}

function getTrendStats(): { total: number; withResearch: number; totalSources: number } {
  try {
    const data = getTrendTerms();
    const terms = data.terms || [];
    const withResearch = terms.filter((t) => t.research_md_path && t.score >= 60).length;
    const totalSources = new Set(terms.flatMap((t) => t.sources || [])).size;
    return { total: terms.length, withResearch, totalSources };
  } catch {
    return { total: 0, withResearch: 0, totalSources: 0 };
  }
}

/* ── Page ── */

export default function HomePage() {
  const data = getTrendTerms();
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
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <main className="trends-page">
        {/* ── Hero ── */}
        <section className="trends-hero">
          <h1>
            Discover What&apos;s Emerging
            <br />
            Before Everyone Else
          </h1>
          <p className="trends-hero-desc">
            Daily tracking of new tech terms, concepts, and market signals
            across {stats.totalSources}+ sources. Free. No signup required.
          </p>
          <div className="trends-hero-stats">
            <TrendingUp size={14} />
            Tracking <strong>{terms.length} terms</strong>
            {' · '}Updated daily 08:30 CST
          </div>
          <div className="trends-lang-bar">
            <Globe size={13} />
            <span>English</span>
            <span className="lang-sep">·</span>
            <a href="/trends/zh/">中文</a>
          </div>
        </section>

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

        {/* ── Stage Filter ── */}
        {terms.length > 0 && (
          <div className="stage-filter">
            {['all', 'nascent', 'emergent', 'validating', 'rising'].map(
              (s) => (
                <a
                  key={s}
                  href={s === 'all' ? '#trend-grid' : `#stage-${s}`}
                  className="stage-filter-btn"
                >
                  {s === 'all' ? 'All' : stageLabel(s)}
                </a>
              ),
            )}
          </div>
        )}

        {/* ── Trend Grid ── */}
        {terms.length === 0 ? (
          <div className="trends-empty">
            <h2>No trends yet</h2>
            <p>
              Check back after the daily pipeline runs. New terms are added
              every morning.
            </p>
          </div>
        ) : (
          <div className="trend-grid" id="trend-grid">
            {terms.map((term) => {
              const slug = term.id.replace('trend-', '');
              return (
                <a
                  key={term.id}
                  href={`/trends/${slug}/`}
                  className="trend-card"
                >
                  <span className={`stage-badge ${term.stage}`}>
                    {stageLabel(term.stage)}
                  </span>
                  {term.revenue_potential != null && (
                    <span className="trend-card-stars" title={`Revenue potential: ${term.revenue_potential}/5`}>
                      {'★'.repeat(term.revenue_potential)}{'☆'.repeat(5 - term.revenue_potential)}
                    </span>
                  )}
                  <span className="trend-card-category">{term.category}</span>
                  <h3>{term.canonical}</h3>
                  <p className="trend-card-summary">
                    {term.summary_en || term.summary_zh}
                  </p>
                  <div className="trend-card-meta">
                    <span className="trend-card-meta-item">
                      <Calendar size={12} />
                      {term.first_seen}
                    </span>
                    <span className="trend-card-meta-item">
                      <Activity size={12} />
                      {term.source_count} sources
                    </span>
                    <span className="trend-card-meta-item">
                      <BarChart3 size={12} />
                      {term.total_mentions} mentions
                    </span>
                  </div>
                </a>
              );
            })}
          </div>
        )}

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
