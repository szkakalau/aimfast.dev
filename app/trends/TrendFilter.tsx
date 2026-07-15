'use client';

import { useState, useCallback, useMemo } from 'react';
import { Calendar, Activity, BarChart3, ChevronLeft, ChevronRight } from 'lucide-react';
import type { TrendTerm } from './types';

const PER_PAGE = 30;

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

type SortKey = 'score' | 'opportunity' | 'revenue' | 'newest' | 'mentions';

const SORT_OPTIONS: { key: SortKey; label: string }[] = [
  { key: 'score', label: 'Score ↓' },
  { key: 'opportunity', label: 'Opportunity ↓' },
  { key: 'revenue', label: 'Revenue ↓' },
  { key: 'newest', label: 'Newest' },
  { key: 'mentions', label: 'Most Mentioned' },
];

export default function TrendFilter({ terms }: { terms: TrendTerm[] }) {
  const [active, setActive] = useState<StageFilter>('all');
  const [sortKey, setSortKey] = useState<SortKey>('score');
  const [page, setPage] = useState(1);

  const sorted = useMemo(() => {
    const arr = [...terms];
    switch (sortKey) {
      case 'score':
        return arr.sort((a, b) => b.score - a.score);
      case 'opportunity':
        return arr.sort((a, b) => (b.opportunity_score ?? 0) - (a.opportunity_score ?? 0));
      case 'revenue':
        return arr.sort((a, b) => (b.revenue_potential ?? 0) - (a.revenue_potential ?? 0));
      case 'newest':
        return arr.sort((a, b) => b.first_seen.localeCompare(a.first_seen));
      case 'mentions':
        return arr.sort((a, b) => b.total_mentions - a.total_mentions);
      default:
        return arr;
    }
  }, [terms, sortKey]);

  const filtered = useMemo(
    () => (active === 'all' ? sorted : sorted.filter((t) => t.stage === active)),
    [sorted, active],
  );

  const totalPages = Math.max(1, Math.ceil(filtered.length / PER_PAGE));
  const safePage = Math.min(page, totalPages);
  const pageTerms = filtered.slice((safePage - 1) * PER_PAGE, safePage * PER_PAGE);

  const handleFilter = useCallback((stage: StageFilter) => {
    setActive(stage);
    setPage(1);
  }, []);

  const handleSort = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    setSortKey(e.target.value as SortKey);
    setPage(1);
  }, []);

  const goPage = useCallback(
    (p: number) => setPage(Math.max(1, Math.min(p, totalPages))),
    [totalPages],
  );

  // Page number list: [1, ..., current-1, current, current+1, ..., totalPages] max 7 slots
  const pageNumbers = useMemo(() => {
    const pages: (number | '…')[] = [];
    if (totalPages <= 7) {
      for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      pages.push(1);
      if (safePage > 3) pages.push('…');
      const start = Math.max(2, safePage - 1);
      const end = Math.min(totalPages - 1, safePage + 1);
      for (let i = start; i <= end; i++) pages.push(i);
      if (safePage < totalPages - 2) pages.push('…');
      pages.push(totalPages);
    }
    return pages;
  }, [totalPages, safePage]);

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

      {/* ── Sort Bar ── */}
      <div className="sort-bar">
        <span className="sort-count">{filtered.length} results</span>
        <select
          className="sort-select"
          value={sortKey}
          onChange={handleSort}
          aria-label="Sort terms"
        >
          {SORT_OPTIONS.map((opt) => (
            <option key={opt.key} value={opt.key}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* ── Trend Grid ── */}
      {filtered.length === 0 ? (
        <div className="trends-empty" role="status">
          <h2>Nothing here yet</h2>
          <p>No terms in this stage. Try another filter.</p>
        </div>
      ) : (
        <>
          <div className="trend-grid" id="trend-grid">
            {pageTerms.map((term) => {
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

          {/* ── Pagination ── */}
          {totalPages > 1 && (
            <nav className="trend-pagination" aria-label="Trend pagination">
              <button
                type="button"
                className="pagination-btn"
                disabled={safePage <= 1}
                onClick={() => goPage(safePage - 1)}
                aria-label="Previous page"
              >
                <ChevronLeft size={16} />
              </button>

              {pageNumbers.map((p, i) =>
                p === '…' ? (
                  <span key={`ellipsis-${i}`} className="pagination-ellipsis">
                    …
                  </span>
                ) : (
                  <button
                    key={p}
                    type="button"
                    className={`pagination-num${p === safePage ? ' active' : ''}`}
                    onClick={() => goPage(p)}
                    aria-label={`Page ${p}`}
                    aria-current={p === safePage ? 'page' : undefined}
                  >
                    {p}
                  </button>
                ),
              )}

              <button
                type="button"
                className="pagination-btn"
                disabled={safePage >= totalPages}
                onClick={() => goPage(safePage + 1)}
                aria-label="Next page"
              >
                <ChevronRight size={16} />
              </button>
            </nav>
          )}
        </>
      )}
    </>
  );
}
