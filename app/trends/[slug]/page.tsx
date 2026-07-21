import type { Metadata } from 'next';
import { marked } from 'marked';
import {
  Calendar,
  TrendingUp,
  Activity,
  BarChart3,
  ArrowUpRight,
  Hash,
  Globe,
} from 'lucide-react';

import type { TrendTerm, TrendTermsData } from '../types';
import {
  getAllTrendTerms,
  getTrendTerm,
  getResearchContent,
  getResearchContentEn,
  stageLabel,
  stageLabelZh,
  stagePct,
  sanitizeTrendHtml,
} from '../data';
import { extractSectionText } from '../utils';

/* ── Helpers ── */

function scoreColor(v: number): string {
  if (v >= 70) return 'var(--opp-score-high)';
  if (v >= 40) return 'var(--opp-score-mid)';
  return 'var(--opp-score-low)';
}

/** Inverted: low = green (good), high = red (bad). Used for competition & SEO difficulty. */
function invertScoreColor(v: number): string {
  if (v <= 30) return 'var(--opp-score-high)';
  if (v <= 60) return 'var(--opp-score-mid)';
  return 'var(--opp-score-low)';
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

  const title = `${term.canonical} — Trend Report & Analysis | AimFast.Dev`;
  const description = (term.summary_en || '').slice(0, 160);
  const url = `https://www.aimfast.dev/trends/${slug}/`;

  return {
    title,
    description,
    robots: { index: true, follow: true },
    alternates: {
      canonical: url,
      languages: {
        'zh-CN': `https://www.aimfast.dev/trends/${slug}/zh/`,
        en: url,
      },
    },
    openGraph: {
      title,
      description,
      url,
      siteName: 'AimFast.Dev',
      type: 'article',
      locale: 'en',
      images: [
        {
          url: `https://www.aimfast.dev/og/trends/${slug}.png`,
          width: 1200,
          height: 630,
          alt: `${term.canonical} — Trend Report | AimFast.Dev`,
        },
      ],
    },
    twitter: {
      card: 'summary_large_image',
      title,
      description,
      images: [`https://www.aimfast.dev/og/trends/${slug}.png`],
    },
  };
}

/* ── Page ── */

