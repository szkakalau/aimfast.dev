import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'AimFast.Dev — Daily Market Intelligence for Indie Builders',
  description:
    'Every morning, get one validated product opportunity — what to build, who will pay, and how much to charge. AI scans 11 sources so you don\'t have to.',
};

export default function LandingPage() {
  return (
    <main>
      {/* ─── Hero ─── */}
      <section className="hero">
        <span className="eyebrow anim-fade-up">Daily Market Intelligence</span>
        <h1 className="anim-fade-up anim-delay-1">
          One validated product opportunity.<br />
          <span>Every single morning.</span>
        </h1>
        <p className="hero-desc anim-fade-up anim-delay-2">
          AI scans 11 sources — HN, Reddit, GitHub, Product Hunt, and more —
          filters 300+ signals, and delivers one actionable insight: what to build,
          who will pay, and how much to charge.
        </p>

        <form
          className="hero-signup anim-fade-up anim-delay-2"
          action="/api/signup"
          method="POST"
        >
          <input
            type="email"
            name="email"
            placeholder="you@email.com"
            required
            aria-label="Email address"
          />
          <button type="submit" className="btn btn-primary">
            Start Free Trial →
          </button>
        </form>
        <p className="hero-secondary">
          14 days free · cancel anytime · no spam, one actionable insight per day
        </p>
      </section>

      {/* ─── Stats Bar ─── */}
      <div className="stats-bar anim-fade-up">
        <div className="stat-item">
          <div className="stat-number">11</div>
          <div className="stat-label">sources scanned daily</div>
        </div>
        <div className="stat-item">
          <div className="stat-number">300+</div>
          <div className="stat-label">signals filtered</div>
        </div>
        <div className="stat-item">
          <div className="stat-number">1</div>
          <div className="stat-label">validated insight</div>
        </div>
        <div className="stat-item">
          <div className="stat-number">2h</div>
          <div className="stat-label">to validate & build</div>
        </div>
      </div>

      {/* ─── How It Works ─── */}
      <section className="workflow">
        <div className="section-header">
          <h2>How It Works</h2>
          <p>
            Every night, our dual-engine system scans the internet so you wake up
            to a ready-made product brief every morning.
          </p>
        </div>

        <div className="workflow-steps">
          <div className="workflow-step">
            <div className="step-num">1</div>
            <h3>Discovery Engine</h3>
            <p>
              AI scans 11 sources (HN, Reddit, GitHub, Product Hunt, DEV, X, and
              more) for emerging trends, pain points, and market gaps. We filter
              out the noise — you only see the signals that matter.
            </p>
          </div>

          <div className="workflow-step">
            <div className="step-num">2</div>
            <h3>Monitoring Engine</h3>
            <p>
              Set up to 10 competitors, topics, or tech stacks you want to track.
              Every day, our AI tells you what they&apos;re doing, what it means,
              and — most importantly — what <em>you</em> should do about it.
            </p>
          </div>

          <div className="workflow-step">
            <div className="step-num">3</div>
            <h3>Daily Decision</h3>
            <p>
              Every morning, open one report. It tells you: what to build today,
              who will pay for it, and what to ignore. No more analysis paralysis
              — just one actionable decision per day.
            </p>
          </div>
        </div>
      </section>

      {/* ─── Sample Report Card ─── */}
      <section className="sample-report" style={{
        padding: 'var(--space-8) 0',
        textAlign: 'center',
      }}>
        <div className="section-header">
          <h2>Here&apos;s What You Get Every Morning</h2>
          <p>A real excerpt from a recent daily report.</p>
        </div>

        <div className="sample-report-card" style={{
          maxWidth: '680px',
          margin: '0 auto',
          background: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-lg)',
          padding: 'var(--space-5)',
          textAlign: 'left',
          fontSize: '0.92rem',
          lineHeight: '1.75',
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '0.7rem',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: 'var(--color-accent)',
            marginBottom: 'var(--space-3)',
          }}>
            📰 AimFast.Dev 日报 · 2026-07-04
          </div>

          <h3 style={{
            fontSize: '1.1rem',
            fontWeight: 600,
            marginBottom: 'var(--space-2)',
            color: 'var(--color-text)',
          }}>
            🎯 今日 2 小时构建：Gmail Photo Rescue
          </h3>

          <p style={{
            color: 'var(--color-text-secondary)',
            marginBottom: 'var(--space-3)',
          }}>
            一个一键下载 Gmail 中所有照片附件的桌面 App。<br />
            <strong style={{ color: 'var(--color-text)' }}>支撑证据：</strong>
            Mail Memories 在 HN 获得 <strong>101 赞 / 53 条讨论</strong>。
            用户评论集中在"这功能太需要了"和"但为什么不能批量导出？"。
          </p>

          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: 'var(--space-3)',
            marginBottom: 'var(--space-3)',
            padding: 'var(--space-3)',
            background: 'var(--color-surface-alt)',
            borderRadius: 'var(--radius-md)',
          }}>
            <div>
              <div style={{
                fontSize: '0.65rem',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                color: 'var(--color-text-muted)',
                marginBottom: '4px',
              }}>
                💰 定价建议
              </div>
              <div style={{
                fontFamily: 'var(--font-heading)',
                fontSize: '1.4rem',
                fontWeight: 700,
                color: 'var(--color-accent)',
              }}>
                $9.99
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>
                一次性购买
              </div>
            </div>
            <div>
              <div style={{
                fontSize: '0.65rem',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                color: 'var(--color-text-muted)',
                marginBottom: '4px',
              }}>
                ⚡ 验证路径
              </div>
              <div style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>
                2 小时 Electron MVP → Show HN → 看多少人问"能导出吗？"
              </div>
            </div>
          </div>

          <div style={{
            padding: 'var(--space-2) var(--space-3)',
            background: 'var(--color-accent-muted)',
            borderLeft: '3px solid var(--color-accent)',
            borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
            fontSize: '0.85rem',
            color: 'var(--color-text-secondary)',
          }}>
            <strong style={{ color: 'var(--color-text)' }}>为什么不选另外两个：</strong>
            ❌ Graphify 插件生态 — 巨头竞争，2 小时不够<br />
            ❌ AI Agent 安全工具 — 技术门槛高，2 小时无法交付
          </div>
        </div>
      </section>

      {/* ─── Pricing ─── */}
      <section className="pricing" style={{
        padding: 'var(--space-8) 0',
      }}>
        <div className="section-header">
          <h2>Simple Pricing</h2>
          <p>
            One plan, full access. No per-seat nonsense, no feature gating.
          </p>
        </div>

        <div style={{
          maxWidth: '400px',
          margin: '0 auto',
          background: 'var(--color-surface)',
          border: '2px solid var(--color-accent)',
          borderRadius: 'var(--radius-xl)',
          padding: 'var(--space-6)',
          textAlign: 'center',
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '0.75rem',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            color: 'var(--color-accent)',
            marginBottom: 'var(--space-2)',
          }}>
            Everything Included
          </div>

          <div style={{
            fontFamily: 'var(--font-heading)',
            fontSize: '3rem',
            fontWeight: 700,
            color: 'var(--color-text)',
            lineHeight: '1',
            marginBottom: '4px',
          }}>
            $19<span style={{ fontSize: '1.2rem', color: 'var(--color-text-muted)' }}>/mo</span>
          </div>
          <div style={{
            fontSize: '0.85rem',
            color: 'var(--color-text-muted)',
            marginBottom: 'var(--space-4)',
          }}>
            or $190/year — save $38
          </div>

          <ul style={{
            listStyle: 'none',
            padding: 0,
            marginBottom: 'var(--space-4)',
            textAlign: 'left',
            fontSize: '0.9rem',
          }}>
            <li style={checkStyle}>✓ Daily verified product opportunity</li>
            <li style={checkStyle}>✓ Competitor & topic tracking (up to 10)</li>
            <li style={checkStyle}>✓ Full report archive</li>
            <li style={checkStyle}>✓ Signal dashboard with trends</li>
            <li style={checkStyle}>✓ 14-day free trial</li>
          </ul>

          <a href="/signup" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }}>
            Start Free Trial →
          </a>

          <div style={{
            fontSize: '0.75rem',
            color: 'var(--color-text-muted)',
            marginTop: 'var(--space-2)',
          }}>
            Cancel anytime. No questions asked.
          </div>
        </div>
      </section>

      {/* ─── FAQ ─── */}
      <section className="faq" style={{
        padding: 'var(--space-8) 0',
        maxWidth: '640px',
        margin: '0 auto',
      }}>
        <div className="section-header">
          <h2>Frequently Asked Questions</h2>
        </div>

        <dl>
          {[
            {
              q: 'How is this different from reading Hacker News?',
              a: 'Hacker News gives you raw links. We give you a validated product brief — what to build, evidence of demand, who the buyer is, and how much to charge. We do the filtering, translation, and analysis so you can spend your 2 hours building, not browsing.',
            },
            {
              q: 'What sources do you scan?',
              a: 'HN, Reddit (r/programming, r/MachineLearning, r/SideProject, r/Entrepreneur, r/digitalnomad), GitHub Trending, DEV Community, Lobsters, V2EX, w2solo, X/Twitter, Product Hunt, HuggingFace, Arxiv, Indie Hackers, Douban, Xiaohongshu — 11+ sources, daily.',
            },
            {
              q: 'Can I track my competitors?',
              a: 'Yes — that is the Monitoring Engine. Add up to 10 competitors, topics, people, or tech stacks. Every day, the AI tells you what they are doing and what you should do about it. Not just "they launched X" — we tell you "their launch reveals a gap you can fill."',
            },
            {
              q: 'What if I don\'t like the daily insight?',
              a: 'Some days the insight will be better than others. That is the nature of scanning live markets. But over a month, you will see patterns emerge — recurring pain points, underserved niches, and weak competitors. The value compounds.',
            },
            {
              q: 'What happens after the 14-day trial?',
              a: 'You will be charged $19/mo (or $190/year if you choose annual). Cancel anytime before the trial ends and you pay nothing. No tricks.',
            },
          ].map(({ q, a }) => (
            <div key={q} style={{
              padding: 'var(--space-3) 0',
              borderBottom: '1px solid var(--color-border)',
            }}>
              <dt style={{
                fontWeight: 600,
                fontSize: '0.95rem',
                marginBottom: 'var(--space-1)',
                color: 'var(--color-text)',
              }}>
                {q}
              </dt>
              <dd style={{
                fontSize: '0.88rem',
                color: 'var(--color-text-secondary)',
                lineHeight: '1.7',
                marginLeft: 0,
              }}>
                {a}
              </dd>
            </div>
          ))}
        </dl>
      </section>

      {/* ─── Footer CTA ─── */}
      <section style={{
        textAlign: 'center',
        padding: 'var(--space-8) 0 var(--space-10)',
      }}>
        <h2 style={{
          fontSize: '1.5rem',
          fontWeight: 600,
          marginBottom: 'var(--space-3)',
        }}>
          Wake up to a product opportunity every morning.
        </h2>
        <a href="/signup" className="btn btn-primary" style={{ fontSize: '1rem', padding: '14px 32px' }}>
          Start Free Trial →
        </a>
      </section>

      {/* ─── Footer ─── */}
      <footer style={{
        borderTop: '1px solid var(--color-border)',
        padding: 'var(--space-5) 0',
        textAlign: 'center',
        fontSize: '0.82rem',
        color: 'var(--color-text-muted)',
      }}>
        <div style={{ marginBottom: 'var(--space-2)' }}>
          <a href="/dashboard/" style={{ color: 'var(--color-accent)', textDecoration: 'none' }}>Dashboard (subscribers)</a>
          <span style={{ margin: '0 var(--space-2)', color: 'var(--color-border)' }}>|</span>
          <a href="/reports/" style={{ color: 'var(--color-accent)', textDecoration: 'none' }}>Archive</a>
          <span style={{ margin: '0 var(--space-2)', color: 'var(--color-border)' }}>|</span>
          <a href="/articles/" style={{ color: 'var(--color-accent)', textDecoration: 'none' }}>Articles</a>
        </div>
        <div>AimFast.Dev — Daily Market Intelligence for Indie Builders</div>
      </footer>
    </main>
  );
}

const checkStyle: React.CSSProperties = {
  padding: '6px 0',
  color: 'var(--color-text-secondary)',
};
