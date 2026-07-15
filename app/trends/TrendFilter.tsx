'use client';

import { useState, useCallback } from 'react';
import { Calendar, Activity, BarChart3 } from 'lucide-react';
import type { TrendTerm } from './types';

function stageLabel(stage: string): string {
  const map: Record<string, string> = {
    nascent: 'Nascent (0-7d)',
    emergent: 'Emergent (8-30d)',
    validating: 'Validating (31-90d)',
    rising: 'Rising (90d+)',
  };
  return map[stage] || stage;
}

const STAGES = ['all', 'nascent', 'emergent', 'validating', 'rising'] as const;
type StageFilter = (typeof STAGES)[number];

export default function TrendFilter({ terms }: { terms: TrendTerm[] }) {
  const [active, setActive] = useState<StageFilter>('all');

  const handleFilter = useCallback((stage: StageFilter) => {
    setActive(stage);
  }, []);

  const filtered = active === 'all' ? terms : terms.filter((t) => t.stage === active);

  return (
    <>
      {/* ── Stage Filter ── */}
      <div className="stage-filter">
        {STAGES.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => handleFilter(s)}
            className={`stage-filter-btn${s === active ? ' active' : ''}`}
          >
            {s === 'all' ? 'All' : stageLabel(s)}
          </button>
        ))}
      </div>

      {/* ── Trend Grid ── */}
      {filtered.length === 0 ? (
        <div className="trends-empty" role="status">
          <h2>Nothing here yet</h2>
          <p>No terms in this stage. Try another filter.</p>
        </div>
      ) : (
        <div className="trend-grid" id="trend-grid">
          {filtered.map((term) => {
            const slug = term.id.replace('trend-', '');
            return (
              <a
                key={term.id}
                href={`/trends/${slug}/`}
                className="trend-card"
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
                </div>
              </a>
            );
          })}
        </div>
      )}
    </>
  );
}
