'use client';

import { BarChart3 } from 'lucide-react';
import type { CompetitorIntel, CompetitorTarget } from '../dashboard-client';

type Props = {
  t: Record<string, string>;
  intel: CompetitorIntel;
  targets: CompetitorTarget[];
};

const TYPE_CLASS: Record<string, string> = {
  competitor: 'ci-type-competitor',
  topic: 'ci-type-topic',
  person: 'ci-type-person',
  tech: 'ci-type-tech',
  platform: 'ci-type-platform',
};

const TYPE_LABEL_KEY: Record<string, string> = {
  competitor: 'ciTypeCompetitor',
  topic: 'ciTypeTopic',
  person: 'ciTypePerson',
  tech: 'ciTypeTech',
  platform: 'ciTypePlatform',
};

export function CompetitorIntel({ t, intel, targets }: Props) {
  const intelTargets = intel?.targets || [];
  const activeTargets = targets.filter((tg) => tg.status === 'active');

  if (activeTargets.length === 0 && intelTargets.length === 0) {
    return null; // Don't show if nothing set up
  }

  // Merge intel data with target definitions for type badges
  const merged = intelTargets.map((it) => {
    const targetDef = targets.find((td) => td.id === it.target_id);
    return { ...it, _type: targetDef?.type || it.target_type || 'competitor' };
  });

  return (
    <div className="ci-card" id="card-competitor">
      <div className="ci-header">
        <h2 id="ci-title">
          <svg className="icon icon-sm icon-accent" viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="12" cy="12" r="3" />
            <circle cx="5" cy="5" r="2" />
            <circle cx="19" cy="5" r="2" />
            <circle cx="5" cy="19" r="2" />
            <circle cx="19" cy="19" r="2" />
          </svg>
          <span>{t.ciTitle}</span>
        </h2>
      </div>

      {merged.length === 0 ? (
        <div className="ci-empty">{t.ciEmpty}</div>
      ) : (
        <div className="ci-target-list">
          {merged.map((it) => (
            <div key={it.target_id} className="ci-target-card">
              <div className="ci-target-header">
                <span className="ci-target-name">{it.target_name}</span>
                <span className={`ci-target-type ${TYPE_CLASS[it._type] || 'ci-type-topic'}`}>
                  {t[TYPE_LABEL_KEY[it._type] || 'ciTypeTopic'] || it._type}
                </span>
              </div>

              <div className="ci-stats">
                <span className="ci-stat">
                  📊 {it.stats.weekly_mentions} {t.ciMentions}
                </span>
                <span className={`ci-stat ${
                  it.stats.trend === 'up' ? 'ci-trend-up' : it.stats.trend === 'down' ? 'ci-trend-down' : 'ci-trend-stable'
                }`}>
                  {it.stats.trend === 'up' ? t.ciTrendUp : it.stats.trend === 'down' ? t.ciTrendDown : t.ciTrendStable}
                </span>
                {it.stats.noise_count > 0 && (
                  <span className="ci-stat">{it.stats.noise_count} {t.ciNoise}</span>
                )}
              </div>

              {it.highlights.length === 0 ? (
                <div className="ci-no-intel">{t.ciNoIntel}</div>
              ) : (
                it.highlights.slice(0, 3).map((hl, i) => (
                  <div key={i} className="ci-highlight">
                    <span className="ci-hl-source">[{hl.source}]</span>
                    <div className="ci-hl-text">{hl.translation}</div>
                    <div className="ci-hl-action">{hl.your_action}</div>
                  </div>
                ))
              )}

              {it.suggested_actions.length > 0 && (
                <div className="ci-suggested-actions">
                  {it.suggested_actions.map((act, i) => (
                    <button key={i} className={`ci-btn ${act.action === 'build' ? 'primary' : act.action === 'ignore' ? 'ignore' : ''}`}>
                      {act.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
