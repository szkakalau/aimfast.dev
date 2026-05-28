export default function HomePage() {
  return (
    <main id="main-content" className="container">
      {/* ═══ Top Nav ═══ */}
      <nav className="top-nav" aria-label="Main navigation">
        <a href="/">Intel — Daily Signals & Analysis</a>
        <a href="/dashboard/" className="nav-tools">
          Tools — Signal Pipeline & Dashboard
        </a>
      </nav>

      {/* ═══ Hero ═══ */}
      <section className="hero anim-fade-up" aria-labelledby="hero-title">
        <div className="eyebrow">
          <svg className="icon icon-sm" viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="12" cy="12" r="4" />
            <path d="M4.93 4.93a10 10 0 0 1 14.14 0M4.93 19.07a10 10 0 0 0 14.14 0" />
          </svg>
          KAKAOPC Intelligence
        </div>
        <h1 id="hero-title">
          One Validated Product Opportunity
          <br />
          <span>Every Morning</span>
        </h1>
        <p className="hero-desc">
          Our AI scans 14 sources — HN, GitHub, Reddit, Product Hunt & more — every day. You
          get one signal scored, translated, and packaged into a buildable plan. Free
          newsletter, 5-minute read.
        </p>
        <form
          className="hero-signup"
          action="https://formspree.io/f/your-form-id"
          method="POST"
        >
          <input
            type="email"
            name="email"
            placeholder="you@example.com"
            autoComplete="email"
            aria-label="Email address"
            required
          />
          <button type="submit" className="btn btn-primary">
            <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
              <polyline points="22,6 12,13 2,6" />
            </svg>
            Subscribe Free
          </button>
        </form>
        <p className="hero-secondary">
          or{' '}
          <a href="/dashboard/">browse the intel dashboard</a> — see today&apos;s signals,
          report, and projects
        </p>
      </section>

      {/* ═══ Stats Bar ═══ */}
      <div className="stats-bar anim-fade-up anim-delay-1">
        <div className="stat-item">
          <div className="stat-number">14</div>
          <div className="stat-label">Signal Sources</div>
        </div>
        <div className="stat-item">
          <div className="stat-number">200+</div>
          <div className="stat-label">Signals / Day</div>
        </div>
        <div className="stat-item">
          <div className="stat-number">2h</div>
          <div className="stat-label">to Landing Page</div>
        </div>
        <div className="stat-item">
          <div className="stat-number">7d</div>
          <div className="stat-label">Validation Cycle</div>
        </div>
      </div>

      {/* ═══ How It Works ═══ */}
      <section className="workflow anim-fade-up" aria-labelledby="workflow-title">
        <div className="section-header">
          <h2 id="workflow-title">From Signal to Product in 3 Steps</h2>
          <p>
            Every morning, our pipeline turns raw internet signals into buildable
            opportunities.
          </p>
        </div>

        <div className="workflow-steps">
          <div className="workflow-step">
            <div className="step-num">01</div>
            <h3>Scan 14 Sources</h3>
            <p>
              HN, GitHub, Reddit, Product Hunt, V2EX, Jike, Xiaohongshu & more — cross-platform
              signals validated daily.
            </p>
          </div>
          <div className="workflow-step">
            <div className="step-num">02</div>
            <h3>E-P-A Framework</h3>
            <p>
              Evidence anchoring, plain-English translation, and counter-view discipline —
              every signal gets a build-or-skip verdict.
            </p>
          </div>
          <div className="workflow-step">
            <div className="step-num">03</div>
            <h3>7-Day Validation</h3>
            <p>
              Landing page in 2 hours, community feedback in 7 days. Build if it works, abandon
              if it doesn&apos;t.
            </p>
          </div>
        </div>
      </section>

      {/* ═══ CTA ═══ */}
      <section className="cta-section anim-fade-up" aria-labelledby="cta-title">
        <div className="cta-card">
          <h2 id="cta-title">Start Building With Confidence</h2>
          <p>
            Stop guessing what to build. Get one validated opportunity every morning, backed
            by cross-platform evidence.
          </p>
          <a href="/dashboard/" className="btn btn-primary">
            Explore the Dashboard →
          </a>
        </div>
      </section>

      <footer className="site-footer">
        <p>
          &copy; {new Date().getFullYear()} KAKAOPC Intel · Built with AI ·{' '}
          <a href="https://github.com/szkakalau">GitHub</a>
        </p>
      </footer>
    </main>
  );
}
