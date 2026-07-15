'use client';

import { useMemo } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

const MAX_PAGE_SLOTS = 7;

interface PaginationProps {
  page: number;
  totalPages: number;
  onPage: (p: number) => void;
}

export default function Pagination({ page, totalPages, onPage }: PaginationProps) {
  const safePage = Math.min(page, totalPages);

  const pageNumbers = useMemo(() => {
    const pages: (number | '…')[] = [];
    if (totalPages <= MAX_PAGE_SLOTS) {
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

  if (totalPages <= 1) return null;

  return (
    <nav className="trend-pagination" aria-label="Trend pagination">
      <button
        type="button"
        className="pagination-btn"
        disabled={safePage <= 1}
        onClick={() => onPage(safePage - 1)}
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
            onClick={() => onPage(p)}
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
        onClick={() => onPage(safePage + 1)}
        aria-label="Next page"
      >
        <ChevronRight size={16} />
      </button>
    </nav>
  );
}
