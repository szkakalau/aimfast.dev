'use client';

import { useState } from 'react';

type CompetitorTarget = {
  id: string;
  name: string;
  type: string;
  aliases: string[];
  keywords: string[];
  status: string;
};

type CompetitorIntelTarget = {
  target_id: string;
  target_name: string;
  target_type: string;
  stats: {
    weekly_mentions: number;
    trend: string;
    sentiment: string;
    noise_count: number;
    signal_count: number;
    core_narrative: string;
  };
  highlights: Array<{
    source: string;
    source_url: string;
    original_text: string;
    translation: string;
    competitor_impact: string;
    your_action: string;
    relevance: string;
  }>;
  suggested_actions: Array<{ action: string; label: string }>;
  noise_summary: string;
};

type Props = {
  t: Record<string, string>;
  intel: {
    date: string;
    target_count: number;
    targets: CompetitorIntelTarget[];
  } | null;
  targets: CompetitorTarget[];
  loading?: boolean;
  onAskAI?: () => void;
};

export function CompetitorCard({ t, intel, targets, loading, onAskAI }: Props) {
  const [showAdd, setShowAdd] = useState(false);

  if (loading) {
    return (
      <div className="card card-full skeleton-card" aria-busy="true">
        <div className="skeleton skeleton-h2" />
        <div className="skeleton skeleton-text" />
        <div className="skeleton skeleton-text short" />
      </div>
    );
  }

  const hasTargets = targets && targets.length > 0;
  const hasIntel = intel && intel.targets && intel.targets.length > 0;

  return (
    <div className="card card-full competitor-card">
      <h2>{t.ciTitle || t.competitorCardTitle}</h2>

      {!hasTargets ? (
        /* Empty: no tracking targets */
        <div className="empty-state">
          <p>{t.ciEmpty || t.competitorEmpty || 'No tracking targets set up yet.'}</p>
          <button className="btn btn-sm btn-outline" onClick={() => setShowAdd(!showAdd)}>
            {t.ciAddTarget || t.competitorAddTarget || '+ Add Target'}
          </button>
          {showAdd && (
            <div className="quick-add" style={{ marginTop: 'var(--space-2)' }}>
              <input
                type="text"
                className="input"
                placeholder={t.competitorAddPlaceholder || 'Competitor name, topic, or tech…'}
                style={{ width: '100%', maxWidth: '320px' }}
              />
              <button className="btn btn-sm btn-primary" style={{ marginLeft: 'var(--space-1)' }}>
                {t.competitorAddConfirm || 'Add'}
              </button>
            </div>
          )}
        </div>
      ) : !hasIntel ? (
        /* Has targets but no intel today */
        <div className="empty-state">
          <p>{t.ciNoIntel || t.competitorNoIntel}</p>
        </div>
      ) : (
        /* Has intel — show per-target summaries */
        <div className="competitor-list">
          {intel.targets.map((ct) => {
            const trendIcon = ct.stats.trend === 'up' ? '↑' : ct.stats.trend === 'down' ? '↓' : '→';
            const trendClass = ct.stats.trend === 'up' ? 'trend-up' : ct.stats.trend === 'down' ? 'trend-down' : 'trend-stable';
            const topAction = ct.suggested_actions?.[0];

            return (
              <div key={ct.target_id} className="competitor-item">
                <div className="competitor-item-header">
                  <span className="competitor-name">{ct.target_name}</span>
                  <span className="type-badge">{ct.target_type}</span>
                  <span className={`trend-icon ${trendClass}`}>{trendIcon}</span>
                  <span className="mention-count">{ct.stats.weekly_mentions} {t.ciMentions || 'mentions'}</span>
                </div>
                <p className="competitor-narrative">{ct.stats.core_narrative}</p>
                {topAction && (
                  <p className="competitor-action">
                    <span className="action-arrow">{t.competitorAction || '→ Your move'}:</span>{' '}
                    {topAction.label}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* ── Actions ── */}
      <div className="decision-actions" style={{ borderTop: hasIntel ? '1px solid var(--color-border)' : 'none', paddingTop: hasIntel ? 'var(--space-2)' : 0 }}>
        {hasTargets && (
          <button className="btn btn-sm btn-outline" onClick={() => setShowAdd(!showAdd)}>
            + {t.ciAddTarget || 'Add Target'}
          </button>
        )}
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
