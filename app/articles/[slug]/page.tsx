import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { compileMDX } from 'next-mdx-remote/rsc';
import type { Metadata } from 'next';
import { isValidPathSegment } from '@/lib/path-security';
import { parseFrontmatter, extractBody } from '@/lib/frontmatter';

function getArticleSlugs(): string[] {
  const dir = join(process.cwd(), 'content', 'articles');
  try {
    return readdirSync(dir)
      .filter((f) => f.endsWith('.mdx') && !f.includes('-en'))
      .map((f) => f.replace(/\.mdx$/, ''));
  } catch {
    return [];
  }
}

function hasEnglishVersion(slug: string): boolean {
  try {
    const enPath = join(process.cwd(), 'content', 'articles', `${slug}-en.mdx`);
    return readFileSync(enPath, 'utf-8') !== undefined;
  } catch {
    return false;
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
  const filePath = join(process.cwd(), 'content', 'articles', `${slug}.mdx`);
  let source: string;
  try {
    source = readFileSync(filePath, 'utf-8');
  } catch {
    return { title: 'Article Not Found — AimFast.Dev' };
  }

  const fm = parseFrontmatter(source);
  const title = fm.title || slug;
  const canonicalUrl = `https://aimfast.dev/articles/${slug}/`;

  const alternates: Record<string, string> = { canonical: canonicalUrl };
  if (hasEnglishVersion(slug)) {
    alternates['languages'] = { en: `https://aimfast.dev/articles/${slug}/en/` } as any;
  }

  return {
    title: `${title} — AimFast.Dev`,
    description: fm.summary || 'Deep-dive signal analysis for indie developers.',
    robots: { index: true, follow: true },
    alternates,
    openGraph: {
      title: `${title} — AimFast.Dev`,
      description: fm.summary || 'Deep-dive signal analysis for indie developers.',
      type: 'article',
      publishedTime: fm.date || undefined,
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
      description: fm.summary || 'Deep-dive signal analysis for indie developers.',
      images: ['https://aimfast.dev/og-image.png'],
    },
  };
}

export function generateStaticParams() {
  return getArticleSlugs().map((slug) => ({ slug }));
}

export default async function ArticlePage({
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
  const filePath = join(process.cwd(), 'content', 'articles', `${slug}.mdx`);

  let source: string;
  try {
    source = readFileSync(filePath, 'utf-8');
  } catch {
    return (
      <main className="container">
        <article className="article" style={{ padding: 'var(--space-10) 0', textAlign: 'center' as const }}>
          <h1>Article Not Found</h1>
          <p><a href="/">Back to home</a></p>
        </article>
      </main>
    );
  }

  // Parse frontmatter
  const frontmatter = parseFrontmatter(source);
  const content = extractBody(source);
  const canonicalUrl = `https://aimfast.dev/articles/${slug}/`;
  const enUrl = `https://aimfast.dev/articles/${slug}/en/`;
  const hasEn = hasEnglishVersion(slug);

  const { content: mdxContent } = await compileMDX({
    source: content,
    options: { parseFrontmatter: false },
  });

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: frontmatter.title || slug,
    datePublished: frontmatter.date || undefined,
    description: frontmatter.summary || '',
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
            {hasEn && (
              <div style={{ marginTop: 'var(--space-3)', fontSize: '0.875rem' }}>
                <a href={enUrl} hrefLang="en" rel="alternate">
                  Read in English →
                </a>
              </div>
            )}
          </header>
          {mdxContent}
        </article>
        <footer className="site-footer">
          <p>
            &copy; {new Date().getFullYear()} AimFast.Dev ·{' '}
            <a href="/">Home</a> · <a href="/dashboard/">Dashboard</a>
            {hasEn && (
              <>
                {' '}· <a href={enUrl}>English version</a>
              </>
            )}
          </p>
        </footer>
      </main>
    </>
  );
}
