import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'AimFast.Dev — Know What Your Market Is Doing, Every Morning',
  description:
    'You\'re building. They\'re watching. Are you? — Daily competitive intel and market signals for indie developers who already have revenue.',
};

export default function LandingPage() {
  return (
    <main>
      {/* ═══════ Hero ═══════ */}
      <section className="hero">
        <span className="eyebrow anim-fade-up">Daily Market Intelligence for Indie Builders</span>
        <h1 className="anim-fade-up anim-delay-1">
          You&apos;re building.<br />
          They&apos;re watching.<br />
          <span>Are you?</span>
        </h1>
        <p className="hero-desc anim-fade-up anim-delay-2">
          Every morning, know what your competitors are doing, what trends are rising,
          and which opportunities are worth your time — in 2 minutes. Built for indie
          developers who already have revenue and can&apos;t afford to be blindsided.
        </p>

        <form
          className="hero-signup anim-fade-up anim-delay-2"
          action="https://tally.so/r/placeholder"
          method="GET"
          target="_blank"
        >
          <input
            type="email"
            name="email"
            placeholder="you@email.com"
            required
            aria-label="Email address"
          />
          <button type="submit" className="btn btn-primary">
            Get Early Access →
          </button>
        </form>
        <p className="hero-secondary">
          $19/mo after trial · cancel anytime · one actionable insight per day
        </p>
      </section>

      {/* ═══════ Pain Cards ═══════ */}
      <section className="pain-cards" style={{ padding: 'var(--space-8) 0' }}>
        <div className="section-header">
          <h2>The Cost of Not Knowing</h2>
          <p>
            Every morning without market intel costs you one of three things.
          </p>
        </div>

        <div className="pain-grid">
          {/* Pain 3: Direction Waste */}
          <div className="pain-card">
            <div className="pain-icon">⏳</div>
            <h3>Direction Waste</h3>
            <p>
              You spent 2 weeks building a feature nobody asked for. If you had
              known the demand was fading 10 days ago, you would have built
              something else.
            </p>
            <div className="pain-solution">
              <span className="pain-arrow">→</span>
              Daily decision card tells you what to build — and what to skip
            </div>
          </div>

          {/* Pain 1: Competition Blind Spots */}
          <div className="pain-card pain-card-accent">
            <div className="pain-icon">👁️</div>
            <h3>Competition Blind Spots</h3>
            <p>
              Your competitor changed their pricing 3 days ago. Their free users
              are looking for alternatives. You didn&apos;t know — until now.
            </p>
            <div className="pain-solution">
              <span className="pain-arrow">→</span>
              Monitor up to 10 competitors, topics, or tech stacks
            </div>
          </div>

          {/* Pain 2: Trend Lag */}
          <div className="pain-card">
            <div className="pain-icon">📉</div>
            <h3>Trend Lag</h3>
            <p>
              A new distribution channel is taking off. Early adopters are
              getting customers at near-zero cost. By the time you hear about it,
              the window is closed.
            </p>
            <div className="pain-solution">
              <span className="pain-arrow">→</span>
              11+ sources scanned daily for emerging signals before they peak
            </div>
          </div>
        </div>
      </section>

      {/* ═══════ Product Demo: Sample Decision Card ═══════ */}
      <section className="sample-report" style={{ padding: 'var(--space-8) 0', textAlign: 'center' }}>
        <div className="section-header">
          <h2>Here&apos;s What You Get Every Morning</h2>
          <p>A real excerpt from a recent daily report — exactly what lands in your dashboard.</p>
        </div>

        <div className="sample-decision-card">
          <div className="sample-card-header">
            <span className="sample-card-title">🎯 Today&apos;s Decision</span>
            <span className="sample-card-date">2026-07-04</span>
          </div>

          <h3 className="sample-card-opportunity">Gmail Photo Rescue</h3>
          <p className="sample-card-summary">
            One-click desktop app to download all photo attachments from Gmail.
          </p>

          <div className="sample-card-evidence">
            <strong>📊 Evidence:</strong>{' '}
            Mail Memories on HN: <strong>101 upvotes, 53 comments</strong>.
            Users repeatedly said: &ldquo;I need this&rdquo; and &ldquo;But why
            can&apos;t I batch export?&rdquo;
          </div>

          <div className="sample-card-two-col">
            <div>
              <span className="sample-card-label">💰 Pricing</span>
              <div className="sample-card-price">$9.99 <span>one-time</span></div>
            </div>
            <div>
              <span className="sample-card-label">⚡ Validation</span>
              <p className="sample-card-validation">
                2h Electron MVP → Show HN → count how many ask &ldquo;can it export?&rdquo;
              </p>
            </div>
          </div>

          <div className="sample-card-whynot">
            <strong>Why not the other two:</strong>{' '}
            ❌ Graphify plugin ecosystem — dominated by big players, can&apos;t compete in 2h{' '}
            · ❌ AI Agent security tool — technical barrier too high for a 2h validation
          </div>
        </div>
      </section>

      {/* ═══════ How It Works ═══════ */}
      <section className="workflow" style={{ padding: 'var(--space-8) 0' }}>
        <div className="section-header">
          <h2>Two Engines, One Report</h2>
          <p>
            Every night, our dual-engine system scans the internet. Every morning,
            you get one decision.
          </p>
        </div>

        <div className="engine-grid">
          <div className="engine-card">
            <div className="engine-icon">🔍</div>
            <h3>Discovery Engine</h3>
            <p>
              AI scans 11+ sources — HN, Reddit, GitHub, Product Hunt, X, DEV,
              V2EX, and more — for emerging pain points, rising trends, and
              market gaps. It filters 300+ signals down to the one that matters.
            </p>
            <ul className="engine-list">
              <li>Cross-platform signal validation</li>
              <li>Pain point vs. hype detection</li>
              <li>Actionability scoring</li>
            </ul>
          </div>

          <div className="engine-card">
            <div className="engine-icon">🛡️</div>
            <h3>Monitoring Engine</h3>
            <p>
              Track up to 10 competitors, topics, people, or tech stacks.
              Every day, the AI tells you what they did, what it means, and —
              most importantly — what <em>you</em> should do about it.
            </p>
            <ul className="engine-list">
              <li>Competitor pricing & feature changes</li>
              <li>Topic trend tracking</li>
              <li>Actionable alerts, not noise</li>
            </ul>
          </div>
        </div>

        <div className="engine-arrow" aria-hidden="true">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 5v14M5 12l7 7 7-7" />
          </svg>
        </div>

        <div className="engine-output">
          <span className="engine-output-label">Daily Report</span>
          One decision card · Competitor updates · System pulse · 2 minutes to read
        </div>
      </section>

      {/* ═══════ Pricing ═══════ */}
      <section className="pricing-section" style={{ padding: 'var(--space-8) 0' }}>
        <div className="section-header">
          <h2>Simple Pricing</h2>
          <p>
            One plan, everything included. No per-seat pricing, no feature gating.
            You either get full value or you cancel — no hard feelings.
          </p>
        </div>

        <div className="pricing-card">
          <div className="pricing-badge">Everything Included</div>

          <div className="pricing-amount-row">
            <span className="pricing-dollar">$</span>
            <span className="pricing-number">19</span>
            <span className="pricing-period">/mo</span>
          </div>
          <div className="pricing-annual">or $190/year — save $38</div>

          <ul className="pricing-features">
            <li>✓ Daily verified product opportunity</li>
            <li>✓ Competitor & topic tracking (up to 10)</li>
            <li>✓ Full report archive</li>
            <li>✓ Signal dashboard with system pulse</li>
            <li>✓ AI assistant (coming soon)</li>
            <li>✓ 14-day free trial</li>
          </ul>

          <a
            href="https://tally.so/r/placeholder"
            className="btn btn-primary pricing-cta"
            target="_blank"
          >
            Start Free Trial →
          </a>

          <div className="pricing-cancel">Cancel anytime. No questions asked.</div>
        </div>
      </section>

      {/* ═══════ FAQ ═══════ */}
      <section className="faq-section" style={{ padding: 'var(--space-8) 0', maxWidth: '640px', margin: '0 auto' }}>
        <div className="section-header">
          <h2>Frequently Asked Questions</h2>
        </div>

        <dl className="faq-list">
          {[
            {
              q: 'How is this different from setting up Google Alerts?',
              a: 'Google Alerts gives you links. We give you a decision. Our AI reads 300+ signals across 11 platforms, cross-references them, scores them, and tells you "build this, skip that." Google Alerts cannot tell you that a Reddit complaint and a GitHub star spike are the same unmet need.',
            },
            {
              q: 'What sources do you scan?',
              a: 'HN, Reddit (r/programming, r/MachineLearning, r/SideProject, r/Entrepreneur, r/digitalnomad), GitHub Trending, DEV Community, Lobsters, V2EX, X/Twitter, Product Hunt, HuggingFace, Arxiv, Indie Hackers, and more — 11+ sources, daily.',
            },
            {
              q: 'Can I track my competitors?',
              a: 'Yes — that is the Monitoring Engine. Add up to 10 competitors, topics, people, or tech stacks. Every day, you see what they did and what you should do about it. Not just "they launched X" — we tell you "their launch reveals a gap you can fill."',
            },
            {
              q: 'What if I miss a day?',
              a: 'Every report is archived. You can browse past daily decisions and full reports from the dashboard at any time. The value compounds — patterns emerge over weeks, not days.',
            },
            {
              q: 'Is there a long-term contract?',
              a: 'No. Cancel anytime — monthly or annual. If you cancel, you keep access until the end of your billing period. No tricks, no retention calls.',
            },
          ].map(({ q, a }) => (
            <div key={q} className="faq-item">
              <dt>{q}</dt>
              <dd>{a}</dd>
            </div>
          ))}
        </dl>
      </section>

      {/* ═══════ Footer CTA ═══════ */}
      <section className="footer-cta" style={{ textAlign: 'center', padding: 'var(--space-8) 0 var(--space-10)' }}>
        <h2>You&apos;re building. They&apos;re watching.</h2>
        <p style={{ color: 'var(--color-text-secondary)', marginBottom: 'var(--space-3)', fontSize: '1rem' }}>
          Start your 14-day free trial. One decision every morning.
        </p>
        <a
          href="https://tally.so/r/placeholder"
          className="btn btn-primary"
          style={{ fontSize: '1rem', padding: '14px 32px' }}
          target="_blank"
        >
          Get Early Access →
        </a>
      </section>

      {/* ═══════ Footer ═══════ */}
      <footer className="site-footer">
        <div className="footer-links">
          <a href="/dashboard/">Dashboard</a>
          <span className="footer-sep">|</span>
          <a href="/reports/">Archive</a>
        </div>
        <div className="footer-copy">
          AimFast.Dev — Daily Market Intelligence for Indie Builders
        </div>
      </footer>
    </main>
  );
}
