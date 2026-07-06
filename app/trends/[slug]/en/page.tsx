import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import type { Metadata } from 'next';
import { marked } from 'marked';
import {
  Calendar,
  TrendingUp,
  Activity,
  BarChart3,
  ArrowUpRight,
  Hash,
} from 'lucide-react';

/* ── Types ── */

interface TrendTerm {
  id: string;
  canonical: string;
  aliases: string[];
  first_seen: string;
  last_seen: string;
  stage: 'nascent' | 'emergent' | 'validating' | 'rising';
  score: number;
  source_count: number;
  total_mentions: number;
  sources: string[];
  growth_pct: number;
  category: string;
  tags: string[];
  summary_zh: string;
  summary_en: string;
  research_md_path: string;
}

interface TrendTermsData {
  updated_at: string;
  terms: TrendTerm[];
}

/* ── Data ── */

function getAllTrendTerms(): TrendTermsData {
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

function getTrendTerm(slug: string): TrendTerm | null {
  const termId = `trend-${slug}`;
  const data = getAllTrendTerms();
  return data.terms.find((t) => t.id === termId) || null;
}

function getResearchContent(path: string): string {
  try {
    const fullPath = join(process.cwd(), path);
    if (!existsSync(fullPath)) return '';
    return readFileSync(fullPath, 'utf-8');
  } catch {
    return '';
  }
}

/* ── Static params ── */

export function generateStaticParams() {
  const data = getAllTrendTerms();
  return data.terms.map((term) => ({
    slug: term.id.replace('trend-', ''),
  }));
}

/* ── Metadata ── */

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const term = getTrendTerm(slug);
  if (!term) {
    return { title: 'Trend Not Found — AimFast.Dev' };
  }

  const title = `${term.canonical} — Trend Report | AimFast.Dev`;
  const description = term.summary_en || term.summary_zh;
  const url = `https://www.aimfast.dev/trends/${slug}/en/`;

  return {
    title,
    description,
    robots: { index: true, follow: true },
    alternates: {
      canonical: url,
      languages: {
        'zh-CN': `https://www.aimfast.dev/trends/${slug}/`,
        'en': `https://www.aimfast.dev/trends/${slug}/en/`,
      },
    },
    openGraph: {
      title,
      description,
      url,
      siteName: 'AimFast.Dev',
      type: 'article',
    },
    twitter: {
      card: 'summary_large_image',
      title,
      description,
    },
  };
}

/* ── Helpers ── */

function stageLabel(stage: string): string {
  const map: Record<string, string> = {
    nascent: 'Nascent (0–7 days)',
    emergent: 'Emergent (8–30 days)',
    validating: 'Validating (31–90 days)',
    rising: 'Rising (90+ days)',
  };
  return map[stage] || stage;
}

/* ── Page ── */

