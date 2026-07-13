import type { Metadata } from 'next';
import { TrendingUp, Calendar, BarChart3, Activity, Globe, Zap, Search, Shield } from 'lucide-react';
// Trends data module is the single source of truth for types + stage labels.
import { getAllTrendTerms, getTrendStats, stageLabelZh } from '../trends/data';

export const metadata: Metadata = {
  title: '趋势发现 — 新兴技术术语与市场信号 | AimFast.Dev',
  description:
    '比别人更早发现新兴技术术语、概念和市场信号。每日免费追踪 11+ 个信号源。无需注册。',
  robots: { index: true, follow: true },
  alternates: {
    canonical: 'https://www.aimfast.dev/zh/',
    languages: {
      en: 'https://www.aimfast.dev/',
      'zh-CN': 'https://www.aimfast.dev/zh/',
    },
  },
  openGraph: {
    title: '趋势发现 — 新兴技术术语 | AimFast.Dev',
    description:
      '比别人更早追踪新兴技术术语。每日更新，覆盖 11+ 信号源。免费，无需注册。',
    url: 'https://www.aimfast.dev/zh/',
    siteName: 'AimFast.Dev',
    locale: 'zh-CN',
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
    description:
      '比别人更早发现新兴技术术语。每日免费追踪。',
    images: ['https://www.aimfast.dev/og-image.png'],
  },
};

/* ── Page ── */

export default function ZhHomePage() {
  const data = getAllTrendTerms();
  const { terms, updated_at } = data;
  const stats = getTrendStats();

  const jsonLd = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'CollectionPage',
        name: '趋势发现 — AimFast.Dev',
        description:
          '比别人更早发现新兴技术术语、概念和市场信号。',
        url: 'https://www.aimfast.dev/zh/',
        inLanguage: 'zh-CN',
        mainEntity: {
          '@type': 'ItemList',
          itemListElement: terms.map((t, i) => ({
            '@type': 'ListItem',
            position: i + 1,
            url: `https://www.aimfast.dev/trends/${t.id.replace('trend-', '')}/zh/`,
            name: t.canonical_zh || t.canonical,
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
            比别人更早
            <br />
            发现正在崛起的机会
          </h1>
          <p className="trends-hero-desc">
            每日追踪新兴技术术语、概念和市场信号，
            覆盖 {stats.totalSources}+ 个信号源。免费，无需注册。
          </p>
          <div className="trends-hero-stats">
            <TrendingUp size={14} />
            正在追踪 <strong>{terms.length} 个术语</strong>
            {' · '}每日 08:30 CST 更新
          </div>
        </section>

        {/* ── Live Stats Bar ── */}
        {stats.total > 0 && (
          <div className="live-stats" aria-label="趋势追踪统计">
            <span className="live-stat">
              <TrendingUp size={16} aria-hidden="true" />
              <span className="live-stat-value">{stats.total}</span> 个追踪术语
            </span>
            <span className="live-stat-sep" aria-hidden="true">·</span>
            <span className="live-stat">
              <Zap size={16} aria-hidden="true" />
              <span className="live-stat-value">{stats.withResearch}</span> 份研究报告
            </span>
            <span className="live-stat-sep" aria-hidden="true">·</span>
            <span className="live-stat">
              <Globe size={16} aria-hidden="true" />
              <span className="live-stat-value">{stats.totalSources}</span>+ 信号源
            </span>
            <span className="live-stat-sep" aria-hidden="true">·</span>
            <span className="live-stat">每日 08:30 CST 更新</span>
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
              每日管道运行后更新。每天早上会有新的术语加入。
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
                    <span className="trend-card-stars" title={`商业潜力: ${term.revenue_potential}/5`}>
                      {'★'.repeat(term.revenue_potential)}{'☆'.repeat(5 - term.revenue_potential)}
                    </span>
                  )}
                  <span className="trend-card-category">{term.category}</span>
                  <h3>{term.canonical_zh || term.canonical}</h3>
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
                      {term.source_count} 个来源
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

        {/* ── How It Works (mini) ── */}
        <section className="workflow" style={{ padding: 'var(--space-8) 0' }}>
          <div className="section-header">
            <h2>双引擎系统，一份报告</h2>
            <p>
              每晚，我们的双引擎系统扫描整个互联网。每天早上，你只需做一个决定。
            </p>
          </div>

          <div className="engine-grid">
            <div className="engine-card">
              <Search size={32} className="engine-icon" />
              <h3>挖掘引擎</h3>
              <p>
                AI 扫描 11+ 个来源 — HN、Reddit、GitHub、Product Hunt、X、DEV、
                V2EX 等 — 寻找新兴痛点、上升趋势和市场空白。
              </p>
              <ul className="engine-list">
                <li>跨平台信号交叉验证</li>
                <li>痛点 vs 噪音识别</li>
                <li>可操作性评分</li>
              </ul>
            </div>

            <div className="engine-card">
              <Shield size={32} className="engine-icon" />
              <h3>监控引擎</h3>
              <p>
                追踪最多 10 个竞争对手、话题、人物或技术栈。
                每天 AI 告诉你他们做了什么，以及最重要的 —
                你<em>应该</em>做什么。
              </p>
              <ul className="engine-list">
                <li>竞争对手定价和功能变化</li>
                <li>话题趋势追踪</li>
                <li>可执行的提醒，而非噪音</li>
              </ul>
            </div>
          </div>

          <div className="engine-arrow" aria-hidden="true">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 5v14M5 12l7 7 7-7" />
            </svg>
          </div>

          <div className="engine-output">
            <span className="engine-output-label">每日报告</span>
            一张决策卡片 · 竞争对手动态 · 系统脉搏 · 2 分钟读完
          </div>
        </section>

        {/* ── CTA ── */}
        <section className="trends-cta">
          <h2>想看完整情报？</h2>
          <p>
            每天早上，我们的挖掘引擎扫描 {stats.totalSources}+ 个信号源，
            将类似这样的信号提炼为一条可执行的决策 —
            附带定价、验证和竞争对手上下文。
          </p>
          <a
            href="/dashboard/"
            className="btn btn-primary"
            style={{ fontSize: '1rem', padding: '14px 32px' }}
          >
            查看 Dashboard →
          </a>
        </section>

        {/* ── Footer ── */}
        <footer className="site-footer">
          <div className="footer-links">
            <a href="/">English</a>
            <span className="footer-sep">|</span>
            <a href="/dashboard/">Dashboard</a>
            <span className="footer-sep">|</span>
            <a href="/pricing/zh/">定价</a>
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
