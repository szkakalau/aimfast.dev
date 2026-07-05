'use client';

import { useState, useMemo } from 'react';
import { ClipboardList } from 'lucide-react';

type Props = {
  t: Record<string, string>;
  reportMd: string;
};

/* ── Lightweight markdown → HTML (covers daily report structure) ── */
function renderMarkdown(md: string): string {
  const lines = md.split('\n');
  const out: string[] = [];
  let inList: 'ul' | 'ol' | null = null;
  let inBlockquote = false;

  const closeList = () => {
    if (inList === 'ul') { out.push('</ul>'); inList = null; }
    if (inList === 'ol') { out.push('</ol>'); inList = null; }
  };

  const closeBlockquote = () => {
    if (inBlockquote) { out.push('</blockquote>'); inBlockquote = false; }
  };

  const inline = (s: string): string =>
    s
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
      .replace(/`([^`]+)`/g, '<code>$1</code>');

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // Skip frontmatter ---
    if (trimmed === '---' && i < 3) {
      // skip until next ---
      const end = lines.indexOf('---', i + 1);
      if (end > i) { i = end; continue; }
    }

    // Horizontal rule
    if (/^-{3,}$/.test(trimmed)) {
      closeList();
      closeBlockquote();
      out.push('<hr />');
      continue;
    }

    // Headings
    if (trimmed.startsWith('### ')) {
      closeList(); closeBlockquote();
      out.push(`<h3>${inline(trimmed.slice(4))}</h3>`);
      continue;
    }
    if (trimmed.startsWith('## ')) {
      closeList(); closeBlockquote();
      out.push(`<h2>${inline(trimmed.slice(3))}</h2>`);
      continue;
    }
    if (trimmed.startsWith('# ')) {
      closeList(); closeBlockquote();
      out.push(`<h1>${inline(trimmed.slice(2))}</h1>`);
      continue;
    }

    // Blockquote
    if (trimmed.startsWith('> ')) {
      closeList();
      if (!inBlockquote) { out.push('<blockquote>'); inBlockquote = true; }
      out.push(`<p>${inline(trimmed.slice(2))}</p>`);
      continue;
    }
    // Handle consecutive blockquote lines that may not start with "> "
    if (inBlockquote && (trimmed === '' || trimmed.startsWith('>'))) {
      closeBlockquote();
      // fall through to blank handling
    }
    if (inBlockquote && !trimmed.startsWith('>')) {
      // close blockquote on non-empty, non-quote line
      closeBlockquote();
    }

    // Ordered list
    const olMatch = trimmed.match(/^(\d+)\.\s+(.*)/);
    if (olMatch) {
      if (inList !== 'ol') { closeList(); out.push('<ol>'); inList = 'ol'; }
      out.push(`<li>${inline(olMatch[2])}</li>`);
      continue;
    }

    // Unordered list
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      if (inList !== 'ul') { closeList(); out.push('<ul>'); inList = 'ul'; }
      out.push(`<li>${inline(trimmed.slice(2))}</li>`);
      continue;
    }

    // Blank line
    if (trimmed === '') {
      closeList();
      closeBlockquote();
      continue;
    }

    // Regular paragraph
    closeList();
    closeBlockquote();
    out.push(`<p>${inline(trimmed)}</p>`);
  }

  closeList();
  closeBlockquote();
  return out.join('\n');
}

export function FullReport({ t, reportMd }: Props) {
  const [open, setOpen] = useState(false);

  const html = useMemo(() => {
    if (!reportMd) return '';
    return renderMarkdown(reportMd);
  }, [reportMd]);

  if (!reportMd) return null;

  return (
    <div className="full-report">
      <button
        className="full-report-toggle"
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={open}
      >
        <span className="full-report-toggle-icon">{open ? '▾' : '▸'}</span>
        <ClipboardList size={16} />
        <span>{t.fullReportToggle || '完整日报'}</span>
        <span className="full-report-toggle-hint">
          {open ? (t.fullReportCollapse || '收起') : (t.fullReportExpand || '展开阅读')}
        </span>
      </button>

      {open && (
        <div className="full-report-content card">
          <div
            className="report-content"
            dangerouslySetInnerHTML={{ __html: html }}
          />
        </div>
      )}
    </div>
  );
}
