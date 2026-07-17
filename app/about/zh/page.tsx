import type { Metadata } from 'next';
import { TrendingUp, BarChart3, Zap, Globe } from 'lucide-react';

export const metadata: Metadata = {
  title: '关于 — AimFast.Dev',
  description:
    'AimFast.Dev 是一个自动化趋势发现平台，每夜扫描 21+ 数据源。了解我们的方法论、Pipeline 和团队。',
  robots: { index: true, follow: true },
  alternates: {
    canonical: 'https://www.aimfast.dev/about/zh/',
  },
  openGraph: {
    title: '关于 — AimFast.Dev',
    description: '了解 AimFast.Dev 的方法论和 Pipeline——面向独立开发者的自动化趋势发现。',
    url: 'https://www.aimfast.dev/about/zh/',
    siteName: 'AimFast.Dev',
    locale: 'zh-CN',
    images: [
      {
        url: 'https://www.aimfast.dev/og-home.png',
        width: 1200,
        height: 630,
        alt: 'AimFast.Dev — 关于',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: '关于 — AimFast.Dev',
    description: '面向独立开发者的自动化趋势发现。了解我们的方法论。',
    images: ['https://www.aimfast.dev/og-home.png'],
  },
};

export default function AboutZhPage() {
  const jsonLd = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: '首页', item: 'https://www.aimfast.dev/zh/' },
          { '@type': 'ListItem', position: 2, name: '关于', item: 'https://www.aimfast.dev/about/zh/' },
        ],
      },
      {
        '@type': 'AboutPage',
        name: '关于 AimFast.Dev',
        description:
          'AimFast.Dev 是一个自动化趋势发现平台，每夜通过 LLM Pipeline 扫描 21+ 数据源，追踪 170+ 新兴技术术语，使用专有的 Builder Score 和阶段分类。',
        url: 'https://www.aimfast.dev/about/zh/',
        about: {
          '@type': 'Organization',
          name: 'AimFast.Dev',
          url: 'https://www.aimfast.dev/zh/',
          description:
            '面向独立开发者的每日市场情报。AI 扫描 21+ 数据源，每天早上交付一个经过验证的产品机会。',
          foundingDate: '2026-01-01',
          sameAs: [
            'https://github.com/szkakalau/aimfast.dev',
            'https://twitter.com/aimfastdev',
          ],
          contactPoint: {
            '@type': 'ContactPoint',
            contactType: 'customer support',
            email: 'support@aimfast.dev',
            url: 'https://www.aimfast.dev/about/zh/',
          },
        },
      },
    ],
  };

  return (
    <main>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* ═══════ Hero ═══════ */}
      <section style={{ padding: 'var(--space-10) 0 var(--space-6)', textAlign: 'center' }}>
        <h1 style={{ fontWeight: 700, margin: '0 0 var(--space-3)' }}>
          每天早上，一个决策
        </h1>
        <p style={{ fontSize: '1.125rem', color: 'var(--color-text-secondary)', maxWidth: '600px', margin: '0 auto', lineHeight: 1.6, overflowWrap: 'break-word' }}>
          AimFast.Dev 是一个自动化趋势发现平台。
          每天夜里，我们的 Pipeline 扫描 21+ 全球数据源，对新兴技术术语进行评分，
          并在早上生成一个可行动的产品机会。
        </p>
      </section>

      {/* ═══════ 我们的工作 ═══════ */}
      <section style={{ padding: 'var(--space-8) 0', maxWidth: '720px', margin: '0 auto' }}>
        <div className="section-header">
          <h2>我们的工作</h2>
        </div>

        <div style={{ display: 'grid', gap: 'var(--space-5)' }}>
          <div style={{
            display: 'flex', gap: 'var(--space-4)', alignItems: 'flex-start',
            padding: 'var(--space-5)', border: '1px solid var(--color-border)', borderRadius: '10px',
          }}>
            <Globe size={24} style={{ flexShrink: 0, color: 'var(--color-accent, #2563eb)', marginTop: '2px' }} />
            <div>
              <h3 style={{ margin: '0 0 var(--space-1)', fontSize: '1.05rem' }}>信号采集</h3>
              <p style={{ color: 'var(--color-text-secondary)', margin: 0, lineHeight: 1.6 }}>
                19 个独立采集器每夜并行运行，从开发者平台（Hacker News、GitHub、DEV、Lobsters）、社交媒体（X/Twitter、Reddit、YouTube）、
                包注册表（npm、PyPI）、AI/ML 中心（HuggingFace、ArXiv）以及消费平台
                （豆瓣、小红书、Product Hunt）拉取数据。单个采集源的失败不会阻塞其他采集源。
              </p>
            </div>
          </div>

          <div style={{
            display: 'flex', gap: 'var(--space-4)', alignItems: 'flex-start',
            padding: 'var(--space-5)', border: '1px solid var(--color-border)', borderRadius: '10px',
          }}>
            <BarChart3 size={24} style={{ flexShrink: 0, color: 'var(--color-accent, #2563eb)', marginTop: '2px' }} />
            <div>
              <h3 style={{ margin: '0 0 var(--space-1)', fontSize: '1.05rem' }}>信号处理与评分</h3>
              <p style={{ color: 'var(--color-text-secondary)', margin: 0, lineHeight: 1.6 }}>
                原始信号经过去重、聚类，并使用我们的 E-P-A 框架（证据 × 通俗易懂 × 可行动）进行评分。
                跨平台检测会标记出现在 ≥2 个独立来源的信号。C 端（消费者）机会被自动检测，
                确保我们不会遗漏纯开发者工具视角所忽略的机会。
              </p>
            </div>
          </div>

          <div style={{
            display: 'flex', gap: 'var(--space-4)', alignItems: 'flex-start',
            padding: 'var(--space-5)', border: '1px solid var(--color-border)', borderRadius: '10px',
          }}>
            <TrendingUp size={24} style={{ flexShrink: 0, color: 'var(--color-accent, #2563eb)', marginTop: '2px' }} />
            <div>
              <h3 style={{ margin: '0 0 var(--space-1)', fontSize: '1.05rem' }}>趋势术语 Pipeline</h3>
              <p style={{ color: 'var(--color-text-secondary)', margin: 0, lineHeight: 1.6 }}>
                术语被提取、规范化、按成熟度阶段分类（Nascent → Emergent → Validating → Rising），
                并使用 Builder Score 进行评分——一个衡量来源多样性、增长速度、权威性、提及量和新鲜度的五因子加权综合评分。
                只有在多个独立来源中得到验证的术语才会出现在 Dashboard 上。
              </p>
            </div>
          </div>

          <div style={{
            display: 'flex', gap: 'var(--space-4)', alignItems: 'flex-start',
            padding: 'var(--space-5)', border: '1px solid var(--color-border)', borderRadius: '10px',
          }}>
            <Zap size={24} style={{ flexShrink: 0, color: 'var(--color-accent, #2563eb)', marginTop: '2px' }} />
            <div>
              <h3 style={{ margin: '0 0 var(--space-1)', fontSize: '1.05rem' }}>每日报告生成</h3>
              <p style={{ color: 'var(--color-text-secondary)', margin: 0, lineHeight: 1.6 }}>
                一个 LLM（DeepSeek）生成结构化的每日报告——不是模板，而是上下文感知的分析，
                遵循严格的规则：每项判断需要证据，每个产品推荐需指定目标用户画像，
                每个机会都包含具体的定价建议。第二个 LLM 通道提取结构化决策数据供 Dashboard 使用。
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════ 方法论 ═══════ */}
      <section style={{ padding: 'var(--space-8) 0', maxWidth: '720px', margin: '0 auto' }}>
        <div className="section-header">
          <h2>方法论</h2>
        </div>

        <p style={{ color: 'var(--color-text-secondary)', lineHeight: 1.7, marginBottom: 'var(--space-4)' }}>
          AimFast.Dev 背后的核心洞察很简单：一个出现在 3 个不相关社区中的术语，
          远比一个在单一回音室中有 500 次提及的术语更具信号价值。
        </p>

        <p style={{ color: 'var(--color-text-secondary)', lineHeight: 1.7, marginBottom: 'var(--space-4)' }}>
          我们的 Builder Score 公式将 <strong>来源数量 ×15</strong> 置于所有其他因素之上，
          体现了这种交叉验证原则。增长速度（×12）捕捉动量方向。
          新鲜度衰减（×10）确保 Dashboard 展示的是现在发生的事情，而不是上个月的。
        </p>

        <p style={{ color: 'var(--color-text-secondary)', lineHeight: 1.7, marginBottom: 'var(--space-4)' }}>
          每个信号必须通过最低门槛：出现在 ≥2 个独立来源中，经受去重（85% 标题相似度阈值），
          并通过 E-P-A 评分体系。连续 7 天无法产生独特洞察的信号会被标记为待审查——而不是被无声地丢弃。
        </p>

        <p style={{ color: 'var(--color-text-secondary)', lineHeight: 1.7 }}>
          完整的技术参考——包括具体的评分公式、Pipeline 架构和 LLM prompt 方法论——请参阅{' '}
          <a href="/llms-full.txt">llms-full.txt</a>（2,656 词，AI 可读格式）。
        </p>
      </section>

      {/* ═══════ 透明度 ═══════ */}
      <section style={{ padding: 'var(--space-8) 0', maxWidth: '720px', margin: '0 auto' }}>
        <div className="section-header">
          <h2>透明度</h2>
        </div>

        <p style={{ color: 'var(--color-text-secondary)', lineHeight: 1.7, marginBottom: 'var(--space-4)' }}>
          所有趋势数据以静态 JSON 形式发布。Pipeline 是开源的。
          我们相信，建立对 AI 生成的市场情报的信任的最佳方式，是让原始数据和方法论完全可查。
        </p>

        <ul style={{ color: 'var(--color-text-secondary)', lineHeight: 1.8, paddingLeft: 'var(--space-4)' }}>
          <li>
            <a href="https://github.com/szkakalau/aimfast.dev">GitHub 源代码</a> — 完整的 Pipeline
          </li>
          <li>
            <a href="/dashboard/data/dashboard.json">Dashboard JSON</a> — 每日包含信号、报告和决策的数据包
          </li>
          <li>
            <a href="/llms-full.txt">llms-full.txt</a> — 完整的 AI 可读方法论文档
          </li>
          <li>
            <a href="/llms.txt">llms.txt</a> — 简洁的 AI 站点索引
          </li>
          <li>
            <a href="/sitemap.xml">Sitemap</a> — 所有已索引页面
          </li>
        </ul>
      </section>

      {/* ═══════ 联系我们 ═══════ */}
      <section style={{ padding: 'var(--space-8) 0 var(--space-10)', maxWidth: '720px', margin: '0 auto' }}>
        <div className="section-header">
          <h2>联系我们</h2>
        </div>

        <p style={{ color: 'var(--color-text-secondary)', lineHeight: 1.7 }}>
          如有问题、反馈或合作意向：{' '}
          <a href="mailto:support@aimfast.dev">support@aimfast.dev</a>
        </p>

        <div style={{ display: 'flex', gap: 'var(--space-4)', marginTop: 'var(--space-3)' }}>
          <a href="https://github.com/szkakalau/aimfast.dev" target="_blank" rel="noopener noreferrer">
            GitHub →
          </a>
          <a href="https://twitter.com/aimfastdev" target="_blank" rel="noopener noreferrer">
            X/Twitter →
          </a>
        </div>
      </section>

      {/* ═══════ Footer ═══════ */}
      <footer className="site-footer">
        <div className="footer-links">
          <a href="/zh/">趋势</a>
          <span className="footer-sep">|</span>
          <a href="/dashboard/">Dashboard</a>
          <span className="footer-sep">|</span>
          <a href="/reports/">报告</a>
          <span className="footer-sep">|</span>
          <a href="/pricing/zh/">定价</a>
        </div>
        <div className="footer-copy">
          AimFast.Dev — 面向独立开发者的每日市场情报
        </div>
      </footer>
    </main>
  );
}
