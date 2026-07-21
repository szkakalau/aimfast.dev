import type { Metadata } from 'next';
import { TrendingUp, BarChart3, Globe, Zap, Search, Shield } from 'lucide-react';
// Trends data module is the single source of truth for types + stage labels.
// The homepage IS the trends discovery page — this cross-route import is intentional.
import { getAllTrendTerms, getTrendStats } from '../trends/data';
import TrendFilter from '../trends/TrendFilter';

export const metadata: Metadata = {
  title: '信号而非噪音 — AI 精选技术趋势与市场信号 | AimFast.Dev',
  description:
    'AI 每天扫描 30+ 个信源，交叉验证后按 Builder Score 排序——帮你过滤噪音，聚焦真正值得行动的机会。免费，无需注册。',
  robots: { index: true, follow: true },
  alternates: {
    canonical: 'https://www.aimfast.dev/zh/',
    languages: {
      en: 'https://www.aimfast.dev/',
      'zh-CN': 'https://www.aimfast.dev/zh/',
    },
  },
  openGraph: {
    title: '信号而非噪音 — 技术趋势 | AimFast.Dev',
    description:
      '按 Builder Score 排序的技术术语——不追热点，只看价值。每日免费追踪。',
    url: 'https://www.aimfast.dev/zh/',
    siteName: 'AimFast.Dev',
    locale: 'zh-CN',
    images: [
      {
        url: 'https://www.aimfast.dev/og-home.png',
        width: 1200,
        height: 630,
        alt: 'AimFast.Dev — 趋势发现',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: '信号而非噪音 — 技术趋势 | AimFast.Dev',
    description:
      '信号而非噪音——AI 交叉验证的技术术语，按 Builder Score 排序。每日免费追踪。',
    images: ['https://www.aimfast.dev/og-home.png'],
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
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: '首页', item: 'https://www.aimfast.dev/zh/' },
        ],
      },
      {
        '@type': 'CollectionPage',
        name: '趋势发现 — AimFast.Dev',
        description:
          'AI 每天扫描 30+ 个信源，交叉验证后按 Builder Score 排序——帮你过滤噪音，聚焦真正值得行动的机会。',
        url: 'https://www.aimfast.dev/zh/',
        inLanguage: 'zh-CN',
        dateModified: updated_at || new Date().toISOString().slice(0, 10),
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
      {
        '@type': 'HowTo',
        name: '趋势如何评分与发现',
        description:
          '每个趋势都由管道自动评分和分阶段，覆盖 30+ 个信号源。',
        step: [
          {
            '@type': 'HowToStep',
            position: 1,
            name: '跨信源验证',
            text: '术语必须在 2 个及以上独立信源中出现——孤立的单帖不会被收录。',
          },
          {
            '@type': 'HowToStep',
            position: 2,
            name: '代表性过滤',
            text: '新产品仅在代表某个新兴方向时才保留，一次性发布不会纳入。',
          },
          {
            '@type': 'HowToStep',
            position: 3,
            name: '讨论量门槛',
            text: '低分单帖不达标；必须有真实的社区讨论热度。',
          },
          {
            '@type': 'HowToStep',
            position: 4,
            name: '通用词黑名单',
            text: '已知泛化词汇如 AI、React、Python、API、LLM、GPT 会被自动忽略。',
          },
          {
            '@type': 'HowToStep',
            position: 5,
            name: '质量优先于数量',
            text: '质量优先于数量——只有经过跨源验证的高质量术语才会被收录，不设数量上限。',
          },
        ],
      },
      {
        '@type': 'FAQPage',
        mainEntity: [
          {
            '@type': 'Question',
            name: '趋势是如何发现的？',
            acceptedAnswer: {
              '@type': 'Answer',
              text: `我们的 AI 每天扫描 30+ 个信号源——HN、Reddit、GitHub、DEV Community、Lobsters、V2EX、X/Twitter、Product Hunt、HuggingFace、Arxiv、npm、PyPI、Stack Overflow、YouTube 等——交叉引用新兴术语，并按信号强度、来源多样性和社区互动评分。`,
            },
          },
          {
            '@type': 'Question',
            name: '数据多久更新一次？',
            acceptedAnswer: {
              '@type': 'Answer',
              text: `每天 08:30 CST 更新。每天早晨，新术语被发现，已有术语被重新评分，市场情报报告被重新生成。`,
            },
          },
          {
            '@type': 'Question',
            name: 'AimFast.Dev 是免费的吗？',
            acceptedAnswer: {
              '@type': 'Answer',
              text: `是的——趋势发现和追踪完全免费。付费方案（$19/月起）可解锁每日决策简报、竞品监控和完整管道访问。14 天免费试用，无需信用卡。`,
            },
          },
        ],
      },
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
          <h1>找到值得行动的信号</h1>
          <p className="trends-hero-desc">
            AI 每天扫描 {stats.totalSources}+ 个信源，交叉验证后按 Builder Score 排序
            ——帮你过滤噪音，聚焦真正值得关注的机会。免费，无需注册。
          </p>
          <div className="trends-hero-stats">
            <TrendingUp size={14} aria-hidden="true" />
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

        {/* ── Stage Filter + Trend Grid (client component) ── */}
        <TrendFilter terms={terms} locale="zh" />

        {/* ── Methodology: How Trends Are Ranked & Discovered ── */}
        <section className="methodology-section">
          <div className="section-header">
            <h2>趋势如何评分与发现</h2>
            <p>
              你看到的每个趋势都由管道自动评分和分阶段。以下是具体的工作方式。
            </p>
          </div>

          <div className="engine-grid">
            {/* Card A: Scoring */}
            <div className="engine-card">
              <h3><BarChart3 size={20} /> 评分机制</h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)', marginBottom: 'var(--space-2)' }}>
                每个术语从四个维度获得 0–100 的综合评分：
              </p>
              <div className="score-formula">
                评分 = 四个维度的加权综合：<br />
                &nbsp;&nbsp;• 来源多样性（权重最高）<br />
                &nbsp;&nbsp;• 跨独立来源的信号强度<br />
                &nbsp;&nbsp;• 社区互动活跃度<br />
                &nbsp;&nbsp;• 跨平台传播度
              </div>

              <p style={{ fontSize: '0.82rem', color: 'var(--color-text-secondary)', marginBottom: 'var(--space-2)' }}>
                <strong>成熟度阶段</strong> — 基于首次发现后的时间：
              </p>
              <div className="stage-legend">
                <span className="stage-legend-item">
                  <span className="stage-legend-dot nascent" /> 萌芽期
                </span>
                <span className="stage-legend-item">
                  <span className="stage-legend-dot emergent" /> 涌现期
                </span>
                <span className="stage-legend-item">
                  <span className="stage-legend-dot validating" /> 验证期
                </span>
                <span className="stage-legend-item">
                  <span className="stage-legend-dot rising" /> 上升期
                </span>
              </div>

              <p style={{ fontSize: '0.82rem', color: 'var(--color-text-secondary)', marginTop: 'var(--space-2)' }}>
                <strong>报告阈值：</strong>{' '}
                <span className="threshold-list">
                  <span>高分段</span> 深度研究报告 ·{' '}
                  <span>中分段</span> 快速简报 ·{' '}
                  <span>低分段</span> 仅追踪
                </span>
              </p>
            </div>

            {/* Card B: Discovery */}
            <div className="engine-card">
              <h3><Search size={20} /> 术语发现规则</h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)', marginBottom: 'var(--space-2)' }}>
                每晚，LLM 管道扫描 30+ 个信号源，按 5 条规则提取新兴术语：
              </p>
              <ul>
                <li>
                  <strong>跨信源验证</strong> — 术语必须在 ≥2 个独立信源中出现，孤立的单帖不会被收录。
                </li>
                <li>
                  <strong>代表性过滤</strong> — 新产品仅在代表某个新兴方向时才提取，单次发布的帖子不纳入。
                </li>
                <li>
                  <strong>讨论量门槛</strong> — 低分单帖不达标；必须有真实的社区讨论热度。
                </li>
                <li>
                  <strong>通用词黑名单</strong> — AI、React、Python、API、LLM、GPT 等已知泛化词汇会被自动忽略。
                </li>
                <li>
                  <strong>质量优先于数量</strong> — 只有经过跨源验证的高质量术语才会被收录，不设数量上限。
                </li>
              </ul>
              <p style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)', marginTop: 'var(--space-2)' }}>
                覆盖来源：HN、Reddit、GitHub、Product Hunt、X、DEV Community、V2EX、Lobsters 等。
              </p>
            </div>
          </div>
        </section>

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
                AI 扫描 30+ 个来源 — HN、Reddit、GitHub、Product Hunt、X、DEV、
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