export default async function TrendDetailPage({
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

  const researchMd = getResearchContentEn(term.research_md_path);

  // Strip YAML frontmatter, extract sections for FAQ generation
  let researchHtml = '';
  let faqItems: { q: string; a: string }[] = [];
  if (researchMd) {
    const bodyOnly = researchMd.replace(/^---[\s\S]*?---\n*/, '').trim();
    researchHtml = await marked.parse(bodyOnly);
    // Sanitize: strip dangerous tags/attrs from LLM-generated markdown
    researchHtml = sanitizeTrendHtml(researchHtml);

    // Extract h2 sections for FAQ (GEO optimization)
    const h2Matches = bodyOnly.matchAll(/^## (.+)$/gm);
    const sections: string[] = [];
    for (const m of h2Matches) {
      sections.push(m[1].trim());
    }

    // Use shared utility to extract plain text from markdown sections for FAQ

    // Generate FAQ from research report sections
    if (sections.length > 0) {
      // What is X? — use the first matching section or the intro paragraph
      const whatIsSection = sections.find((s) => /what is|overview|introduction/i.test(s));
      const whatIsText = whatIsSection ? extractSectionText(bodyOnly, whatIsSection) : '';
      faqItems.push({
        q: `What is ${term.canonical}?`,
        a: whatIsText || `${term.canonical} is an emerging technology term tracked by AimFast.Dev. ${term.summary_en || ''} First detected on ${term.first_seen} across ${term.source_count} independent sources.`,
      });

      // Why now? — use market context, trend analysis, or signal sections
      const whyNowSection = sections.find((s) => /why now|market context|trend analysis|signal/i.test(s));
      const whyNowText = whyNowSection ? extractSectionText(bodyOnly, whyNowSection) : '';
      faqItems.push({
        q: `Why is ${term.canonical} trending now?`,
        a: whyNowText || `The term "${term.canonical}" has been spotted across ${term.source_count} sources (${term.sources.slice(0, 4).join(', ')}${term.sources.length > 4 ? ' and more' : ''}) with ${term.total_mentions} total mentions and ${term.growth_pct}% growth.`,
      });

      // Who should care? — use target audience, opportunity, or who sections
      const whoSection = sections.find((s) => /who|target audience|opportunity|build/i.test(s));
      const whoText = whoSection ? extractSectionText(bodyOnly, whoSection) : '';
      faqItems.push({
        q: `Who should pay attention to ${term.canonical}?`,
        a: whoText || `Independent developers, indie hackers, and product builders tracking emerging tech trends. This term falls under the "${term.category}" category and is currently in the ${term.stage} stage.`,
      });
    }
  }

  // ===== JSON-LD =====

  const jsonLd = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: 'Trend Discovery', item: 'https://www.aimfast.dev/' },
          { '@type': 'ListItem', position: 2, name: term.canonical, item: `https://www.aimfast.dev/trends/${slug}/` },
        ],
      },
      {
        '@type': 'Article',
        headline: `${term.canonical} — Trend Report`,
        description: term.summary_en,
        url: `https://www.aimfast.dev/trends/${slug}/`,
        datePublished: `${term.first_seen}T00:00:00+08:00`,
        dateModified: `${term.last_seen}T00:00:00+08:00`,
        author: { '@type': 'Organization', name: 'AimFast.Dev' },
        inLanguage: 'en',
        workTranslation: { '@type': 'CreativeWork', '@id': `https://www.aimfast.dev/trends/${slug}/zh/`, inLanguage: 'zh-CN' },
        mainEntityOfPage: {
          '@type': 'WebPage',
          '@id': `https://www.aimfast.dev/trends/${slug}/`,
        },
        about: {
          '@type': 'DefinedTerm',
          name: term.canonical,
          description: term.summary_en,
          inDefinedTermSet: 'https://www.aimfast.dev/trends/',
        },
      },
      ...(faqItems.length > 0
        ? [
            {
              '@type': 'FAQPage',
              mainEntity: faqItems.map((f) => ({
                '@type': 'Question',
                name: f.q,
                acceptedAnswer: {
                  '@type': 'Answer',
                  text: f.a,
                },
              })),
            },
          ]
        : []),
    ],
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <main className="trend-detail">
        {/* ── Breadcrumb + Language Switcher ── */}
        <div className="trend-detail-topbar">
          <a href="/" className="trend-breadcrumb">
            ← Back to all trends
          </a>
          <a href={`/trends/${slug}/zh/`} className="lang-switch">
            <Globe size={13} />
            中文
          </a>
        </div>

        {/* ── Header ── */}
        <div className="trend-detail-header">
          <span className={`stage-badge ${term.stage}`}>
            {stageLabel(term.stage)}
          </span>
          <h1 style={{ overflowWrap: 'break-word' }}>{term.canonical}</h1>

          <div className="trend-detail-sources">
            {term.sources.map((s) => (
              <span key={s} className="trend-source-badge">
                {s}
              </span>
            ))}
          </div>

          <div className="trend-detail-meta-row">
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
              <span
                className="score-tooltip"
                title="Score = Signal Avg × 0.3 + Sources × 8 (max 30) + Engagement × 0.5 (max 20) + Cross-Platform × 10 (max 20)"
              >?</span>
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
          {/* ── Main Content ── */}
          <div className="trend-detail-content">
            {researchHtml ? (
              <div
                className="report-content"
                dangerouslySetInnerHTML={{ __html: researchHtml }}
              />
            ) : (
              <p style={{ color: 'var(--color-text-muted)' }}>
                Research report not yet generated. Check back soon — our AI
                generates deep-dive reports for high-scoring trends daily.
              </p>
            )}

            {/* ── Opportunity Analysis (v2) ── */}
            {term.opportunity_score != null && (
              <section className="opportunity-section">
                <div className="opp-header">
                  <h2>Opportunity Analysis</h2>
                  <div className="opp-overall">
                    <span className="opp-overall-score" style={{ color: scoreColor(term.opportunity_score) }}>
                      {term.opportunity_score}
                    </span>
                    <span className="opp-overall-label">/100 · Opportunity Score</span>
                    {term.revenue_potential != null && (
                      <span className="opp-stars">
                        {'★'.repeat(term.revenue_potential)}
                        {'☆'.repeat(5 - term.revenue_potential)}
                      </span>
                    )}
                  </div>
                </div>

                {/* Score Grid */}
                <div className="opp-score-grid">
                  {term.market_score != null && (
                    <div className="opp-score-card">
                      <div className="score-value" style={{ color: scoreColor(term.market_score) }}>
                        {term.market_score}
                      </div>
                      <div className="score-label">Market</div>
                      <div className="score-bar">
                        <div className="score-bar-fill" style={{ width: `${term.market_score}%`, background: scoreColor(term.market_score) }} />
                      </div>
                    </div>
                  )}
                  {term.competition_score != null && (
                    <div className="opp-score-card">
                      <div className="score-value" style={{ color: invertScoreColor(term.competition_score) }}>
                        {term.competition_score}
                      </div>
                      <div className="score-label">Competition</div>
                      <div className="score-sub">Lower = better</div>
                      <div className="score-bar">
                        <div className="score-bar-fill" style={{ width: `${term.competition_score}%`, background: invertScoreColor(term.competition_score) }} />
                      </div>
                    </div>
                  )}
                  {term.demand_score != null && (
                    <div className="opp-score-card">
                      <div className="score-value" style={{ color: scoreColor(term.demand_score) }}>
                        {term.demand_score}
                      </div>
                      <div className="score-label">Demand</div>
                      <div className="score-bar">
                        <div className="score-bar-fill" style={{ width: `${term.demand_score}%`, background: scoreColor(term.demand_score) }} />
                      </div>
                    </div>
                  )}
                  {term.seo_difficulty != null && (
                    <div className="opp-score-card">
                      <div className="score-value" style={{ color: invertScoreColor(term.seo_difficulty) }}>
                        {term.seo_difficulty}
                      </div>
                      <div className="score-label">SEO Difficulty</div>
                      <div className="score-sub">Lower = easier</div>
                      <div className="score-bar">
                        <div className="score-bar-fill" style={{ width: `${term.seo_difficulty}%`, background: invertScoreColor(term.seo_difficulty) }} />
                      </div>
                    </div>
                  )}
                </div>

                {/* Suggested Products */}
                {term.suggested_products && term.suggested_products.length > 0 && (
                  <div className="opp-products">
                    <span className="opp-products-label">Suggested Products:</span>
                    {term.suggested_products.map((p) => (
                      <span key={p} className="opp-product-badge">{p}</span>
                    ))}
                  </div>
                )}

                {/* Meta: Dev time + Revenue */}
                <div className="opp-meta-row">
                  {term.estimated_dev_days != null && (
                    <span className="opp-meta-item">
                      MVP in ~{term.estimated_dev_days} days
                    </span>
                  )}
                </div>

                {/* Opportunity Summary */}
                {term.opportunity_summary_en && (
                  <p className="opp-summary">{term.opportunity_summary_en}</p>
                )}

                {/* Risk Factors */}
                {term.risk_factors_en && term.risk_factors_en.length > 0 && (
                  <div className="opp-risks">
                    <span className="opp-risks-label">Risks:</span>
                    {term.risk_factors_en.map((r) => (
                      <span key={r} className="opp-risk-badge">{r}</span>
                    ))}
                  </div>
                )}

                {/* CTA */}
                <div className="opp-cta">
                  <p>Want daily opportunity scores like this for every emerging trend?</p>
                  <a href="/" className="btn btn-primary" style={{ fontSize: '0.92rem', padding: '12px 24px' }}>
                    Start Free Trial →
                  </a>
                </div>
              </section>
            )}

            {/* ── FAQ Section (GEO) ── */}
            {faqItems.length > 0 && (
              <section className="trend-faq" style={{ marginTop: 'var(--space-6)' }}>
                <h2>Frequently Asked Questions</h2>
                {faqItems.map((f, i) => (
                  <details key={i} className="faq-item" open={i === 0}>
                    <summary>{f.q}</summary>
                    <div className="faq-answer">
                      <p>{f.a}</p>
                    </div>
                  </details>
                ))}
              </section>
            )}
          </div>

          {/* ── Sidebar ── */}
          <aside className="trend-sidebar">
            <div className="trend-sidebar-card">
              <h4>About This Trend</h4>
              <p>{term.summary_en || ''}</p>
              <div
                style={{
                  fontSize: '0.82rem',
                  color: 'var(--color-text-secondary)',
                  lineHeight: '1.8',
                }}
              >
                <div>
                  <strong>Category:</strong> {term.category}
                </div>
                <div>
                  <strong>Age:</strong> {stageLabel(term.stage)}
                </div>
                <div>
                  <strong>Tags:</strong>{' '}
                  {term.tags.map((t) => (
                    <span
                      key={t}
                      style={{ color: 'var(--color-accent)', marginRight: '6px' }}
                    >
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
              <a
                href="/"
                className="btn btn-primary"
                style={{
                  width: '100%',
                  justifyContent: 'center',
                  fontSize: '0.88rem',
                  padding: '12px 20px',
                }}
              >
                Start Free Trial
                <ArrowUpRight size={14} />
              </a>
            </div>
          </aside>
        </div>

        {/* ── Bottom CTA ── */}
        <section className="trends-cta">
          <h2>Don&apos;t just track trends — act on them</h2>
          <p>
            Every morning, get one actionable product opportunity with
            evidence, pricing strategy, and validation path. 14-day free
            trial.
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
            <a href="/">Trends</a>
            <span className="footer-sep">|</span>
            <a href="/dashboard/">Dashboard</a>
            <span className="footer-sep">|</span>
            <a href="/pricing/">Pricing</a>
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
