'use client';

import type { TrackedItem } from '@/app/trends/utils';

/** Minimal signal shape for delta computation. Matches daily signals.json fields we need. */
export interface SignalSnapshot {
  id: string;
  canonical: string;
  category: string;
  stage: string;
  score: number;
  total_mentions: number;
}

interface WatchlistProps {
  trackedItems: TrackedItem[];
  todaySignals: SignalSnapshot[];
  historySignals: SignalSnapshot[]; // 7 days ago — empty array if unavailable
  topRecommendations: SignalSnapshot[]; // top N signals for cold-start recommendations
  loading?: boolean;
  historyUnavailable?: boolean;
}

/** Compute 7-day score delta. Returns null if history data is unavailable or the term is too new. */
function computeDelta(today: SignalSnapshot | undefined, history: SignalSnapshot | undefined): number | null {
  if (!today || !history) return null;
  return today.score - history.score;
}

function daysSince(iso: string): number {
  return Math.floor((Date.now() - new Date(iso).getTime()) / 86400000);
}

export default function Watchlist({
  trackedItems,
  todaySignals,
  historySignals,
  topRecommendations,
  loading,
  historyUnavailable,
}: WatchlistProps) {
  // Build lookup maps
  const todayMap = new Map(todaySignals.map((s) => [s.id, s]));
  const historyMap = new Map(historySignals.map((s) => [s.id, s]));

  // ── Loading state ──
  if (loading) {
    return (
      <section className="dash-section" aria-label="My Watchlist">
        <h2 className="dash-section-title">📊 My Watchlist</h2>
        <div className="watchlist-grid">
          {[1, 2, 3].map((i) => (
            <div key={i} className="watchlist-card skeleton-card" aria-busy="true">
              <div className="skeleton skeleton-h2" />
              <div className="skeleton skeleton-text" />
            </div>
          ))}
        </div>
      </section>
    );
  }

  // ── Empty state (cold start) ──
  if (trackedItems.length === 0) {
    return (
      <section className="dash-section" aria-label="My Watchlist">
        <h2 className="dash-section-title">📊 My Watchlist</h2>
        <div className="watchlist-empty">
          <p className="watchlist-empty-text">
            Track trending terms from the <a href="/">Trends page</a> to monitor their growth here.
          </p>
        </div>
        {topRecommendations.length > 0 && (
          <>
            <p className="watchlist-recommendation-hint">Try tracking one of today&apos;s top signals:</p>
            <div className="watchlist-grid">
              {topRecommendations.slice(0, 3).map((rec) => (
                <div key={rec.id} className="watchlist-card watchlist-card-recommendation">
                  <span className="watchlist-rec-badge">🔥 Trending</span>
                  <h4 className="watchlist-card-name">{rec.canonical}</h4>
                  <span className="watchlist-card-category">{rec.category}</span>
                  <span className="watchlist-rec-score">Score: {rec.score}</span>
                </div>
              ))}
            </div>
          </>
        )}
      </section>
    );
  }

  // ── Tracked items grid ──
  return (
    <section className="dash-section" aria-label="My Watchlist">
      <div className="dash-section-header">
        <h2 className="dash-section-title">📊 My Watchlist</h2>
        <span className="watchlist-count">{trackedItems.length} tracked</span>
      </div>

      {historyUnavailable && (
        <div className="watchlist-toast" role="alert">
          Historical data temporarily unavailable. Deltas will appear once restored.
        </div>
      )}

      <div className="watchlist-grid">
        {trackedItems.map((item) => {
          const today = todayMap.get(item.id);
          const history = historyMap.get(item.id);
          const delta = computeDelta(today, history);
          const age = daysSince(item.addedAt);
          const isCollecting = age < 7;

          // Term disappeared from today's signals
          if (!today) {
            return (
              <div key={item.id} className="watchlist-card watchlist-card-gone">
                <h4 className="watchlist-card-name">{item.id.replace('trend-', '')}</h4>
                <span className="watchlist-card-delta watchlist-delta-neutral">No recent data</span>
              </div>
            );
          }

          return (
            <div key={item.id} className="watchlist-card">
              <span className={`stage-dot ${today.stage}`} aria-hidden="true" />
              <h4 className="watchlist-card-name">{today.canonical}</h4>
              <span className="watchlist-card-category">{today.category}</span>
              {isCollecting ? (
                <span className="watchlist-card-delta watchlist-delta-collecting">
                  Collecting data ({7 - age}d left)
                </span>
              ) : delta !== null ? (
                <span
                  className={`watchlist-card-delta ${
                    delta > 0 ? 'watchlist-delta-up' : delta < 0 ? 'watchlist-delta-down' : 'watchlist-delta-neutral'
                  }`}
                >
                  {delta > 0 ? '↑' : delta < 0 ? '↓' : '→'} {Math.abs(delta)} pts
                </span>
              ) : (
                <span className="watchlist-card-delta watchlist-delta-neutral">No history</span>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
