import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import type { Metadata } from 'next';
import { TrendingUp, Calendar, BarChart3, Activity, Globe } from 'lucide-react';
import type { TrendTerm, TrendTermsData } from './types';
import { stageLabel } from './data';

export const metadata: Metadata = {
  title: 'Trend Discovery — Emerging Tech Terms & Concepts | AimFast.Dev',
  description:
    'Discover emerging technology terms, concepts, and market signals before they trend. Free daily tracking of nascent tech across 11+ sources.',
  robots: { index: true, follow: true },
  alternates: {
    canonical: 'https://www.aimfast.dev/trends/',
    languages: {
      'zh-CN': 'https://www.aimfast.dev/trends/zh/',
      en: 'https://www.aimfast.dev/trends/',
    },
  },
  openGraph: {
    title: 'Trend Discovery — Emerging Tech Terms | AimFast.Dev',
    description:
      'Track emerging tech terms before they trend. Daily updates from 11+ sources. Free. No signup required.',
    url: 'https://www.aimfast.dev/trends/',
    siteName: 'AimFast.Dev',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Trend Discovery — Emerging Tech Terms | AimFast.Dev',
    description:
      'Discover emerging tech terms before they trend. Free daily tracking.',
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

/* ── Page ── */

export default function TrendsPage() {
  const data = getTrendTerms();
  const { terms, updated_at } = data;
  const totalSources = [...new Set(terms.flatMap((t) => t.sources))].length;

  const jsonLd = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'CollectionPage',
        name: 'Trend Discovery — AimFast.Dev',
        description:
          'Discover emerging technology terms, concepts, and market signals before they trend.',
        url: 'https://www.aimfast.dev/trends/',
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
            across {totalSources}+ sources. Free. No signup required.
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

        {/* ── CTA ── */}
        <section className="trends-cta">
          <h2>Want the full picture?</h2>
          <p>
            Every morning, our Discovery Engine scans {totalSources}+ sources and
            distills signals like these into one actionable decision — with
            pricing, validation, and competitor context.
          </p>
          <a
            href="/"
            className="btn btn-primary"
            style={{ fontSize: '1rem', padding: '14px 32px' }}
          >
            Start Free Trial →
          </a>
        </section>

        {/* ── Footer ── */}
        <footer className="site-footer">
          <div className="footer-links">
            <a href="/">Home</a>
            <span className="footer-sep">|</span>
            <a href="/dashboard/">Dashboard</a>
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
