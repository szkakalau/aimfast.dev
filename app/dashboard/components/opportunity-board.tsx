'use client';

import { useState, useCallback } from 'react';
import type { Bet, Lesson, OppEntry } from '../dashboard-client';

type Props = {
  t: Record<string, string>;
  bets: Bet[];
  opportunities: OppEntry[];
  demandRadar: Record<string, unknown>;
  lessons: Lesson[];
  onPlaceBet: (demandName: string, demandId: string) => void;
};

const STAGE_BADGE: Record<string, string> = {
  breaking: 'opp-stage breaking',
  forming: 'opp-stage forming',
  early: 'opp-stage',
  mature: 'opp-stage',
};

const LESSON_TYPE_CLASS: Record<string, string> = {
  no_traffic: 'lesson-type no_traffic',
  no_conversion: 'lesson-type no_conversion',
  signal_weak: 'lesson-type signal_weak',
  needs_pivot: 'lesson-type needs_pivot',
  market_nonexistent: 'lesson-type market_nonexistent',
};

export function OpportunityBoard({ t, bets, opportunities, demandRadar, lessons, onPlaceBet }: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const activeBets = bets.filter((b) => b.status === 'active');

  const toggleExpand = useCallback((id: string) => {
    setExpandedId((prev) => (prev === id ? null : id));
  }, []);

  // Use demand_radar demands if available, otherwise use opportunities
  const radarDemands = (demandRadar as Record<string, unknown>)?.demands as OppEntry[] | undefined;
  const demands: OppEntry[] = (Array.isArray(radarDemands) ? radarDemands : null) || opportunities;

  return (
    <div className="card card-full" id="card-data">
      <h2>
        <svg className="icon icon-sm icon-accent" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 6v6l4 2" />
        </svg>
        {t.oppBoardTitle}
      </h2>

      <div className="opp-board">
        {/* ── Zone 1: Active Bets ── */}
        <section className="opp-zone">
          <h3 className="opp-zone-title">{t.oppActiveBets}</h3>
          {activeBets.length === 0 ? (
            <div className="empty">{t.oppActiveBetsEmpty}</div>
          ) : (
            activeBets.map((bet) => {
              const createdDate = bet.created_at ? new Date(bet.created_at) : null;
              const daysSinceCreation = createdDate
                ? Math.floor((Date.now() - createdDate.getTime()) / (1000 * 60 * 60 * 24))
                : 0;
              const daysLeft = (bet.timeline_days || 7) - daysSinceCreation;
              const isDue = daysLeft <= 0;

              return (
                <div key={bet.id} className="active-bet-row">
                  <span className={`bet-status-dot ${isDue ? 'review-due' : 'active-bet'}`} />
                  <span className="opp-card-name">{bet.demand}</span>
                  <span className={`opp-stage ${bet.action === 'build' ? 'breaking' : 'forming'}`}>
                    {bet.action === 'observe' && t.oppObserve}
                    {bet.action === 'validate' && t.oppValidate}
                    {bet.action === 'build' && t.oppBuild}
                  </span>
                  <span className="bet-day-counter">
                    {isDue ? '⚠ Review Due' : `${daysLeft}d left`}
                  </span>
                </div>
              );
            })
          )}
        </section>

        {/* ── Zone 2: Opportunity Pipeline ── */}
        <section className="opp-zone">
          <h3 className="opp-zone-title">{t.oppPipeline}</h3>
          {demands.length === 0 ? (
            <div className="empty">{t.oppPipelineEmpty}</div>
          ) : (
            demands.slice(0, 10).map((opp, i) => {
              const id = opp.id || opp.name || `opp-${i}`;
              const name = opp.name || opp.demand || '';
              const score = opp.score || 0;
              const stage = opp.stage || 'forming';
              const why = opp.why || '';
              const isExpanded = expandedId === id;

              return (
                <div key={id} className={`opp-card ${isExpanded ? 'expanded' : ''}`}>
                  <div className="opp-card-header" onClick={() => toggleExpand(id)}>
                    <span className="opp-card-rank">{i + 1}</span>
                    <span className="opp-card-name">{name}</span>
                    {opp._suggested && <span className="badge-ai-suggest">AI</span>}
                    <span className="opp-card-why">{why}</span>
                    <div className="opp-card-indicators">
                      <span className="opp-score">{score}</span>
                      <span className={STAGE_BADGE[stage] || 'opp-stage'}>
                        {stage === 'breaking' ? 'Breaking' : stage === 'forming' ? 'Forming' : stage}
                      </span>
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="opp-card-detail">
                      <div className="opp-detail-grid">
                        <div className="opp-detail-item">
                          <div className="opp-detail-label">Score</div>
                          <div className="opp-detail-val">{score}</div>
                        </div>
                        <div className="opp-detail-item">
                          <div className="opp-detail-label">Stage</div>
                          <div className="opp-detail-val">{stage}</div>
                        </div>
                        <div className="opp-detail-item">
                          <div className="opp-detail-label">Why</div>
                          <div className="opp-detail-val" style={{ fontSize: '0.85rem' }}>
                            {why || '--'}
                          </div>
                        </div>
                      </div>
                      <div className="opp-card-actions" style={{ borderTop: 'none', paddingLeft: 0, paddingRight: 0 }}>
                        <button className="btn-opp-action primary-action" onClick={() => onPlaceBet(name, id)}>
                          {t.betDrawerTitle}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </section>

        {/* ── Zone 3: Recent Lessons ── */}
        <section className="opp-zone">
          <h3 className="opp-zone-title">{t.oppLessons}</h3>
          {lessons.length === 0 ? (
            <div className="empty">{t.oppLessonsEmpty}</div>
          ) : (
            lessons.slice(0, 5).map((ls) => (
              <div key={ls.id} className="lesson-row">
                <span className={LESSON_TYPE_CLASS[ls.type] || 'lesson-type'}>
                  {ls.type}
                </span>
                <strong> {ls.opportunity}</strong>: {ls.lesson}
              </div>
            ))
          )}
        </section>
      </div>
    </div>
  );
}
