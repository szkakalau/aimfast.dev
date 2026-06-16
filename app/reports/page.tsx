import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import type { Metadata } from 'next';

const REPORTS_DIR = join(process.cwd(), 'content', 'reports');

export const metadata: Metadata = {
  title: 'Daily Reports — AimFast.Dev',
  description:
    'Browse all daily signal intelligence reports. Each report contains product opportunities, trend analysis, and buildable insights for indie developers.',
  robots: { index: true, follow: true },
  alternates: { canonical: 'https://aimfast.dev/reports/' },
  openGraph: {
    title: 'Daily Reports — AimFast.Dev',
    description: 'Browse daily signal intelligence reports with product opportunities and trend analysis.',
    url: 'https://aimfast.dev/reports/',
    siteName: 'AimFast.Dev',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Daily Reports — AimFast.Dev',
    description: 'Browse daily signal intelligence reports.',
  },
};

interface ReportMeta {
  date: string;
  title: string;
  summary: string;
  hasEn: boolean;
}

function getReports(): ReportMeta[] {
  try {
    const files = readdirSync(REPORTS_DIR).filter((f) => f.endsWith('.md'));
    const zhFiles = files.filter((f) => !f.includes('-en'));
    const enSet = new Set(
      files.filter((f) => f.includes('-en')).map((f) => f.replace('-en.md', ''))
    );

    return zhFiles
      .map((f) => {
        const date = f.replace('.md', '');
        const hasEn = enSet.has(date);
        const filePath = join(REPORTS_DIR, f);
        const source = readFileSync(filePath, 'utf-8');

        let title = `Daily Report — ${date}`;
        let summary = '';
        const fmMatch = source.match(/^---\r?\n([\s\S]*?)\r?\n---/);
        if (fmMatch) {
          const lines = fmMatch[1].split('\n');
          for (const line of lines) {
            const colonIdx = line.indexOf(':');
            if (colonIdx > 0) {
              const key = line.slice(0, colonIdx).trim();
              let val = line.slice(colonIdx + 1).trim();
              if (
                (val.startsWith('"') && val.endsWith('"')) ||
                (val.startsWith("'") && val.endsWith("'"))
              ) {
                val = val.slice(1, -1);
              }
              if (key === 'title') title = val;
              if (key === 'summary') summary = val;
            }
          }
        }
        return { date, title, summary, hasEn };
      })
      .sort((a, b) => b.date.localeCompare(a.date)); // newest first
  } catch {
    return [];
  }
}

export default function ReportsIndexPage() {
  const reports = getReports();

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'CollectionPage',
    name: 'Daily Reports — AimFast.Dev',
    description: 'Daily signal intelligence reports for indie developers.',
    url: 'https://aimfast.dev/reports/',
    mainEntity: {
      '@type': 'ItemList',
      itemListElement: reports.map((r, i) => ({
        '@type': 'ListItem',
        position: i + 1,
        url: `https://aimfast.dev/reports/${r.date}/`,
      })),
    },
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <main className="container">
        <div className="reports-index" style={{ padding: 'var(--space-8) 0' }}>
          <h1>📋 Daily Reports</h1>
          <p style={{ color: 'var(--color-muted)', marginBottom: 'var(--space-6)' }}>
            {reports.length} report{reports.length !== 1 ? 's' : ''} available. Click any date to read the full report.
          </p>

          {reports.length === 0 ? (
            <p>No reports yet. Check back after the daily pipeline runs.</p>
          ) : (
            <ul className="reports-list">
              {reports.map((r) => (
                <li key={r.date}>
                  <a href={`/reports/${r.date}/`}>
                    <h2>{r.title}</h2>
                    <time dateTime={r.date}>{r.date}</time>
                    {r.summary && <p>{r.summary}</p>}
                  </a>
                  <div style={{ marginTop: 'var(--space-2)' }}>
                    <a href={`/reports/${r.date}/`} style={{ fontSize: '0.85rem' }}>
                      中文
                    </a>
                    {r.hasEn && (
                      <a
                        href={`/reports/${r.date}/en/`}
                        className="report-lang-link"
                        style={{ fontSize: '0.85rem' }}
                      >
                        · English
                      </a>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}

          <p style={{ marginTop: 'var(--space-6)', fontSize: '0.85rem', color: 'var(--color-muted)' }}>
            <a href="/">← Back to home</a>
          </p>
        </div>
        <footer className="site-footer">
          <p>
            &copy; {new Date().getFullYear()} AimFast.Dev ·{' '}
            <a href="/">Home</a> · <a href="/dashboard/">Dashboard</a>
          </p>
        </footer>
      </main>
    </>
  );
}
