'use client';

import { useEffect, useRef } from 'react';

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
};

export function TrendCharts({ t, history }: Props) {
  const scoreCanvasRef = useRef<HTMLCanvasElement>(null);
  const volumeCanvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    // Dynamic import Chart.js only on client
    let destroyed = false;

    async function renderCharts() {
      // Use the CDN-loaded Chart.js
      const Chart = (window as unknown as Record<string, unknown>).Chart as {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        new (ctx: CanvasRenderingContext2D, config: Record<string, unknown>): any;
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        defaults: { font: { family: string }; color: string };
      } | undefined;
      if (!Chart || history.length === 0) return;

      const sorted = [...history].reverse(); // oldest first for charts
      const labels = sorted.map((h) => h.date.slice(5)); // "MM-DD"

      // Score chart
      if (scoreCanvasRef.current && !destroyed) {
        const sCtx = scoreCanvasRef.current.getContext('2d');
        if (sCtx) {
          Chart.defaults.font.family = 'JetBrains Mono, monospace';
          Chart.defaults.color = '#737885';
          new Chart(sCtx, {
            type: 'line',
            data: {
              labels,
              datasets: [
                {
                  label: t.chartScoreTitle,
                  data: sorted.map((h) => h.top_score),
                  borderColor: '#1E40AF',
                  backgroundColor: 'transparent',
                  tension: 0.3,
                  pointRadius: 3,
                },
                {
                  label: 'Avg Score',
                  data: sorted.map((h) => h.avg_score),
                  borderColor: '#F59E0B',
                  backgroundColor: 'transparent',
                  tension: 0.3,
                  pointRadius: 2,
                  borderDash: [4, 4],
                },
              ],
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: { legend: { position: 'bottom' } },
              scales: { y: { beginAtZero: true } },
            },
          });
        }
      }

      // Volume chart
      if (volumeCanvasRef.current && !destroyed) {
        const vCtx = volumeCanvasRef.current.getContext('2d');
        if (vCtx && Chart) {
          new Chart(vCtx, {
            type: 'bar',
            data: {
              labels,
              datasets: [
                {
                  label: t.chartVolumeTitle,
                  data: sorted.map((h) => h.total_signals),
                  backgroundColor: '#3B82F6',
                  borderRadius: 4,
                },
                {
                  label: 'Cross-Platform',
                  data: sorted.map((h) => h.cross_platform),
                  backgroundColor: '#F59E0B',
                  borderRadius: 4,
                },
              ],
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: { legend: { position: 'bottom' } },
              scales: { y: { beginAtZero: true } },
            },
          });
        }
      }
    }

    // Wait for Chart.js to load from CDN
    const checkInterval = setInterval(() => {
      if ((window as unknown as Record<string, unknown>).Chart) {
        clearInterval(checkInterval);
        renderCharts();
      }
    }, 200);

    return () => {
      destroyed = true;
      clearInterval(checkInterval);
    };
  }, [history, t]);

  if (history.length === 0) return null;

  return (
    <>
      <div className="card">
        <h2>
          <svg className="icon icon-sm icon-accent" viewBox="0 0 24 24" aria-hidden="true">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
          </svg>
          {t.chartScoreTitle}
        </h2>
        <div className="chart-wrap">
          <canvas ref={scoreCanvasRef} role="img" aria-label={t.chartScoreTitle} />
        </div>
      </div>
      <div className="card">
        <h2>
          <svg className="icon icon-sm icon-accent" viewBox="0 0 24 24" aria-hidden="true">
            <rect x="2" y="14" width="4" height="6" rx="1" />
            <rect x="10" y="8" width="4" height="12" rx="1" />
            <rect x="18" y="2" width="4" height="18" rx="1" />
          </svg>
          {t.chartVolumeTitle}
        </h2>
        <div className="chart-wrap">
          <canvas ref={volumeCanvasRef} role="img" aria-label={t.chartVolumeTitle} />
        </div>
      </div>
    </>
  );
}
