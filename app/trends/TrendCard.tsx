'use client';

import { Calendar, Activity, BarChart3, Plus, Check } from 'lucide-react';
import type { TrendTerm } from './types';
import { stageLabel } from './labels';

type Props = { term: TrendTerm; isTracked?: boolean; onTrack?: (id: string) => void };

export default function TrendCard({ term, isTracked, onTrack }: Props) {
  const slug = term.id.replace('trend-', '');

  const handleTrack = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onTrack?.(term.id);
  };

  return (
    <a
      key={term.id}
      href={`/trends/${slug}/`}
      className={`trend-card${isTracked ? ' tracked' : ''}`}
    >
      <span className={`stage-badge ${term.stage}`}>
        {stageLabel(term.stage)}
      </span>
      {term.revenue_potential != null && (
        <span className="trend-card-stars" title={`Revenue potential: ${term.revenue_potential}/5`}>
          {'★'.repeat(term.revenue_potential)}{'☆'.repeat(5 - term.revenue_potential)}
        </span>
      )}
      <span className="trend-card-category">{term.category}</span>
      <h3>{term.canonical}</h3>
      <p className="trend-card-summary">
        {term.summary_en || term.summary_zh}
      </p>

      {/* Builder signals: show when opportunity data exists */}
      {(term.estimated_dev_days != null ||
        term.suggested_products?.length ||
        term.revenue_potential != null) && (
        <div className="trend-card-builder">
          {term.estimated_dev_days != null && (
            <span>{term.estimated_dev_days}d MVP</span>
          )}
          {term.suggested_products?.[0] && (
            <>
              <span className="builder-sep">·</span>
              <span>{term.suggested_products[0]}</span>
            </>
          )}
          {term.revenue_potential != null && (
            <>
              <span className="builder-sep">·</span>
              <span title={`Revenue potential: ${term.revenue_potential}/5`}>
                {'★'.repeat(term.revenue_potential)}{'☆'.repeat(5 - term.revenue_potential)}
              </span>
            </>
          )}
        </div>
      )}

      <div className="trend-card-meta">
        <span className="trend-card-meta-item">
          <Calendar size={12} />
          {term.first_seen}
        </span>
        <span className="trend-card-meta-item">
          <Activity size={12} />
          {term.source_count} sources
        </span>
        <span className="trend-card-meta-item">
          <BarChart3 size={12} />
          {term.total_mentions} mentions
        </span>

        {onTrack && (
          <button
            type="button"
            className={`track-btn${isTracked ? ' tracked' : ''}`}
            onClick={handleTrack}
            aria-label={isTracked ? `Untrack ${term.canonical}` : `Track ${term.canonical}`}
          >
            {isTracked ? (
              <><Check size={14} /> Tracked</>
            ) : (
              <><Plus size={14} /> Track</>
            )}
          </button>
        )}
      </div>
    </a>
  );
}
