import type { Metadata } from 'next';
import { Check, Star } from 'lucide-react';

export const metadata: Metadata = {
  title: '定价 — AimFast.Dev',
  description:
    '三档方案，面向独立开发者。Starter $19/月起，趋势发现。Builder $39/月，每日决策 + 竞品监控。Team $79/月，团队共享 + API。',
  robots: { index: true, follow: true },
  alternates: {
    canonical: 'https://www.aimfast.dev/pricing/zh/',
    languages: {
      en: 'https://www.aimfast.dev/pricing/',
      'zh-CN': 'https://www.aimfast.dev/pricing/zh/',
    },
  },
  other: { 'last-modified': '2026-07-16' },
  openGraph: {
    title: '定价 — AimFast.Dev',
    description: '三档方案，面向独立开发者。Starter $19/月、Builder $39/月、Team $79/月。所有方案均含 14 天免费试用。',
    url: 'https://www.aimfast.dev/pricing/zh/',
    siteName: 'AimFast.Dev',
    locale: 'zh-CN',
    images: [
      {
        url: 'https://www.aimfast.dev/og-pricing.png',
        width: 1200,
        height: 630,
        alt: 'AimFast.Dev — 定价',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: '定价 — AimFast.Dev',
    description: '三档方案，面向独立开发者。Starter $19/月、Builder $39/月、Team $79/月。',
    images: ['https://www.aimfast.dev/og-pricing.png'],
  },
};

interface Plan {
  id: string;
  name: string;
  badge?: string;
  monthly: number;
  yearly: number;
  description: string;
  features: string[];
  cta: string;
  highlight?: boolean;
}

const PLANS: Plan[] = [
  {
    id: 'starter',
    name: 'Starter',
    monthly: 19,
    yearly: 190,
    description: '给好奇的 Builder——在趋势爆发前看到它。',
    features: [
      '每日趋势发现（30+ 来源）',
      '浏览所有追踪词条',
      '阶段与分类筛选',
      '基础词条追踪（3 个）',
      '每周邮件简报',
      '14 天免费试用',
    ],
    cta: '开始免费试用',
  },
  {
    id: 'builder',
    name: 'Builder',
    badge: '最受欢迎',
    monthly: 39,
    yearly: 390,
    description: '每天早上一份决策。用情报而非猜测来构建产品。',
    features: [
      'Starter 全部功能',
      '每日验证决策卡片',
      '竞争对手与话题监控（最多 10 个）',
      '完整深度研究报告（Top 25% Builder Score）',
      'AI 评分与跨平台验证',
      '完整报告存档',
      '无限词条追踪',
      '优先邮件支持',
      '14 天免费试用',
    ],
    cta: '开始免费试用',
    highlight: true,
  },
  {
    id: 'team',
    name: 'Team',
    badge: '团队版',
    monthly: 79,
    yearly: 790,
    description: '小团队共享情报。统一方向，减少争论。',
    features: [
      'Builder 全部功能',
      '3 个团队席位',
      '共享监控面板',
      'CSV 导出',
      'API 访问（即将上线）',
      '新功能优先体验',
      '14 天免费试用',
    ],
    cta: '开始免费试用',
  },
];

const FAQ_ITEMS = [
  {
    q: '这和设置 Google Alerts 有什么区别？',
    a: 'Google Alerts 给你链接，我们给你决策。我们的 AI 阅读 300+ 信号，覆盖 30+ 个平台，交叉验证、评分，然后告诉你"做这个，跳过那个"。Google Alerts 无法告诉你一个 Reddit 抱怨和一个 GitHub star 暴涨其实是同一个未被满足的需求。',
  },
  {
    q: '你们扫描哪些来源？',
    a: 'HN、Reddit、GitHub Trending、DEV Community、Lobsters、V2EX、X/Twitter、Product Hunt、HuggingFace、Arxiv、npm、PyPI、Stack Overflow、YouTube、Google News、Google Trends 等 — 30+ 个来源，每日更新。',
  },
  {
    q: '我可以追踪竞争对手吗？',
    a: '可以——Builder 及以上方案包含此功能。添加最多 10 个竞争对手、话题、人物或技术栈。每天你会看到他们做了什么，以及你该做什么。不只是"他们上线了 X"——我们会告诉你"他们的发布揭示了一个你可以填补的空白。"',
  },
  {
    q: '如果我错过了一天怎么办？',
    a: '每份报告都会存档。你可以随时在 Dashboard 中浏览过去的每日决策和完整报告。价值会不断累积——规律需要几周而非几天才能浮现。',
  },
  {
    q: '有长期合同吗？',
    a: '没有。随时取消——月付或年付均可。取消后，你仍可在当前账单周期结束前使用。没有套路，没有挽留电话。',
  },
  {
    q: '可以中途升级或降级吗？',
    a: '可以——随时切换方案。升级立即生效，费用按比例计算。降级在当前账单周期结束后生效。',
  },
];

export default function PricingZhPage() {
  const faqJsonLd = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: '首页', item: 'https://www.aimfast.dev/zh/' },
          { '@type': 'ListItem', position: 2, name: '定价', item: 'https://www.aimfast.dev/pricing/zh/' },
        ],
      },
      {
        '@type': 'FAQPage',
        mainEntity: FAQ_ITEMS.map(({ q, a }) => ({
          '@type': 'Question',
          name: q,
          acceptedAnswer: { '@type': 'Answer', text: a },
        })),
      },
    ],
  };

  return (
    <main className="container">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }}
      />

      {/* ═══════ Hero ═══════ */}
      <section style={{ padding: 'var(--space-10) var(--space-3) var(--space-6)', textAlign: 'center' }}>
        <h1 style={{ fontSize: 'clamp(1.6rem, 6vw, 2.25rem)', fontWeight: 700, margin: '0 0 var(--space-3)' }}>
          每天早上，一份决策
        </h1>
        <p style={{ fontSize: '1.125rem', color: 'var(--color-text-secondary)', maxWidth: '560px', margin: '0 auto', lineHeight: 1.6 }}>
          三档方案，同一个承诺：不再猜测该做什么。
          所有方案均含 14 天免费试用——无需信用卡。
        </p>
      </section>

      {/* ═══════ Pricing Cards ═══════ */}
      <section style={{ padding: '0 var(--space-3) var(--space-8)', maxWidth: '960px', margin: '0 auto' }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
          gap: 'var(--space-5)',
          alignItems: 'start',
        }}>
          {PLANS.map((plan) => (
            <div
              key={plan.id}
              style={{
                position: 'relative',
                border: plan.highlight
                  ? '2px solid var(--color-accent, #2563eb)'
                  : '1px solid var(--color-border, #e5e7eb)',
                borderRadius: '12px',
                padding: 'var(--space-6)',
                background: plan.highlight
                  ? 'var(--color-surface, #fff)'
                  : 'var(--color-bg, #f9fafb)',
                boxShadow: plan.highlight
                  ? '0 4px 24px rgba(37, 99, 235, 0.12)'
                  : 'none',
              }}
            >
              {/* Badge */}
              {plan.badge && (
                <div style={{
                  position: 'absolute',
                  top: '-13px',
                  left: '50%',
                  transform: 'translateX(-50%)',
                  background: plan.highlight ? 'var(--color-accent, #2563eb)' : 'var(--color-text-secondary, #6b7280)',
                  color: '#fff',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  padding: '4px 14px',
                  borderRadius: '999px',
                  whiteSpace: 'nowrap',
                }}>
                  {plan.badge === '最受欢迎' && (
                    <Star size={12} style={{ display: 'inline', marginRight: '4px', verticalAlign: '-1px' }} />
                  )}
                  {plan.badge}
                </div>
              )}

              {/* Plan Name */}
              <h2 style={{
                fontSize: '1.25rem',
                fontWeight: 700,
                margin: plan.badge ? 'var(--space-3) 0 var(--space-1)' : '0 0 var(--space-1)',
              }}>
                {plan.name}
              </h2>

              {/* Description */}
              <p style={{
                fontSize: '0.85rem',
                color: 'var(--color-text-secondary)',
                margin: '0 0 var(--space-4)',
                minHeight: '2.5em',
                lineHeight: 1.4,
              }}>
                {plan.description}
              </p>

              {/* Price */}
              <div style={{ marginBottom: 'var(--space-4)' }}>
                <span style={{ fontSize: 'clamp(1.8rem, 7vw, 2.5rem)', fontWeight: 800, lineHeight: 1 }}>
                  ${plan.monthly}
                </span>
                <span style={{ fontSize: '0.95rem', color: 'var(--color-text-secondary)' }}>
                  /月
                </span>
                <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted, #9ca3af)', marginTop: '2px' }}>
                  或 ${plan.yearly}/年 — 省 ${plan.monthly * 12 - plan.yearly}
                </div>
              </div>

              {/* CTA */}
              <a
                href="https://tally.so/r/placeholder"
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: 'block',
                  textAlign: 'center',
                  padding: '12px 0',
                  borderRadius: '8px',
                  fontWeight: 600,
                  fontSize: '0.95rem',
                  textDecoration: 'none',
                  marginBottom: 'var(--space-5)',
                  transition: 'all 150ms ease-out',
                  background: plan.highlight
                    ? 'var(--color-accent, #2563eb)'
                    : 'var(--color-bg, #f3f4f6)',
                  color: plan.highlight ? '#fff' : 'var(--color-text, #111827)',
                  border: plan.highlight ? 'none' : '1px solid var(--color-border, #d1d5db)',
                }}
              >
                {plan.cta} →
              </a>

              {/* Features */}
              <ul style={{
                listStyle: 'none',
                padding: 0,
                margin: 0,
                fontSize: '0.875rem',
                lineHeight: 1.6,
              }}>
                {plan.features.map((f) => (
                  <li
                    key={f}
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: 'var(--space-2)',
                      marginBottom: 'var(--space-2)',
                    }}
                  >
                    <Check
                      size={16}
                      style={{
                        flexShrink: 0,
                        marginTop: '4px',
                        color: plan.highlight
                          ? 'var(--color-accent, #2563eb)'
                          : 'var(--color-text-secondary, #6b7280)',
                      }}
                    />
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Money-back note */}
        <p style={{
          textAlign: 'center',
          fontSize: '0.85rem',
          color: 'var(--color-text-muted, #9ca3af)',
          marginTop: 'var(--space-4)',
        }}>
          所有方案均含 14 天免费试用。随时取消——无需理由。
        </p>
      </section>

      {/* ═══════ FAQ ═══════ */}
      <section style={{ padding: 'var(--space-8) var(--space-3)', maxWidth: '640px', margin: '0 auto' }}>
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
      <section style={{ textAlign: 'center', padding: 'var(--space-8) var(--space-3) var(--space-10)' }}>
        <h2>14 天免费。每天早上，一份决策。</h2>
        <p style={{ color: 'var(--color-text-secondary)', marginBottom: 'var(--space-4)', fontSize: '1rem' }}>
          无需信用卡。随时取消。
        </p>
        <a
          href="https://tally.so/r/placeholder"
          className="btn btn-primary"
          style={{ fontSize: '1rem', padding: '14px 32px' }}
          target="_blank"
          rel="noopener noreferrer"
        >
          开始构建 →
        </a>
      </section>

      {/* ═══════ Footer ═══════ */}
      <footer className="site-footer">
        <div className="footer-links">
          <a href="/pricing/">English</a>
          <span className="footer-sep">|</span>
          <a href="/">Trends</a>
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
