'use client';

import type { Signal } from '../dashboard-client';

type Props = {
  t: Record<string, string>;
  signals: Signal[];
};

function ScoreBadge({ score }: { score: number }) {
  const cls = score >= 30 ? 'score-high' : score >= 15 ? 'score-mid' : 'score-low';
  return <span className={'score ' + cls}>{score}</span>;
}

export function TopSignals({ t, signals }: Props) {
  if (signals.length === 0) {
    return (
      <div className="card card-full">
        <h2>{t.signalsTitle}</h2>
        <div className="empty">{t.noData}</div>
      </div>
    );
  }

  return (
    <div className="card card-full">
      <h2>
        <svg className="icon icon-sm icon-accent" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
        </svg>
        {t.signalsTitle}
      </h2>
      <table aria-label={t.signalsTitle}>
        <thead>
          <tr>
            <th scope="col">{t.thRank}</th>
            <th scope="col">{t.thSignal}</th>
            <th scope="col">{t.thSource}</th>
            <th scope="col">{t.thScore}</th>
            <th scope="col">{t.thCross}</th>
            <th scope="col">{t.thEngagement}</th>
          </tr>
        </thead>
        <tbody>
          {signals.map((s, i) => (
            <tr key={s.id}>
              <td>{i + 1}</td>
              <td>
                <a className="signal-link" href={s.url} target="_blank" rel="noopener noreferrer">
                  {s.title}
                </a>
              </td>
              <td>{s.source}</td>
              <td><ScoreBadge score={s.score} /></td>
              <td>{s.cross_platform_count}</td>
              <td>{s.engagement?.total || 0}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
