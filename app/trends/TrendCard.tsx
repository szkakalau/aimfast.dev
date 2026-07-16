'use client';

import { Calendar, Activity, BarChart3, Plus, Check } from 'lucide-react';
import type { TrendTerm } from './types';
import { stageLabel, stageLabelZh, type Locale } from './labels';

type Props = { term: TrendTerm; isTracked?: boolean; onTrack?: (id: string) => void; atLimit?: boolean; locale?: Locale };

export default function TrendCard({ term, isTracked, onTrack, atLimit, locale = 'en' }: Props) {
  const slug = term.id.replace('trend-', '');
  const isZh = locale === 'zh';
  const displayName = isZh && term.canonical_zh ? term.canonical_zh : term.canonical;
  const summary = isZh && term.summary_zh ? term.summary_zh : (term.summary_en || term.summary_zh);
  const stageText = isZh ? stageLabelZh(term.stage) : stageLabel(term.stage);
  const linkHref = isZh ? `/trends/${slug}/zh/` : `/trends/${slug}/`;

  const handleTrack = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onTrack?.(term.id);
  };

  return (
    <a
      key={term.id}
      href={linkHref}
      className={`trend-card${isTracked ? ' tracked' : ''}`}
    >
      <span className={`stage-badge ${term.stage}`}>
        {stageText}
      </span>
      {term.revenue_potential != null && (
        <span className="trend-card-stars" title={`${isZh ? '商业潜力' : 'Revenue potential'}: ${term.revenue_potential}/5`}>
          {'★'.repeat(term.revenue_potential)}{'☆'.repeat(5 - term.revenue_potential)}
        </span>
      )}
      <span className="trend-card-category">{term.category}</span>
      <h3>{displayName}</h3>
      <p className="trend-card-summary">
        {summary}
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
          {term.source_count} {isZh ? '个来源' : 'sources'}
        </span>
        <span className="trend-card-meta-item">
          <BarChart3 size={12} />
          {term.total_mentions} {isZh ? '次提及' : 'mentions'}
        </span>

        {onTrack && (
          <button
            type="button"
            className={`track-btn${isTracked ? ' tracked' : atLimit ? '' : ' track-btn-pulse'}`}
            onClick={handleTrack}
            disabled={atLimit && !isTracked}
            aria-label={
              atLimit && !isTracked
                ? (isZh ? `追踪数量已达上限 (50)。请取消关注一些项目后添加 ${displayName}。` : `Tracking limit reached (50 items). Untrack some items to add ${term.canonical}.`)
                : isTracked ? (isZh ? `取消追踪 ${displayName}` : `Untrack ${term.canonical}`) : (isZh ? `追踪 ${displayName}` : `Track ${term.canonical}`)
            }
            title={atLimit && !isTracked ? (isZh ? '追踪数量已达上限 (50)' : 'Tracking limit reached (50 items)') : undefined}
          >
            {isTracked ? (
              <><Check size={14} /> {isZh ? '已追踪' : 'Tracked'}</>
            ) : (
              <><Plus size={14} /> {isZh ? '追踪' : 'Track'}</>
            )}
          </button>
        )}
      </div>
    </a>
  );
}
