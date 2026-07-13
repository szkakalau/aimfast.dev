import type { Metadata } from 'next';
import { Clock, Eye, TrendingDown } from 'lucide-react';

export const metadata: Metadata = {
  title: '定价 — AimFast.Dev',
  description:
    '一个方案，全部包含。$19/月。面向独立开发者的每日市场情报 — 产品机会、竞争对手追踪、趋势分析。',
  robots: { index: true, follow: true },
  alternates: {
    canonical: 'https://www.aimfast.dev/pricing/zh/',
    languages: {
      en: 'https://www.aimfast.dev/pricing/',
      'zh-CN': 'https://www.aimfast.dev/pricing/zh/',
    },
  },
  openGraph: {
    title: '定价 — AimFast.Dev',
    description: '面向独立开发者的每日市场情报。$19/月，14 天免费试用。',
    url: 'https://www.aimfast.dev/pricing/zh/',
    siteName: 'AimFast.Dev',
    locale: 'zh-CN',
    images: [
      {
        url: 'https://www.aimfast.dev/og-image.png',
        width: 1200,
        height: 630,
        alt: 'AimFast.Dev — 定价',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: '定价 — AimFast.Dev',
    description: '面向独立开发者的每日市场情报。$19/月。',
    images: ['https://www.aimfast.dev/og-image.png'],
  },
};

const FAQ_ITEMS = [
  {
    q: '这和设置 Google Alerts 有什么区别？',
    a: 'Google Alerts 给你链接，我们给你决策。我们的 AI 阅读 300+ 信号，覆盖 11 个平台，交叉验证、评分，然后告诉你"做这个，跳过那个"。Google Alerts 无法告诉你一个 Reddit 抱怨和一个 GitHub star 暴涨其实是同一个未被满足的需求。',
  },
  {
    q: '你们扫描哪些来源？',
    a: 'HN、Reddit（r/programming、r/MachineLearning、r/SideProject、r/Entrepreneur、r/digitalnomad）、GitHub Trending、DEV Community、Lobsters、V2EX、X/Twitter、Product Hunt、HuggingFace、Arxiv、Indie Hackers 等 — 11+ 个来源，每日更新。',
  },
  {
    q: '我可以追踪竞争对手吗？',
    a: '可以 — 这就是监控引擎。添加最多 10 个竞争对手、话题、人物或技术栈。每天你会看到他们做了什么，以及你该做什么。不只是"他们上线了 X"——我们会告诉你"他们的发布揭示了一个你可以填补的空白。"',
  },
  {
    q: '如果我错过了一天怎么办？',
    a: '每份报告都会存档。你可以随时在 Dashboard 中浏览过去的每日决策和完整报告。价值会不断累积 — 规律需要几周而非几天才能浮现。',
  },
  {
    q: '有长期合同吗？',
    a: '没有。随时取消 — 月付或年付均可。取消后，你仍可在当前账单周期结束前使用。没有套路，没有挽留电话。',
  },
];

export default function PricingZhPage() {
  const faqJsonLd = {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: FAQ_ITEMS.map(({ q, a }) => ({
      '@type': 'Question',
      name: q,
      acceptedAnswer: { '@type': 'Answer', text: a },
    })),
  };

  return (
    <main>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }}
      />

      {/* ═══════ Pain Cards — 不知道的代价 ═══════ */}
      <section className="pain-cards" style={{ padding: 'var(--space-8) 0' }}>
        <div className="section-header">
          <h1>不知道的代价</h1>
          <p>
            每天早上没有市场情报，你都可能付出以下三种代价之一。
          </p>
        </div>

        <div className="pain-grid">
          <div className="pain-card">
            <Clock size={32} className="pain-icon" />
            <h3>方向浪费</h3>
            <p>
              你花了 2 周做了一个没人要的功能。如果你 10 天前就知道需求在衰退，
              你会选择做别的。
            </p>
            <div className="pain-solution">
              <span className="pain-arrow">→</span>
              每日决策卡片告诉你该做什么 — 以及该跳过什么
            </div>
          </div>

          <div className="pain-card pain-card-accent">
            <Eye size={32} className="pain-icon" />
            <h3>竞争盲区</h3>
            <p>
              你的竞争对手 3 天前改了定价。他们的免费用户在找替代品。
              你不知道 — 直到现在。
            </p>
            <div className="pain-solution">
              <span className="pain-arrow">→</span>
              监控最多 10 个竞争对手、话题或技术栈
            </div>
          </div>

          <div className="pain-card">
            <TrendingDown size={32} className="pain-icon" />
            <h3>趋势滞后</h3>
            <p>
              一个新的分发渠道正在起飞。早期采用者以几乎零成本获取客户。
              等你听说了，窗口已经关闭了。
            </p>
            <div className="pain-solution">
              <span className="pain-arrow">→</span>
              每日扫描 11+ 来源，捕捉峰值前的信号
            </div>
          </div>
        </div>
      </section>

      {/* ═══════ Pricing ═══════ */}
      <section className="pricing-section" style={{ padding: 'var(--space-8) 0' }}>
        <div className="section-header">
          <h2>简单定价</h2>
          <p>
            一个方案，全部包含。没有按人头收费，没有功能分层。
            你要么获得全部价值，要么取消 — 不必难为情。
          </p>
        </div>

        <div className="pricing-card">
          <div className="pricing-badge">全部功能</div>

          <div className="pricing-amount-row">
            <span className="pricing-dollar">$</span>
            <span className="pricing-number">19</span>
            <span className="pricing-period">/月</span>
          </div>
          <div className="pricing-annual">或 $190/年 — 省 $38</div>

          <ul className="pricing-features">
            <li>✓ 每日验证的产品机会</li>
            <li>✓ 竞争对手和话题追踪（最多 10 个）</li>
            <li>✓ 完整报告存档</li>
            <li>✓ 信号 Dashboard 含系统脉搏</li>
            <li>✓ AI 助手（即将上线）</li>
            <li>✓ 14 天免费试用</li>
          </ul>

          <a
            href="https://tally.so/r/placeholder"
            className="btn btn-primary pricing-cta"
            target="_blank"
            rel="noopener noreferrer"
          >
            开始免费试用 →
          </a>

          <div className="pricing-cancel">随时取消。无需理由。</div>
        </div>
      </section>

      {/* ═══════ FAQ ═══════ */}
      <section className="faq-section" style={{ padding: 'var(--space-8) 0', maxWidth: '640px', margin: '0 auto' }}>
        <div className="section-header">
          <h2>常见问题</h2>
        </div>

        <dl className="faq-list">
          {FAQ_ITEMS.map(({ q, a }) => (
            <div key={q} className="faq-item">
              <dt>{q}</dt>
              <dd>{a}</dd>
            </div>
          ))}
        </dl>
      </section>

      {/* ═══════ Footer CTA ═══════ */}
      <section className="footer-cta" style={{ textAlign: 'center', padding: 'var(--space-8) 0 var(--space-10)' }}>
        <h2>你在构建。他们在旁观。</h2>
        <p style={{ color: 'var(--color-text-secondary)', marginBottom: 'var(--space-3)', fontSize: '1rem' }}>
          开始 14 天免费试用。每天早上一条可执行的情报。
        </p>
        <a
          href="https://tally.so/r/placeholder"
          className="btn btn-primary"
          style={{ fontSize: '1rem', padding: '14px 32px' }}
          target="_blank"
          rel="noopener noreferrer"
        >
          获取早期访问 →
        </a>
      </section>

      {/* ═══════ Footer ═══════ */}
      <footer className="site-footer">
        <div className="footer-links">
          <a href="/">English</a>
          <span className="footer-sep">|</span>
          <a href="/dashboard/">Dashboard</a>
        </div>
        <div className="footer-copy">
          AimFast.Dev — 独立开发者的每日市场情报
        </div>
      </footer>
    </main>
  );
}
