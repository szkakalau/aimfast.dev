import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { compileMDX } from 'next-mdx-remote/rsc';
import type { Metadata } from 'next';

const REPORTS_DIR = join(process.cwd(), 'content', 'reports');

interface ReportFrontmatter {
  title?: string;
  date?: string;
  summary?: string;
}

function parseFrontmatter(source: string): { fm: ReportFrontmatter; body: string } {
  const fm: ReportFrontmatter = {};
  let body = source;
  const fmMatch = source.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?/);
  if (fmMatch) {
    const lines = fmMatch[1].split('\n');
    for (const line of lines) {
      const colonIdx = line.indexOf(':');
      if (colonIdx > 0) {
        const key = line.slice(0, colonIdx).trim();
        let val = line.slice(colonIdx + 1).trim();
        if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
          val = val.slice(1, -1);
        }
        if (key === 'title') fm.title = val;
        if (key === 'date') fm.date = val;
        if (key === 'summary') fm.summary = val;
      }
    }
    body = source.slice(fmMatch[0].length);
  }
  return { fm, body };
}

function getReportDates(): string[] {
  try {
    return readdirSync(REPORTS_DIR)
      .filter((f) => f.endsWith('.md') && !f.includes('-en'))
      .map((f) => f.replace(/\.md$/, ''));
  } catch {
    return [];
  }
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ date: string }>;
}): Promise<Metadata> {
  const { date } = await params;
  const filePath = join(REPORTS_DIR, `${date}.md`);

  let source: string;
  try {
    source = readFileSync(filePath, 'utf-8');
  } catch {
    return { title: 'Report Not Found — AimFast.Dev' };
  }

  const { fm } = parseFrontmatter(source);
  const title = fm.title || `Daily Report — ${date}`;
  const canonicalUrl = `https://aimfast.dev/reports/${date}/`;
  const enUrl = `https://aimfast.dev/reports/${date}/en/`;

  return {
    title: `${title} — AimFast.Dev`,
    description: fm.summary || `Daily signal intelligence report for ${date}. Product opportunities, trend analysis, and buildable insights for indie developers.`,
    robots: { index: true, follow: true },
    alternates: {
      canonical: canonicalUrl,
      languages: { en: enUrl },
    },
    openGraph: {
      title: `${title} — AimFast.Dev`,
      description: fm.summary || `Daily signal intelligence report for ${date}.`,
      type: 'article',
      publishedTime: fm.date || date,
      url: canonicalUrl,
      siteName: 'AimFast.Dev',
      locale: 'zh_CN',
      images: [
        {
          url: 'https://aimfast.dev/og-image.png',
          width: 1200,
          height: 630,
          alt: 'AimFast.Dev — Daily Signal Intelligence',
        },
      ],
    },
    twitter: {
      card: 'summary_large_image',
      title: `${title} — AimFast.Dev`,
      description: fm.summary || 'Daily product opportunities from 14 signal sources.',
      images: ['https://aimfast.dev/og-image.png'],
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
  const filePath = join(REPORTS_DIR, `${date}.md`);

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

  const { fm, body } = parseFrontmatter(source);
  const title = fm.title || `Daily Report — ${date}`;
  const canonicalUrl = `https://aimfast.dev/reports/${date}/`;
  const enUrl = `https://aimfast.dev/reports/${date}/en/`;

  const { content } = await compileMDX({
    source: body,
    options: { parseFrontmatter: false },
  });

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: title,
    datePublished: fm.date || date,
    description: fm.summary || '',
    author: { '@type': 'Organization', name: 'AimFast.Dev' },
    publisher: { '@type': 'Organization', name: 'AimFast.Dev' },
    inLanguage: 'zh-CN',
    url: canonicalUrl,
    mainEntityOfPage: { '@type': 'WebPage', '@id': canonicalUrl },
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <main className="container">
        <nav aria-label="Breadcrumb" style={{ padding: 'var(--space-4) 0', fontSize: '0.875rem' }}>
          <ol style={{ listStyle: 'none', display: 'flex', gap: 'var(--space-2)', margin: 0, padding: 0 }}>
            <li><a href="/">Home</a></li>
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
            <div style={{ marginTop: 'var(--space-4)', fontSize: '0.875rem' }}>
              <a href={enUrl} hrefLang="en" rel="alternate">
                Read in English →
              </a>
            </div>
          </header>
          <div className="report-content">
            {content}
          </div>
        </article>
        <footer className="site-footer" style={{ borderTop: '1px solid var(--color-border)', paddingTop: 'var(--space-6)', marginTop: 'var(--space-10)' }}>
          <p style={{ fontSize: '0.875rem', color: 'var(--color-muted)' }}>
            &copy; {new Date().getFullYear()} AimFast.Dev ·{' '}
            <a href="/">Home</a> · <a href="/dashboard/">Dashboard</a> ·{' '}
            <a href={`/reports/${date}/en/`}>English version</a>
          </p>
        </footer>
      </main>
    </>
  );
}
