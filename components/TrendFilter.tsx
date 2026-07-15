'use client';

import { useState, useCallback, useMemo } from 'react';
import { Code2, Crosshair } from 'lucide-react';
import type { TrendTerm } from '@/app/trends/types';
import TrendCard from '@/app/trends/TrendCard';
import Pagination from '@/app/trends/Pagination';
import { stageLabel, STAGES, type StageFilter } from '@/app/trends/labels';
import { builderScore, normalizeCategory, getTrackedItems, addTrackedItem, removeTrackedItem } from '@/app/trends/utils';

const PER_PAGE = 30;

type SortKey = 'builder' | 'score' | 'opportunity' | 'revenue' | 'newest' | 'mentions';

const SORT_OPTIONS: { key: SortKey; label: string }[] = [
  { key: 'builder', label: 'Builder Score' },
  { key: 'score', label: 'Score ↓' },
  { key: 'opportunity', label: 'Opportunity ↓' },
  { key: 'revenue', label: 'Revenue ↓' },
  { key: 'newest', label: 'Newest' },
  { key: 'mentions', label: 'Most Mentioned' },
];

export default function TrendFilter({ terms }: { terms: TrendTerm[] }) {
  const [activeStage, setActiveStage] = useState<StageFilter>('all');
  const [sortKey, setSortKey] = useState<SortKey>('builder');
  const [productType, setProductType] = useState<string>('all');
  const [category, setCategory] = useState<string>('all');
  const [aiFocus, setAiFocus] = useState(false);
  const [page, setPage] = useState(1);
  const [trackedIds, setTrackedIds] = useState<Set<string>>(() => {
    const items = getTrackedItems();
    return new Set(items.map((item) => item.id));
  });

  // ── Derived data ──

  const productTypes = useMemo(() => {
    const types = new Set<string>();
    for (const t of terms) {
      for (const p of t.suggested_products || []) {
        types.add(p);
      }
    }
    return Array.from(types).sort();
  }, [terms]);

  const categories = useMemo(() => {
    const cats = new Set<string>();
    for (const t of terms) {
      const nc = normalizeCategory(t.category);
      if (nc) cats.add(nc);
    }
    return Array.from(cats).sort();
  }, [terms]);

  // ── Sort → Filter pipeline ──

  const sorted = useMemo(() => {
    const arr = [...terms];
    switch (sortKey) {
      case 'builder':
        return arr.sort((a, b) => builderScore(b) - builderScore(a));
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

  const filtered = useMemo(() => {
    let result = activeStage === 'all' ? sorted : sorted.filter((t) => t.stage === activeStage);
    if (productType !== 'all') {
      result = result.filter((t) => (t.suggested_products || []).includes(productType));
    }
    if (aiFocus) {
      result = result.filter((t) => t.category === 'AI/LLM');
    } else if (category !== 'all') {
      result = result.filter((t) => normalizeCategory(t.category) === category);
    }
    return result;
  }, [sorted, activeStage, productType, category, aiFocus]);

  // ── Pagination ──

  const totalPages = Math.max(1, Math.ceil(filtered.length / PER_PAGE));
  const pageTerms = filtered.slice((Math.min(page, totalPages) - 1) * PER_PAGE, Math.min(page, totalPages) * PER_PAGE);

  // ── Handlers (reset page on every filter change) ──

  const handleFilter = useCallback((stage: StageFilter) => {
    setActiveStage(stage);
    setPage(1);
  }, []);

  const handleProductType = useCallback((pt: string) => {
    setProductType(pt);
    setPage(1);
  }, []);

  const handleCategory = useCallback((cat: string) => {
    setCategory(cat);
    setAiFocus(false);
    setPage(1);
  }, []);

  const handleAiFocus = useCallback(() => {
    setAiFocus((prev) => !prev);
    setCategory('all');
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

  const handleTrack = useCallback((id: string) => {
    setTrackedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
        removeTrackedItem(id);
      } else {
        if (next.size >= 50) {
          // At limit — warn user via console (non-intrusive).
          // UI-level toast would require adding a notification system; out of scope for now.
          console.warn('[Track] Tracking limit reached (50 items). Remove some items to track new ones.');
          return prev;
        }
        next.add(id);
        addTrackedItem(id);
      }
      return next;
    });
  }, []);

  // ── Empty state message ──

  const emptyMessage = aiFocus
    ? 'No AI/LLM terms in this stage. Try a different stage or turn off AI Focus.'
    : category !== 'all'
      ? `No "${category}" terms in this stage. Try another category or stage.`
      : productType !== 'all'
        ? `No "${productType}" opportunities in this stage. Try another product type.`
        : 'No terms in this stage. Try another filter.';

  // ── Render ──

  return (
    <>
      {/* Stage Filter */}
      <div className="stage-filter">
        {STAGES.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => handleFilter(s)}
            className={`stage-filter-btn${s === activeStage ? ' active' : ''}`}
          >
            {s === 'all' ? 'All' : stageLabel(s)}
          </button>
        ))}
      </div>

      {/* Filter Bar — dropdowns + AI Focus + sort + count in one row */}
      <div className="filter-bar">
        <div className="filter-group">
          {categories.length > 0 && (
            <select
              className="filter-select"
              value={aiFocus ? '__ai__' : category}
              onChange={(e) => {
                const v = e.target.value;
                if (v === '__ai__') {
                  if (!aiFocus) handleAiFocus();
                } else {
                  handleCategory(v);
                }
              }}
              aria-label="Filter by category"
            >
              <option value="all">All Categories</option>
              <option value="__ai__">AI/LLM</option>
              {categories.filter(c => c !== 'AI/LLM').map((cat) => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
          )}
          {productTypes.length > 0 && (
            <select
              className="filter-select"
              value={productType}
              onChange={(e) => handleProductType(e.target.value)}
              aria-label="Filter by product type"
            >
              <option value="all">All Types</option>
              {productTypes.map((pt) => (
                <option key={pt} value={pt}>{pt}</option>
              ))}
            </select>
          )}
          <button
            type="button"
            onClick={handleAiFocus}
            className={`filter-ai-toggle${aiFocus ? ' active' : ''}`}
            aria-pressed={aiFocus}
          >
            <Crosshair size={14} aria-hidden="true" />
            AI Focus
          </button>
        </div>
        <div className="filter-right">
          <span className="sort-count">{filtered.length} results</span>
          <select
            className="sort-select"
            value={sortKey}
            onChange={handleSort}
            aria-label="Sort terms"
          >
            <optgroup label="For Builders">
              <option value="builder">{SORT_OPTIONS[0].label}</option>
            </optgroup>
            <optgroup label="General">
              {SORT_OPTIONS.slice(1).map((opt) => (
                <option key={opt.key} value={opt.key}>
                  {opt.label}
                </option>
              ))}
            </optgroup>
          </select>
        </div>
      </div>

      {/* Trend Grid */}
      {filtered.length === 0 ? (
        <div className="trends-empty" role="status">
          <h2>No matches</h2>
          <p>{emptyMessage}</p>
        </div>
      ) : (
        <>
          <div className="trend-grid" id="trend-grid">
            {pageTerms.map((term) => (
              <TrendCard key={term.id} term={term} isTracked={trackedIds.has(term.id)} onTrack={handleTrack} atLimit={trackedIds.size >= 50} />
            ))}
          </div>
          <Pagination page={page} totalPages={totalPages} onPage={goPage} />
        </>
      )}
    </>
  );
}
