import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { compileMDX } from 'next-mdx-remote/rsc';
import type { Metadata } from 'next';
import { isValidPathSegment } from '@/lib/path-security';
import { parseFrontmatter, extractBody } from '@/lib/frontmatter';

const ARTICLES_DIR = join(process.cwd(), 'content', 'articles');

function getZhArticles(): { slug: string }[] {
  try {
    return readdirSync(ARTICLES_DIR)
      .filter((f) => f.endsWith('.mdx') && !f.includes('-en'))
      .map((f) => ({ slug: f.replace(/\.mdx$/, '') }));
  } catch {
    return [];
  }
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  if (!isValidPathSegment(slug)) {
    return { title: 'Invalid Request — AimFast.Dev' };
  }
  const filePath = join(ARTICLES_DIR, `${slug}.mdx`);

  let source: string;
  try {
    source = readFileSync(filePath, 'utf-8');
  } catch {
    return { title: 'Article Not Found — AimFast.Dev' };
  }

  const fm = parseFrontmatter(source);
  const title = fm.title || slug;
  const canonicalUrl = `https://www.aimfast.dev/articles/${slug}/zh/`;
  const enUrl = `https://www.aimfast.dev/articles/${slug}/`;

  return {
    title: `${title} — AimFast.Dev`,
    description: fm.summary || '面向独立开发者的深度信号分析。',
    robots: { index: true, follow: true },
    alternates: {
      canonical: canonicalUrl,
      languages: { 'zh-CN': canonicalUrl, en: enUrl },
    },
    openGraph: {
      title: `${title} — AimFast.Dev`,
      description: fm.summary || '面向独立开发者的深度信号分析。',
      type: 'article',
      publishedTime: fm.date || undefined,
      url: canonicalUrl,
      siteName: 'AimFast.Dev',
      locale: 'zh-CN',
      images: [
        {
          url: 'https://www.aimfast.dev/og-articles.png',
          width: 1200,
          height: 630,
          alt: 'AimFast.Dev — Daily Signal Intelligence',
        },
      ],
    },
    twitter: {
      card: 'summary_large_image',
      title: `${title} — AimFast.Dev`,
      description: fm.summary || '面向独立开发者的深度信号分析。',
      images: ['https://www.aimfast.dev/og-articles.png'],
    },
  };
}

export function generateStaticParams() {
  return getZhArticles().map(({ slug }) => ({ slug }));
}

export default async function ArticleZhPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  if (!isValidPathSegment(slug)) {
    return (
      <main className="container">
        <article className="article" style={{ padding: 'var(--space-10) 0', textAlign: 'center' as const }}>
          <h1>Invalid Request</h1>
          <p><a href="/">Back to home</a></p>
        </article>
      </main>
    );
  }
  const filePath = join(ARTICLES_DIR, `${slug}.mdx`);

  let source: string;
  try {
    source = readFileSync(filePath, 'utf-8');
  } catch {
    return (
      <main className="container">
        <article className="article" style={{ padding: 'var(--space-10) 0', textAlign: 'center' as const }}>
          <h1>Article Not Found</h1>
          <p>
            No Chinese version exists for this article.{' '}
            <a href={`/articles/${slug}/`}>View English version</a>
          </p>
          <p><a href="/">Back to home</a></p>
        </article>
      </main>
    );
  }

  const frontmatter = parseFrontmatter(source);
  // Strip leading H1 to avoid duplicate heading (page header already renders H1)
  let content = extractBody(source).replace(/^# .+\n+/, '');
  const canonicalUrl = `https://www.aimfast.dev/articles/${slug}/zh/`;
  const enUrl = `https://www.aimfast.dev/articles/${slug}/`;

  const { content: mdxContent } = await compileMDX({
    source: content,
    options: { parseFrontmatter: false },
  });

  const jsonLd = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: 'Trends', item: 'https://www.aimfast.dev/' },
          { '@type': 'ListItem', position: 2, name: 'Articles', item: 'https://www.aimfast.dev/articles/' },
          { '@type': 'ListItem', position: 3, name: frontmatter.title || slug, item: canonicalUrl },
        ],
      },
      {
        '@type': 'Article',
        headline: frontmatter.title || slug,
        datePublished: frontmatter.date ? `${frontmatter.date}T00:00:00+08:00` : undefined,
        description: frontmatter.summary || '',
        author: { '@type': 'Organization', name: 'AimFast.Dev' },
        publisher: { '@type': 'Organization', name: 'AimFast.Dev' },
        inLanguage: 'zh-CN',
        translationOfWork: { '@type': 'CreativeWork', '@id': enUrl, inLanguage: 'en' },
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
        <article className="article" style={{ padding: 'var(--space-8) 0' }}>
          <header style={{ marginBottom: 'var(--space-6)' }}>
            <h1>{frontmatter.title || slug}</h1>
            {frontmatter.date && (
              <time dateTime={frontmatter.date} className="article-meta-date">
                {frontmatter.date}
              </time>
            )}
            {frontmatter.summary && (
              <p className="article-meta-summary">{frontmatter.summary}</p>
            )}
            <div style={{ marginTop: 'var(--space-3)', fontSize: '0.875rem' }}>
              <a href={enUrl} hrefLang="en" rel="alternate">
                Read in English →
              </a>
            </div>
          </header>
          {mdxContent}
        </article>
        <footer className="site-footer">
          <p>
            &copy; {new Date().getFullYear()} AimFast.Dev ·{' '}
            <a href="/">Trends</a> · <a href="/dashboard/">Dashboard</a> · <a href="/pricing/">Pricing</a> ·{' '}
            <a href={enUrl}>English version</a>
          </p>
        </footer>
      </main>
    </>
  );
}
