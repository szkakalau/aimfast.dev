'use client';

import type { Signal } from '../dashboard-client';

type Props = {
  t: Record<string, string>;
  topSignal: Signal | null;
  betCount: number;
  signalCount: number;
};

export function DashboardHero({ t, topSignal, betCount, signalCount }: Props) {
  return (
    <div className="card card-full">
      <div className="top-hero">
        <div className="hero-left">
          <div className="hero-label">{t.heroOpportunity}</div>
          <div className="hero-demand">
            {topSignal ? topSignal.title : '--'}
          </div>
          {topSignal && (
            <div className="hero-meta">
              Score: {topSignal.score} · {topSignal.source}
            </div>
          )}
        </div>
        <div className="hero-right">
          <div className="hero-label">{t.heroBets}</div>
          <div className="hero-bet-count">{betCount}</div>
          <div className="hero-sub">{t.heroSubBets}</div>
        </div>
        <div className="hero-right">
          <div className="hero-label">{t.heroSignals}</div>
          <div className="hero-bet-count">{signalCount}</div>
          <div className="hero-sub">{t.heroSubSignals}</div>
        </div>
      </div>
    </div>
  );
}
