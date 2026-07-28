'use client';

import { useMemo } from 'react';
import { useSearchParams, usePathname } from 'next/navigation';
import { ChevronLeft, ChevronRight } from 'lucide-react';

const MAX_PAGE_SLOTS = 7;

interface PaginationProps {
  page: number;
  totalPages: number;
  onPage: (p: number) => void;
}

/** Build a crawlable href preserving all query params except page. */
function buildHref(params: URLSearchParams, pathname: string, targetPage: number): string {
  const next = new URLSearchParams(params.toString());
  if (targetPage > 1) {
    next.set('page', String(targetPage));
  } else {
    next.delete('page');
  }
  const qs = next.toString();
  return qs ? `${pathname}?${qs}` : pathname;
}

export default function Pagination({ page, totalPages, onPage }: PaginationProps) {
  const safePage = Math.min(page, totalPages);
  const searchParams = useSearchParams();
  const pathname = usePathname();

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
      {/* Prev button: use <a> for crawlability, onClick for client-side nav */}
      <a
        className={`pagination-btn${safePage <= 1 ? ' disabled' : ''}`}
        href={safePage <= 1 ? undefined : buildHref(searchParams, pathname, safePage - 1)}
        aria-label="Previous page"
        onClick={(e) => {
          if (safePage <= 1) { e.preventDefault(); return; }
          e.preventDefault();
          onPage(safePage - 1);
        }}
        {...(safePage <= 1 ? { role: 'link', 'aria-disabled': true } : {})}
      >
        <ChevronLeft size={16} />
      </a>

      {pageNumbers.map((p, i) =>
        p === '…' ? (
          <span key={`ellipsis-${i}`} className="pagination-ellipsis">
            …
          </span>
        ) : (
          <a
            key={p}
            className={`pagination-num${p === safePage ? ' active' : ''}`}
            href={buildHref(searchParams, pathname, p)}
            aria-label={`Page ${p}`}
            aria-current={p === safePage ? 'page' : undefined}
            onClick={(e) => {
              e.preventDefault();
              onPage(p);
            }}
          >
            {p}
          </a>
        ),
      )}

      {/* Next button */}
      <a
        className={`pagination-btn${safePage >= totalPages ? ' disabled' : ''}`}
        href={safePage >= totalPages ? undefined : buildHref(searchParams, pathname, safePage + 1)}
        aria-label="Next page"
        onClick={(e) => {
          if (safePage >= totalPages) { e.preventDefault(); return; }
          e.preventDefault();
          onPage(safePage + 1);
        }}
        {...(safePage >= totalPages ? { role: 'link', 'aria-disabled': true } : {})}
      >
        <ChevronRight size={16} />
      </a>
    </nav>
  );
}