export default async function TrendDetailEnPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const term = getTrendTerm(slug);

  if (!term) {
    return (
      <main className="trend-detail">
        <div className="trends-empty">
          <h2>Trend not found</h2>
          <p>
            <a href="/trends/">← Back to all trends</a>
          </p>
        </div>
      </main>
    );
  }

  const researchMd = getResearchContent(term.research_md_path);
  let researchHtml = '';
  if (researchMd) {
    const bodyOnly = researchMd.replace(/^---[\s\S]*?---\n*/, '').trim();
    researchHtml = await marked.parse(bodyOnly);
  }

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: `${term.canonical} — Trend Report`,
    description: term.summary_en,
    url: `https://www.aimfast.dev/trends/${slug}/en/`,
    datePublished: term.first_seen,
    dateModified: term.last_seen,
    author: { '@type': 'Organization', name: 'AimFast.Dev' },
    inLanguage: 'en',
    mainEntityOfPage: {
      '@type': 'WebPage',
      '@id': `https://www.aimfast.dev/trends/${slug}/en/`,
    },
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <main className="trend-detail">
        {/* ── Breadcrumb ── */}
        <div className="trend-detail-breadcrumb">
          <a href="/trends/">← Back to all trends</a>
          {' · '}
          <a href={`/trends/${slug}/`}>中文</a>
        </div>

        {/* ── Header ── */}
        <div className="trend-detail-header">
          <span className={`stage-badge ${term.stage}`}>
            {stageLabel(term.stage)}
          </span>
          <h1>{term.canonical}</h1>

          <div className="trend-detail-sources">
            {term.sources.map((s) => (
              <span key={s} className="trend-source-badge">
                {s}
              </span>
            ))}
          </div>

          <div className="trend-detail-meta-row" style={{ marginTop: 'var(--space-3)' }}>
            <span className="trend-detail-meta-item">
              <Calendar size={14} />
              First seen <strong>{term.first_seen}</strong>
            </span>
            <span className="trend-detail-meta-item">
              <Calendar size={14} />
              Last seen <strong>{term.last_seen}</strong>
            </span>
            <span className="trend-detail-meta-item">
              <BarChart3 size={14} />
              Score <strong>{term.score}</strong>
            </span>
            <span className="trend-detail-meta-item">
              <Activity size={14} />
              <strong>{term.source_count}</strong> sources
            </span>
            <span className="trend-detail-meta-item">
              <Hash size={14} />
              <strong>{term.total_mentions}</strong> mentions
            </span>
            <span className="trend-detail-meta-item">
              <TrendingUp size={14} />
              Growth <strong>+{term.growth_pct}%</strong>
            </span>
          </div>
        </div>

        {/* ── Content + Sidebar Layout ── */}
        <div className="trend-detail-layout">
          <div className="trend-detail-content">
            {researchHtml ? (
              <div
                className="report-content"
                dangerouslySetInnerHTML={{ __html: researchHtml }}
              />
            ) : (
              <p style={{ color: 'var(--color-text-muted)' }}>
                Research report not yet generated. Check back soon.
              </p>
            )}
          </div>

          <aside className="trend-sidebar">
            <div className="trend-sidebar-card">
              <h4>About This Trend</h4>
              <p>{term.summary_en || term.summary_zh}</p>
              <div style={{ fontSize: '0.82rem', color: 'var(--color-text-secondary)', lineHeight: '1.8' }}>
                <div>
                  <strong>Category:</strong> {term.category}
                </div>
                <div>
                  <strong>Tags:</strong>{' '}
                  {term.tags.map((t) => (
                    <span key={t} style={{ color: 'var(--color-accent)', marginRight: '6px' }}>
                      #{t}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <div className="trend-sidebar-card">
              <h4>Want the full picture?</h4>
              <p>
                Get daily competitive intel, product opportunities, and
                monitoring — not just trends.
              </p>
              <a href="/" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center', fontSize: '0.88rem', padding: '10px 20px' }}>
                Start Free Trial
                <ArrowUpRight size={14} />
              </a>
            </div>
          </aside>
        </div>

        {/* ── Bottom CTA ── */}
        <section className="trends-cta" style={{ marginTop: 'var(--space-8)' }}>
          <h2>Don&apos;t just track trends — act on them</h2>
          <p>
            Every morning, get one actionable product opportunity with evidence,
            pricing strategy, and validation path. 14-day free trial.
          </p>
          <a href="/" className="btn btn-primary" style={{ fontSize: '1rem', padding: '14px 32px' }}>
            Start Free Trial →
          </a>
        </section>

        <footer className="site-footer">
          <div className="footer-links">
            <a href="/">Home</a>
            <span className="footer-sep">|</span>
            <a href="/trends/">All Trends</a>
            <span className="footer-sep">|</span>
            <a href="/dashboard/">Dashboard</a>
            <span className="footer-sep">|</span>
            <a href="/reports/">Reports</a>
          </div>
          <div className="footer-copy">
            AimFast.Dev — Trend reports updated daily
          </div>
        </footer>
      </main>
    </>
  );
}
