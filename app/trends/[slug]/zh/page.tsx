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

import type { TrendTerm, TrendTermsData } from '../../types';
import {
  getAllTrendTerms,
  getTrendTerm,
  getResearchContent,
  stageLabelZh,
  stagePct,
  sanitizeTrendHtml,
} from '../../data';
import { extractSectionText } from '../../utils';

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
    return { title: '未找到趋势词 — AimFast.Dev' };
  }

  const title = `${term.canonical} — 趋势报告与分析 | AimFast.Dev`;
  const description = term.summary_zh || term.summary_en;
  const url = `https://www.aimfast.dev/trends/${slug}/zh/`;

  return {
    title,
    description,
    robots: { index: true, follow: true },
    alternates: {
      canonical: url,
      languages: {
        en: `https://www.aimfast.dev/trends/${slug}/`,
        'zh-CN': url,
      },
    },
    openGraph: {
      title,
      description,
      url,
      siteName: 'AimFast.Dev',
      type: 'article',
      locale: 'zh-CN',
      images: [
        {
          url: `https://www.aimfast.dev/og/trends/${slug}.png`,
          width: 1200,
          height: 630,
          alt: `${term.canonical} — 趋势报告 | AimFast.Dev`,
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

export default async function TrendDetailZhPage({
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
          <h2>未找到趋势词</h2>
          <p>
            <a href="/trends/">← 返回趋势列表</a>
          </p>
        </div>
      </main>
    );
  }

  const researchMd = getResearchContent(term.research_md_path);

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

    if (sections.length > 0) {
      // What is X? — match Chinese & English section headers
      const whatIsSection = sections.find((s) => /什么是|概述|介绍|what is|overview|introduction/i.test(s));
      const whatIsText = whatIsSection ? extractSectionText(bodyOnly, whatIsSection) : '';
      faqItems.push({
        q: `${term.canonical} 是什么？`,
        a: whatIsText || `${term.canonical} 是 AimFast.Dev 追踪的新兴技术术语。${term.summary_zh || term.summary_en} 首次发现于 ${term.first_seen}，已覆盖 ${term.source_count} 个独立信源。`,
      });

      // Why now? — match Chinese & English section headers
      const whyNowSection = sections.find((s) => /为什么现在|市场背景|趋势分析|信号|why now|market context|trend analysis|signal/i.test(s));
      const whyNowText = whyNowSection ? extractSectionText(bodyOnly, whyNowSection) : '';
      faqItems.push({
        q: `为什么 ${term.canonical} 现在火了？`,
        a: whyNowText || `该词已出现在 ${term.source_count} 个信源中（${term.sources.join('、')}），累计 ${term.total_mentions} 次提及，增长 ${term.growth_pct}%。详见下方完整报告。`,
      });

      // Who should care? — match Chinese & English section headers
      const whoSection = sections.find((s) => /谁|目标用户|机会|开发|who|target audience|opportunity|build/i.test(s));
      const whoText = whoSection ? extractSectionText(bodyOnly, whoSection) : '';
      faqItems.push({
        q: `谁应该关注 ${term.canonical}？`,
        a: whoText || `独立开发者、独立黑客、以及关注新兴技术趋势的产品人。该词属于"${term.category}"类别，目前处于${stageLabelZh(term.stage)}。`,
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
          { '@type': 'ListItem', position: 1, name: '趋势发现', item: 'https://www.aimfast.dev/' },
          { '@type': 'ListItem', position: 2, name: term.canonical, item: `https://www.aimfast.dev/trends/${slug}/zh/` },
        ],
      },
      {
        '@type': 'Article',
        headline: `${term.canonical} — 趋势报告`,
        description: term.summary_zh,
        url: `https://www.aimfast.dev/trends/${slug}/zh/`,
        datePublished: `${term.first_seen}T00:00:00+08:00`,
        dateModified: `${term.last_seen}T00:00:00+08:00`,
        author: { '@type': 'Organization', name: 'AimFast.Dev' },
        inLanguage: 'zh-CN',
        translationOfWork: { '@type': 'CreativeWork', '@id': `https://www.aimfast.dev/trends/${slug}/` },
        mainEntityOfPage: {
          '@type': 'WebPage',
          '@id': `https://www.aimfast.dev/trends/${slug}/zh/`,
        },
        about: {
          '@type': 'DefinedTerm',
          name: term.canonical,
          description: term.summary_zh,
          inDefinedTermSet: 'https://www.aimfast.dev/trends/zh/',
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
            ← 返回趋势列表
          </a>
          <a href={`/trends/${slug}/`} className="lang-switch">
            <Globe size={13} />
            English
          </a>
        </div>

        {/* ── Header ── */}
        <div className="trend-detail-header">
          <span className={`stage-badge ${term.stage}`}>
            {stageLabelZh(term.stage)}
          </span>
          <h1>{term.canonical}</h1>

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
              首次出现 <strong>{term.first_seen}</strong>
            </span>
            <span className="trend-detail-meta-item">
              <Calendar size={14} />
              最近出现 <strong>{term.last_seen}</strong>
            </span>
            <span className="trend-detail-meta-item">
              <BarChart3 size={14} />
              评分 <strong>{term.score}</strong>
              <span
                className="score-tooltip"
                title="评分 = 信号平均分 × 0.3 + 信源数 × 8（上限30）+ 互动热度 × 0.5（上限20）+ 跨平台传播 × 10（上限20）"
              >?</span>
            </span>
            <span className="trend-detail-meta-item">
              <Activity size={14} />
              <strong>{term.source_count}</strong> 个信源
            </span>
            <span className="trend-detail-meta-item">
              <Hash size={14} />
              <strong>{term.total_mentions}</strong> 次提及
            </span>
            <span className="trend-detail-meta-item">
              <TrendingUp size={14} />
              增长 <strong>+{term.growth_pct}%</strong>
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
                研究报告尚未生成。请稍后再来——我们的 AI 每天会为高分趋势词自动生成深度研究报告。
              </p>
            )}

            {/* ── Opportunity Analysis (v2) ── */}
            {term.opportunity_score != null && (
              <section className="opportunity-section">
                <div className="opp-header">
                  <h2>机会分析</h2>
                  <div className="opp-overall">
                    <span className="opp-overall-score" style={{ color: scoreColor(term.opportunity_score) }}>
                      {term.opportunity_score}
                    </span>
                    <span className="opp-overall-label">/100 · 综合机会评分</span>
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
                      <div className="score-label">市场评分</div>
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
                      <div className="score-label">竞争评分</div>
                      <div className="score-sub">越低越好</div>
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
                      <div className="score-label">需求评分</div>
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
                      <div className="score-label">SEO 难度</div>
                      <div className="score-sub">越低越容易</div>
                      <div className="score-bar">
                        <div className="score-bar-fill" style={{ width: `${term.seo_difficulty}%`, background: invertScoreColor(term.seo_difficulty) }} />
                      </div>
                    </div>
                  )}
                </div>

                {/* Suggested Products */}
                {term.suggested_products && term.suggested_products.length > 0 && (
                  <div className="opp-products">
                    <span className="opp-products-label">建议产品形态：</span>
                    {term.suggested_products.map((p) => (
                      <span key={p} className="opp-product-badge">{p}</span>
                    ))}
                  </div>
                )}

                {/* Meta: Dev time */}
                <div className="opp-meta-row">
                  {term.estimated_dev_days != null && (
                    <span className="opp-meta-item">
                      预计 MVP 开发时间：~{term.estimated_dev_days} 天
                    </span>
                  )}
                </div>

                {/* Opportunity Summary */}
                {term.opportunity_summary_zh && (
                  <p className="opp-summary">{term.opportunity_summary_zh}</p>
                )}

                {/* Risk Factors */}
                {term.risk_factors_zh && term.risk_factors_zh.length > 0 && (
                  <div className="opp-risks">
                    <span className="opp-risks-label">风险因素：</span>
                    {term.risk_factors_zh.map((r) => (
                      <span key={r} className="opp-risk-badge">{r}</span>
                    ))}
                  </div>
                )}

                {/* CTA */}
                <div className="opp-cta">
                  <p>想要每个新兴趋势都获得这样的机会分析？</p>
                  <a href="/" className="btn btn-primary" style={{ fontSize: '0.92rem', padding: '10px 24px' }}>
                    免费试用 →
                  </a>
                </div>
              </section>
            )}

            {/* ── FAQ Section (GEO) ── */}
            {faqItems.length > 0 && (
              <section className="trend-faq" style={{ marginTop: 'var(--space-6)' }}>
                <h2>常见问题</h2>
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
              <h4>关于这个趋势</h4>
              <p>{term.summary_zh || term.summary_en}</p>
              <div
                style={{
                  fontSize: '0.82rem',
                  color: 'var(--color-text-secondary)',
                  lineHeight: '1.8',
                }}
              >
                <div>
                  <strong>分类：</strong>{term.category}
                </div>
                <div>
                  <strong>发现天数：</strong>{stagePct(term.stage)} 天
                </div>
                <div>
                  <strong>标签：</strong>
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
              <h4>想看完整情报？</h4>
              <p>
                获取每日竞品情报、产品机会和持续监控——不止是趋势。
              </p>
              <a
                href="/"
                className="btn btn-primary"
                style={{
                  width: '100%',
                  justifyContent: 'center',
                  fontSize: '0.88rem',
                  padding: '10px 20px',
                }}
              >
                免费试用
                <ArrowUpRight size={14} />
              </a>
            </div>
          </aside>
        </div>

        {/* ── Bottom CTA ── */}
        <section className="trends-cta">
          <h2>不只是追踪趋势——抓住机会</h2>
          <p>
            每天早上，你会收到一个可执行的产品机会，附带证据链、定价策略和验证路径。14 天免费试用。
          </p>
          <a
            href="/"
            className="btn btn-primary"
            style={{ fontSize: '1rem', padding: '14px 32px' }}
          >
            免费试用 →
          </a>
        </section>

        {/* ── Footer ── */}
        <footer className="site-footer">
          <div className="footer-links">
            <a href="/">趋势</a>
            <span className="footer-sep">|</span>
            <a href="/dashboard/">Dashboard</a>
            <span className="footer-sep">|</span>
            <a href="/pricing/">定价</a>
            <span className="footer-sep">|</span>
            <a href="/reports/">Reports</a>
          </div>
          <div className="footer-copy">
            AimFast.Dev — 趋势报告每日更新
          </div>
        </footer>
      </main>
    </>
  );
}
