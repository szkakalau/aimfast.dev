'use client';

type Props = {
  t: Record<string, string>;
  signal: {
    id: string;
    title: string;
    url: string;
    source: string;
    source_key: string;
    signal_type: string;
    score: number;
    engagement: { likes?: number; replies?: number; points?: number; comments?: number; total: number };
    cross_platform_count: number;
    summary: string;
    tags: string[];
    author: string;
  } | null;
  reportMd: string;
  date: string;
  loading?: boolean;
  onAskAI?: () => void;
};

export function DecisionCard({ t, signal, reportMd: _reportMd, date, loading, onAskAI }: Props) {
  if (loading) {
    return (
      <div className="card card-full skeleton-card" aria-busy="true">
        <div className="skeleton skeleton-h2" />
        <div className="skeleton skeleton-text" />
        <div className="skeleton skeleton-text short" />
        <div className="skeleton skeleton-block" style={{ height: '80px' }} />
      </div>
    );
  }

  if (!signal) {
    return (
      <div className="card card-full">
        <h2>{t.decisionCardTitle}</h2>
        <div className="empty-state">
          <p>{t.decisionNoSignal}</p>
        </div>
      </div>
    );
  }

  const scoreBadge = signal.score >= 30 ? 'score-badge high' : signal.score >= 15 ? 'score-badge mid' : 'score-badge';

  return (
    <div className="card card-full decision-card">
      {/* ── Header ── */}
      <div className="decision-header">
        <h2>{t.decisionCardTitle}</h2>
        <span className={scoreBadge}>{signal.score}</span>
      </div>

      {/* ── Title ── */}
      <h3 className="decision-title">{signal.title}</h3>
      <p className="decision-summary">{signal.summary}</p>

      {/* ── Evidence ── */}
      <div className="decision-section">
        <h4 className="decision-section-title">{t.decisionEvidence}</h4>
        <div className="evidence-list">
          <div className="evidence-item">
            <span className="evidence-source">{signal.source}</span>
            <span className="evidence-stat">
              {signal.engagement.total > 0
                ? `${signal.engagement.total} ${t.decisionEngagement || 'interactions'}`
                : ''}
            </span>
          </div>
          {signal.tags.slice(0, 3).map((tag) => (
            <span key={tag} className="evidence-tag">{tag}</span>
          ))}
        </div>
      </div>

      {/* ── Buyer ── */}
      <div className="decision-section">
        <h4 className="decision-section-title">{t.decisionBuyer}</h4>
        <p className="decision-buyer-text">{signal.summary.includes('付费') || signal.summary.includes('pay') ? signal.summary : t.decisionBuyerInferred || 'Independent developers and small teams facing this problem daily.'}</p>
      </div>

      {/* ── Pricing + Validation ── */}
      <div className="decision-two-col">
        <div className="decision-col">
          <h4 className="decision-section-title">{t.decisionPricing}</h4>
          <div className="decision-pricing">
            <span className="pricing-amount">$9.99</span>
            <span className="pricing-unit">{t.decisionOneTime || 'one-time'}</span>
          </div>
        </div>
        <div className="decision-col">
          <h4 className="decision-section-title">{t.decisionValidation}</h4>
          <p className="decision-validation-text">
            {t.decisionValidationDefault || '2h MVP → post to signal source → measure response'}
          </p>
        </div>
      </div>

      {/* ── Actions ── */}
      <div className="decision-actions">
        <button className="btn-ask-ai" onClick={onAskAI} disabled={!onAskAI}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M12 2a10 10 0 1 0 10 10H12V2z" />
            <path d="M12 2a10 10 0 0 1 10 10h-4a6 6 0 0 0-6-6V2z" />
          </svg>
          {t.decisionAskAI}
        </button>
      </div>
    </div>
  );
}
