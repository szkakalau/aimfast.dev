import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { compileMDX } from 'next-mdx-remote/rsc';
import type { Metadata } from 'next';
import { isValidPathSegment } from '@/lib/path-security';
import { parseFrontmatterWithBody } from '@/lib/frontmatter';

const REPORTS_DIR = join(process.cwd(), 'content', 'reports');

function getReportDates(): string[] {
  try {
    return readdirSync(REPORTS_DIR)
      .filter((f) => f.endsWith('-en.md'))
      .map((f) => f.replace(/-en\.md$/, ''));
  } catch {
    return [];
  }
}

function hasZhVersion(date: string): boolean {
  try {
    const zhPath = join(REPORTS_DIR, `${date}.md`);
    return readFileSync(zhPath, 'utf-8') !== undefined;
  } catch {
    return false;
  }
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ date: string }>;
}): Promise<Metadata> {
  const { date } = await params;
  if (!isValidPathSegment(date)) {
    return { title: 'Invalid Request — AimFast.Dev' };
  }
  const filePath = join(REPORTS_DIR, `${date}-en.md`);

  let source: string;
  try {
    source = readFileSync(filePath, 'utf-8');
  } catch {
    return { title: 'Report Not Found — AimFast.Dev' };
  }

  const { fm } = parseFrontmatterWithBody(source);
  const title = fm.title || `Daily Report — ${date}`;
  const canonicalUrl = `https://www.aimfast.dev/reports/${date}/`;
  const zhUrl = `https://www.aimfast.dev/reports/${date}/zh/`;
  const hasZh = hasZhVersion(date);

  const alternates: Record<string, unknown> = {
    canonical: canonicalUrl,
    languages: hasZh
      ? { en: canonicalUrl, 'zh-CN': zhUrl }
      : { en: canonicalUrl },
  };

  return {
    title: `${title} — AimFast.Dev`,
    description: fm.summary || `Daily signal intelligence report for ${date}. Product opportunities, trend analysis, and buildable insights for indie developers.`,
    robots: { index: true, follow: true },
    alternates,
    openGraph: {
      title: `${title} — AimFast.Dev`,
      description: fm.summary || `Daily signal intelligence report for ${date}.`,
      type: 'article',
      publishedTime: fm.date || date,
      url: canonicalUrl,
      siteName: 'AimFast.Dev',
      locale: 'en',
      images: [
        {
          url: 'https://www.aimfast.dev/og-reports.png',
          width: 1200,
          height: 630,
          alt: 'AimFast.Dev — Daily Signal Intelligence',
        },
      ],
    },
    twitter: {
      card: 'summary_large_image',
      title: `${title} — AimFast.Dev`,
      description: fm.summary || 'Daily product opportunities from 30+ signal sources.',
      images: ['https://www.aimfast.dev/og-reports.png'],
    },
  };
}

export function generateStaticParams() {
  return getReportDates().map((date) => ({ date }));
}

export default async function ReportPage({
  params,
}: {
  params: Promise<{ date: string }>;
}) {
  const { date } = await params;
  if (!isValidPathSegment(date)) {
    return (
      <main className="container" style={{ padding: 'var(--space-10) 0', textAlign: 'center' as const }}>
        <h1>Invalid Request</h1>
        <p><a href="/">Back to home</a></p>
      </main>
    );
  }
  const filePath = join(REPORTS_DIR, `${date}-en.md`);

  let source: string;
  try {
    source = readFileSync(filePath, 'utf-8');
  } catch {
    return (
      <main className="container" style={{ padding: 'var(--space-10) 0', textAlign: 'center' as const }}>
        <h1>Report Not Found</h1>
        <p>No report exists for {date}.</p>
        <p><a href="/">Back to home</a></p>
      </main>
    );
  }

  const { fm, body } = parseFrontmatterWithBody(source);
  const title = fm.title || `Daily Report — ${date}`;
  const canonicalUrl = `https://www.aimfast.dev/reports/${date}/`;
  const zhUrl = `https://www.aimfast.dev/reports/${date}/zh/`;
  const hasZh = hasZhVersion(date);

  const { content } = await compileMDX({
    source: body,
    options: { parseFrontmatter: false },
  });

  const jsonLd = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: 'Trends', item: 'https://www.aimfast.dev/' },
          { '@type': 'ListItem', position: 2, name: 'Reports', item: 'https://www.aimfast.dev/reports/' },
          { '@type': 'ListItem', position: 3, name: title, item: canonicalUrl },
        ],
      },
      {
        '@type': 'Article',
        headline: title,
        datePublished: `${fm.date || date}T00:00:00+08:00`,
        description: fm.summary || `Daily signal intelligence report for ${date}.`,
        author: { '@type': 'Organization', name: 'AimFast.Dev' },
        publisher: { '@type': 'Organization', name: 'AimFast.Dev' },
        inLanguage: 'en',
        translationOfWork: hasZh ? { '@type': 'CreativeWork', '@id': zhUrl, inLanguage: 'zh-CN' } : undefined,
        url: canonicalUrl,
        mainEntityOfPage: { '@type': 'WebPage', '@id': canonicalUrl },
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
        <nav aria-label="Breadcrumb" style={{ padding: 'var(--space-4) 0', fontSize: '0.875rem' }}>
          <ol style={{ listStyle: 'none', display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)', margin: 0, padding: 0 }}>
            <li><a href="/">Trends</a></li>
            <li aria-hidden="true">/</li>
            <li><a href="/reports/">Reports</a></li>
            <li aria-hidden="true">/</li>
            <li>{date}</li>
          </ol>
        </nav>
        <article style={{ padding: 'var(--space-4) 0 var(--space-10)' }}>
          <header style={{ marginBottom: 'var(--space-8)' }}>
            <h1 style={{ fontSize: 'var(--text-3xl)', fontWeight: 700, overflowWrap: 'break-word', wordBreak: 'break-word' }}>{title}</h1>
            {fm.date && (
              <time dateTime={fm.date} style={{ color: 'var(--color-muted)', fontSize: '0.875rem' }}>
                {fm.date}
              </time>
            )}
            {fm.summary && (
              <p style={{ fontSize: 'var(--text-lg)', color: 'var(--color-muted)', marginTop: 'var(--space-4)' }}>
                {fm.summary}
              </p>
            )}
            {hasZh && (
              <div style={{ marginTop: 'var(--space-4)', fontSize: '0.875rem' }}>
                <a href={zhUrl} hrefLang="zh-CN" rel="alternate" style={{ minHeight: 44, display: 'inline-flex', alignItems: 'center' }}>
                  阅读中文版 →
                </a>
              </div>
            )}
          </header>
          <div className="report-content">
            {content}
          </div>
        </article>
        <footer className="site-footer" style={{ borderTop: '1px solid var(--color-border)', paddingTop: 'var(--space-6)', marginTop: 'var(--space-10)' }}>
          <p style={{ fontSize: '0.875rem', color: 'var(--color-muted)' }}>
            &copy; {new Date().getFullYear()} AimFast.Dev ·{' '}
            <a href="/">Trends</a> · <a href="/dashboard/">Dashboard</a> · <a href="/pricing/">Pricing</a>
            {hasZh && (
              <> · <a href={zhUrl}>中文版</a></>
            )}
          </p>
        </footer>
      </main>
    </>
  );
}
