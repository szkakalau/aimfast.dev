import type { Metadata } from 'next';
import { TrendingUp, Calendar, BarChart3, Activity, Globe } from 'lucide-react';
import { getAllTrendTerms, stageLabelZh } from '../data';

export const metadata: Metadata = {
  title: '趋势发现 — 新兴技术术语与概念 | AimFast.Dev',
  description:
    '在新兴技术术语和概念流行之前，先人一步发现它们。每日免费追踪 11+ 信源的新兴科技趋势。',
  robots: { index: true, follow: true },
  alternates: {
    canonical: 'https://www.aimfast.dev/trends/zh/',
    languages: {
      'zh-CN': 'https://www.aimfast.dev/trends/zh/',
      en: 'https://www.aimfast.dev/trends/',
    },
  },
  openGraph: {
    title: '趋势发现 — 新兴技术术语 | AimFast.Dev',
    description:
      '在新兴技术术语流行之前发现它们。每日更新，来自 11+ 信源。免费，无需注册。',
    url: 'https://www.aimfast.dev/trends/zh/',
    siteName: 'AimFast.Dev',
    images: [
      {
        url: 'https://www.aimfast.dev/og-image.png',
        width: 1200,
        height: 630,
        alt: 'AimFast.Dev — 趋势发现',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: '趋势发现 — 新兴技术术语 | AimFast.Dev',
    description: '在新兴技术术语流行之前发现它们。免费每日追踪。',
    images: ['https://www.aimfast.dev/og-image.png'],
  },
};

/* ── Page ── */

export default function TrendsZhPage() {
  const data = getAllTrendTerms();
  const { terms, updated_at } = data;
  const totalSources = [...new Set(terms.flatMap((t) => t.sources))].length;

  const jsonLd = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'CollectionPage',
        name: '趋势发现 — AimFast.Dev',
        description:
          '在新兴技术术语、概念和市场信号流行之前发现它们。',
        url: 'https://www.aimfast.dev/trends/zh/',
        inLanguage: 'zh-CN',
        mainEntity: {
          '@type': 'ItemList',
          itemListElement: terms.map((t, i) => ({
            '@type': 'ListItem',
            position: i + 1,
            url: `https://www.aimfast.dev/trends/${t.id.replace('trend-', '')}/zh/`,
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
            在新兴趋势爆发前
            <br />
            先人一步发现它们
          </h1>
          <p className="trends-hero-desc">
            每日追踪 {totalSources}+ 信源中的新技术术语、概念和市场信号。
            免费，无需注册。
          </p>
          <div className="trends-hero-stats">
            <TrendingUp size={14} />
            正在追踪 <strong>{terms.length} 个术语</strong>
            {' · '}每日更新 08:30 CST
          </div>
          <div className="trends-lang-bar">
            <Globe size={13} />
            <span>中文</span>
            <span className="lang-sep">·</span>
            <a href="/trends/">English</a>
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
                  {s === 'all' ? '全部' : stageLabelZh(s)}
                </a>
              ),
            )}
          </div>
        )}

        {/* ── Trend Grid ── */}
        {terms.length === 0 ? (
          <div className="trends-empty">
            <h2>暂无趋势</h2>
            <p>
              每日 pipeline 运行后即可查看。每天早晨新增术语。
            </p>
          </div>
        ) : (
          <div className="trend-grid" id="trend-grid">
            {terms.map((term) => {
              const slug = term.id.replace('trend-', '');
              return (
                <a
                  key={term.id}
                  href={`/trends/${slug}/zh/`}
                  className="trend-card"
                >
                  <span className={`stage-badge ${term.stage}`}>
                    {stageLabelZh(term.stage)}
                  </span>
                  {term.revenue_potential != null && (
                    <span className="trend-card-stars" title={`收入潜力: ${term.revenue_potential}/5`}>
                      {'★'.repeat(term.revenue_potential)}{'☆'.repeat(5 - term.revenue_potential)}
                    </span>
                  )}
                  <span className="trend-card-category">{term.category}</span>
                  <h3>{term.canonical}</h3>
                  <p className="trend-card-summary">
                    {term.summary_zh || term.summary_en}
                  </p>
                  <div className="trend-card-meta">
                    <span className="trend-card-meta-item">
                      <Calendar size={12} />
                      {term.first_seen}
                    </span>
                    <span className="trend-card-meta-item">
                      <Activity size={12} />
                      {term.source_count} 个信源
                    </span>
                    <span className="trend-card-meta-item">
                      <BarChart3 size={12} />
                      {term.total_mentions} 次提及
                    </span>
                  </div>
                </a>
              );
            })}
          </div>
        )}

        {/* ── CTA ── */}
        <section className="trends-cta">
          <h2>想看完整情报？</h2>
          <p>
            每天早上，我们的 Discovery Engine 扫描 {totalSources}+ 信源，
            将这样的信号浓缩成一个可执行的决策——附带定价、验证和竞品分析。
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
            <a href="/">首页</a>
            <span className="footer-sep">|</span>
            <a href="/dashboard/">Dashboard</a>
            <span className="footer-sep">|</span>
            <a href="/reports/">Reports</a>
          </div>
          <div className="footer-copy">
            AimFast.Dev — 更新于{' '}
            {updated_at ? updated_at.slice(0, 10) : '每日'} · 免费趋势发现
          </div>
        </footer>
      </main>
    </>
  );
}
