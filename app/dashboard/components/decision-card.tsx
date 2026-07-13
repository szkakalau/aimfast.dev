'use client';

type CEndOpportunity = {
  name?: string;
  name_en?: string;
  signal_snippet?: string;
  signal_snippet_en?: string;
  buyer?: string;
  buyer_en?: string;
  pricing?: string;
  pricing_en?: string;
  validation?: string;
  validation_en?: string;
};

type DecisionData = {
  product_name?: string;
  product_name_en?: string;
  one_liner?: string;
  one_liner_en?: string;
  pricing?: string;
  pricing_en?: string;
  validation_path?: string;
  validation_path_en?: string;
  buyer?: string;
  buyer_en?: string;
  why_not_others?: string;
  why_not_others_en?: string;
  c_end_opportunities?: CEndOpportunity[];
};

type Props = {
  t: Record<string, string>;
  lang: 'zh' | 'en';
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
  decision?: DecisionData;
  reportMd: string;
  date: string;
  loading?: boolean;
  onAskAI?: () => void;
};

export function DecisionCard({ t, lang, signal, decision, reportMd: _reportMd, date, loading, onAskAI }: Props) {
  const isEn = lang === 'en';
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

  if (!signal && !decision?.product_name) {
    return (
      <div className="card card-full">
        <h2>{t.decisionCardTitle}</h2>
        <div className="empty-state">
          <p>{t.decisionNoSignal}</p>
        </div>
      </div>
    );
  }

  const scoreBadge = signal && signal.score >= 30 ? 'score-badge high' : signal && signal.score >= 15 ? 'score-badge mid' : 'score-badge';

  // Use decision data when available, fall back to signal data
  const hasDecision = !!decision?.product_name;

  return (
    <div className="card card-full decision-card">
      {/* ── Header ── */}
      <div className="decision-header">
        <h2>{t.decisionCardTitle}</h2>
        {signal && <span className={scoreBadge}>{signal.score}</span>}
      </div>

      {/* ── Product / Signal Title ── */}
      {hasDecision ? (
        <>
          <h3 className="decision-title">{isEn && decision.product_name_en ? decision.product_name_en : decision.product_name}</h3>
          <p className="decision-summary">{isEn && decision.one_liner_en ? decision.one_liner_en : decision.one_liner}</p>
        </>
      ) : (
        <>
          <h3 className="decision-title">{signal?.title}</h3>
          <p className="decision-summary">{signal?.summary}</p>
        </>
      )}

      {/* ── Evidence ── */}
      <div className="decision-section">
        <h4 className="decision-section-title">{t.decisionEvidence}</h4>
        {hasDecision && (decision.why_not_others || decision.why_not_others_en) ? (
          <p className="decision-why-not">{isEn && decision.why_not_others_en ? decision.why_not_others_en : decision.why_not_others}</p>
        ) : signal ? (
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
        ) : null}
      </div>

      {/* ── Buyer ── */}
      <div className="decision-section">
        <h4 className="decision-section-title">{t.decisionBuyer}</h4>
        <p className="decision-buyer-text">
          {hasDecision && (decision.buyer || decision.buyer_en)
            ? (isEn && decision.buyer_en ? decision.buyer_en : decision.buyer)
            : t.decisionBuyerInferred || 'Independent developers and small teams facing this problem daily.'}
        </p>
      </div>

      {/* ── Pricing + Validation ── */}
      <div className="decision-two-col">
        <div className="decision-col">
          <h4 className="decision-section-title">{t.decisionPricing}</h4>
          <div className="decision-pricing">
            <span className="pricing-amount">
              {hasDecision && (decision.pricing || decision.pricing_en)
                ? (isEn && decision.pricing_en ? decision.pricing_en : decision.pricing)
                : '$9.99'}
            </span>
            {!hasDecision && (
              <span className="pricing-unit">{t.decisionOneTime || 'one-time'}</span>
            )}
          </div>
        </div>
        <div className="decision-col">
          <h4 className="decision-section-title">{t.decisionValidation}</h4>
          <p className="decision-validation-text">
            {hasDecision && (decision.validation_path || decision.validation_path_en)
              ? (isEn && decision.validation_path_en ? decision.validation_path_en : decision.validation_path)
              : t.decisionValidationDefault || '2h MVP → post to signal source → measure response'}
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

      {/* ── C-End Consumer Opportunities ── */}
      {decision?.c_end_opportunities && decision.c_end_opportunities.length > 0 && (
        <div className="decision-cend-section">
          <h3 className="decision-cend-title">{t.cEndTitle}</h3>
          <div className="cend-list">
            {decision.c_end_opportunities.map((opp, idx) => (
              <div key={idx} className="cend-item">
                <div className="cend-item-header">
                  <span className="cend-item-index">{idx + 1}</span>
                  <h4 className="cend-item-name">{isEn && opp.name_en ? opp.name_en : opp.name}</h4>
                </div>
                <p className="cend-item-signal">{isEn && opp.signal_snippet_en ? opp.signal_snippet_en : opp.signal_snippet}</p>
                <div className="cend-item-meta">
                  <div className="cend-meta-row">
                    <span className="cend-meta-label">{t.cEndBuyer}</span>
                    <span className="cend-meta-value">{isEn && opp.buyer_en ? opp.buyer_en : opp.buyer}</span>
                  </div>
                  <div className="cend-meta-row">
                    <span className="cend-meta-label">{t.decisionPricing}</span>
                    <span className="cend-meta-value cend-pricing">{isEn && opp.pricing_en ? opp.pricing_en : opp.pricing}</span>
                  </div>
                  <div className="cend-meta-row">
                    <span className="cend-meta-label">{t.decisionValidation}</span>
                    <span className="cend-meta-value">{isEn && opp.validation_en ? opp.validation_en : opp.validation}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
