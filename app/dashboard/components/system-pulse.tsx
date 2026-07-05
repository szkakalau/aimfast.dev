'use client';

type HistoryEntry = {
  date: string;
  total_signals: number;
  top_score: number;
  avg_score: number;
  action_qualified: number;
  cross_platform: number;
};

type Props = {
  t: Record<string, string>;
  history: HistoryEntry[];
  signalCount: number;
  topScore: number;
  crossPlatformCount: number;
  sourcesOnline: number;
  sourcesTotal: number;
  loading?: boolean;
};

const MINI_CHART_BARS = 14;

export function SystemPulse({ t, history, signalCount, topScore, crossPlatformCount, sourcesOnline, sourcesTotal, loading }: Props) {
  if (loading) {
    return (
      <div className="card card-full skeleton-card" aria-busy="true">
        <div className="skeleton skeleton-h2" />
        <div className="skeleton skeleton-block" style={{ height: '40px' }} />
        <div className="skeleton skeleton-text short" />
      </div>
    );
  }

  const healthy = sourcesOnline === sourcesTotal && sourcesTotal > 0;
  const statusLabel = healthy ? (t.pulseHealthy || 'Healthy') : (t.pulseDegraded || 'Degraded');
  const statusClass = healthy ? 'pulse-healthy' : 'pulse-degraded';

  // Build mini bar chart data
  const chartData = history.length > 0
    ? history.slice(-MINI_CHART_BARS).map((h) => h.total_signals)
    : [];
  const chartMax = Math.max(...chartData, 1);

  return (
    <div className="card card-full pulse-card">
      <div className="pulse-header">
        <h2>{t.pulseTitle || 'System Pulse'}</h2>
        <span className={`pulse-status ${statusClass}`}>
          <span className="status-dot" />
          {statusLabel}
        </span>
      </div>

      <div className="pulse-grid">
        {/* ── Mini chart ── */}
        <div className="pulse-chart-col">
          <div className="mini-chart" aria-label={`${MINI_CHART_BARS}-day signal volume`}>
            {chartData.length > 0 ? (
              chartData.map((v, i) => {
                const heightPct = (v / chartMax) * 100;
                return (
                  <div
                    key={i}
                    className="mini-bar"
                    style={{ height: `${Math.max(heightPct, 4)}%` }}
                    title={`${v} signals`}
                  />
                );
              })
            ) : (
              <div className="mini-chart-empty">{t.pulseNoData || 'No data yet'}</div>
            )}
          </div>
          <div className="mini-chart-label">14d</div>
        </div>

        {/* ── Stats ── */}
        <div className="pulse-stats">
          <div className="pulse-stat">
            <span className="pulse-stat-value">{signalCount}</span>
            <span className="pulse-stat-label">{t.pulseSignals || 'Signals Today'}</span>
          </div>
          <div className="pulse-stat">
            <span className="pulse-stat-value">{topScore}</span>
            <span className="pulse-stat-label">{t.pulseTopScore || 'Top Score'}</span>
          </div>
          <div className="pulse-stat">
            <span className="pulse-stat-value">{crossPlatformCount}</span>
            <span className="pulse-stat-label">{t.pulseCrossPlatform || 'Cross-Platform'}</span>
          </div>
          <div className="pulse-stat">
            <span className="pulse-stat-value">
              {sourcesOnline}<span className="pulse-stat-sub">/{sourcesTotal}</span>
            </span>
            <span className="pulse-stat-label">{t.pulseSourcesOnline || 'Sources Online'}</span>
          </div>
        </div>
      </div>

      {/* ── Archive link ── */}
      <div className="pulse-footer">
        <a href="/reports/" className="pulse-archive-link">
          {t.pulseViewArchive || 'View Full Report Archive'} →
        </a>
      </div>
    </div>
  );
}
