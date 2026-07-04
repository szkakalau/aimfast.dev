'use client';

import { useMemo, useEffect, useRef, useState, useCallback } from 'react';
import { marked } from 'marked';

type ArchiveEntry = {
  date: string;
  report_md: string;
  report_md_en: string;
  has_report: boolean;
};

type Props = {
  t: Record<string, string>;
  lang: 'zh' | 'en';
  reportMd: string;
  date: string;
  archive: ArchiveEntry[];
  selectedDate: string;
  onSelectDate: (date: string) => void;
};

export function DailyReport({ t, lang, reportMd, date, archive, selectedDate, onSelectDate }: Props) {
  const [activeId, setActiveId] = useState('');
  const [showBackToTop, setShowBackToTop] = useState(false);
  const reportRef = useRef<HTMLDivElement>(null);
  const readingBarRef = useRef<HTMLDivElement>(null);

  // Render markdown
  const html = useMemo(() => {
    if (!reportMd) return '';
    return marked(reportMd, { breaks: true, gfm: true }) as string;
  }, [reportMd]);

  // Extract headings for TOC
  const toc = useMemo(() => {
    const headings: { id: string; text: string; level: number }[] = [];
    if (!reportMd) return headings;
    const lines = reportMd.split('\n');
    for (const line of lines) {
      const match = line.match(/^(#{1,3})\s+(.+)/);
      if (match) {
        const text = match[2].replace(/[#*`~\[\]]/g, '').trim();
        const id = text.toLowerCase().replace(/\s+/g, '-').replace(/[^\w-]/g, '');
        headings.push({ id, text, level: match[1].length });
      }
    }
    return headings;
  }, [reportMd]);

  // Intersection observer for TOC active state
  useEffect(() => {
    if (!reportRef.current) return;
    const headingEls = reportRef.current.querySelectorAll('h1, h2, h3');
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id);
            break;
          }
        }
      },
      { rootMargin: '-80px 0px -70% 0px' }
    );
    headingEls.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [html]);

  // Reading progress
  useEffect(() => {
    const handleScroll = () => {
      const scrollTop = window.scrollY;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      const progress = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
      if (readingBarRef.current) {
        readingBarRef.current.style.width = `${Math.min(progress, 100)}%`;
      }
      setShowBackToTop(scrollTop > 500);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToTop = useCallback(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  // Archive navigation
  const dates = useMemo(() => archive.filter((a) => a.has_report).map((a) => a.date), [archive]);
  const currentIdx = dates.indexOf(selectedDate);

  const goPrev = useCallback(() => {
    if (currentIdx > 0) onSelectDate(dates[currentIdx - 1]);
  }, [currentIdx, dates, onSelectDate]);

  const goNext = useCallback(() => {
    if (currentIdx < dates.length - 1) onSelectDate(dates[currentIdx + 1]);
  }, [currentIdx, dates, onSelectDate]);

  if (!reportMd) {
    return (
      <div className="card card-full">
        <h2>{t.reportTitle}</h2>
        <div className="empty">{t.noData}</div>
      </div>
    );
  }

  return (
    <div className="card card-full" id="card-content">
      {/* Header */}
      <div className="content-header">
        <h2>
          <svg className="icon icon-sm icon-accent" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
          </svg>
          {t.reportTitle}
        </h2>

        {/* Archive nav */}
        {dates.length > 1 && (
          <div className="archive-nav" aria-label="Archive date navigation">
            <button className="archive-arrow" onClick={goPrev} disabled={currentIdx <= 0} aria-label="Previous day">
              <svg className="icon icon-sm" viewBox="0 0 24 24" aria-hidden="true">
                <polyline points="15 18 9 12 15 6" />
              </svg>
            </button>
            <div className="archive-dates">
              {dates.slice(0, 14).map((d) => (
                <button
                  key={d}
                  className={`archive-date-btn ${d === selectedDate ? 'active' : ''}`}
                  onClick={() => onSelectDate(d)}
                >
                  {d.slice(5)}
                </button>
              ))}
            </div>
            <button className="archive-arrow" onClick={goNext} disabled={currentIdx >= dates.length - 1} aria-label="Next day">
              <svg className="icon icon-sm" viewBox="0 0 24 24" aria-hidden="true">
                <polyline points="9 18 15 12 9 6" />
              </svg>
            </button>
          </div>
        )}
      </div>

      {/* Reading progress */}
      <div id="reading-progress">
        <div id="reading-progress-bar" ref={readingBarRef} />
      </div>

      {/* TOC dropdown (mobile) */}
      {toc.length > 0 && (
        <div className="toc-dropdown-wrap">
          <select
            onChange={(e) => {
              const el = document.getElementById(e.target.value);
              if (el) el.scrollIntoView({ behavior: 'smooth' });
            }}
            aria-label={t.tocTitle}
          >
            <option value="">{t.tocJumpTo}</option>
            {toc.map((h) => (
              <option key={h.id} value={h.id}>
                {'  '.repeat(h.level - 1)}{h.text}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Report layout */}
      <div className="report-layout">
        {toc.length > 0 && (
          <nav className="toc-sidebar" aria-label={t.tocTitle}>
            <div className="toc-title">{t.tocTitle}</div>
            {toc.map((h) => (
              <a
                key={h.id}
                href={`#${h.id}`}
                className={activeId === h.id ? 'active' : ''}
                style={{ paddingLeft: `${(h.level - 1) * 12 + 8}px` }}
                onClick={(e) => {
                  e.preventDefault();
                  const el = document.getElementById(h.id);
                  if (el) el.scrollIntoView({ behavior: 'smooth' });
                }}
              >
                {h.text}
              </a>
            ))}
          </nav>
        )}

        <div
          ref={reportRef}
          className="report-body"
          role="region"
          aria-label={t.reportAria}
          dangerouslySetInnerHTML={{ __html: html }}
        />
      </div>

      {/* Back to top */}
      {showBackToTop && (
        <button className="btn-back-to-top" onClick={scrollToTop} aria-label={t.backToTop} title={t.backToTop}>
          ↑
        </button>
      )}
    </div>
  );
}
