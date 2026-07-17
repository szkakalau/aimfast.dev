import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import type { Metadata } from 'next';
import { parseFrontmatter } from '@/lib/frontmatter';
import { ClipboardList } from 'lucide-react';

const REPORTS_DIR = join(process.cwd(), 'content', 'reports');

export const metadata: Metadata = {
  title: 'Daily Reports — Signal Intelligence Archive | AimFast.Dev',
  description:
    'Browse all daily signal intelligence reports. Each report contains product opportunities, trend analysis, and buildable insights for indie developers.',
  robots: { index: true, follow: true },
  alternates: {
    canonical: 'https://www.aimfast.dev/reports/',
    languages: { 'zh-CN': 'https://www.aimfast.dev/reports/' },
  },
  openGraph: {
    title: 'Daily Reports — AimFast.Dev',
    description: 'Browse daily signal intelligence reports with product opportunities and trend analysis.',
    url: 'https://www.aimfast.dev/reports/',
    siteName: 'AimFast.Dev',
    locale: 'en',
    images: [
      {
        url: 'https://www.aimfast.dev/og-reports.png',
        width: 1200,
        height: 630,
        alt: 'AimFast.Dev — Daily Reports',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Daily Reports — AimFast.Dev',
    description: 'Browse daily signal intelligence reports.',
    images: ['https://www.aimfast.dev/og-reports.png'],
  },
};

interface ReportMeta {
  date: string;
  title: string;
  summary: string;
  hasZh: boolean;
}

function getReports(): ReportMeta[] {
  try {
    const files = readdirSync(REPORTS_DIR).filter((f) => f.endsWith('.md'));
    const enFiles = files.filter((f) => f.includes('-en'));
    const zhSet = new Set(
      files.filter((f) => !f.includes('-en')).map((f) => f.replace('.md', ''))
    );

    return enFiles
      .map((f) => {
        const date = f.replace('-en.md', '');
        const hasZh = zhSet.has(date);
        const filePath = join(REPORTS_DIR, f);
        const source = readFileSync(filePath, 'utf-8');

        const fm = parseFrontmatter(source);
        return {
          date,
          title: fm.title || `Daily Report — ${date}`,
          summary: fm.summary || '',
          hasZh,
        };
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
    '@graph': [
      {
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://www.aimfast.dev/' },
          { '@type': 'ListItem', position: 2, name: 'Reports', item: 'https://www.aimfast.dev/reports/' },
        ],
      },
      {
        '@type': 'CollectionPage',
        name: 'Daily Reports — AimFast.Dev',
        description: 'Daily signal intelligence reports for indie developers.',
        url: 'https://www.aimfast.dev/reports/',
        inLanguage: 'en',
        mainEntity: {
          '@type': 'ItemList',
          itemListElement: reports.map((r, i) => ({
            '@type': 'ListItem',
            position: i + 1,
            url: `https://www.aimfast.dev/reports/${r.date}/`,
          })),
        },
      },
    ],
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <main className="container">
        <div className="reports-index" style={{ padding: 'var(--space-8) 0' }}>
          <h1><ClipboardList size={28} className="icon-inline" /> Daily Reports</h1>
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
                      English
                    </a>
                    {r.hasZh && (
                      <a
                        href={`/reports/${r.date}/zh/`}
                        className="report-lang-link"
                        style={{ fontSize: '0.85rem' }}
                      >
                        · 中文
                      </a>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}

          <p style={{ marginTop: 'var(--space-6)', fontSize: '0.85rem', color: 'var(--color-muted)' }}>
            <a href="/">← Back to trends</a>
          </p>
        </div>
        <footer className="site-footer">
          <p>
            &copy; {new Date().getFullYear()} AimFast.Dev ·{' '}
            <a href="/">Trends</a> · <a href="/dashboard/">Dashboard</a> · <a href="/pricing/">Pricing</a>
          </p>
        </footer>
      </main>
    </>
  );
}
