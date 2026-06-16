import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { compileMDX } from 'next-mdx-remote/rsc';
import type { Metadata } from 'next';

const ARTICLES_DIR = join(process.cwd(), 'content', 'articles');

function parseFrontmatter(source: string): { title?: string; date?: string; summary?: string } {
  const frontmatter: { title?: string; date?: string; summary?: string } = {};
  const fmMatch = source.match(/^---\n([\s\S]*?)\n---/);
  if (!fmMatch) return frontmatter;
  const lines = fmMatch[1].split('\n');
  for (const line of lines) {
    const colonIdx = line.indexOf(':');
    if (colonIdx > 0) {
      const key = line.slice(0, colonIdx).trim();
      const val = line.slice(colonIdx + 1).trim();
      if (key === 'title') frontmatter.title = val;
      if (key === 'date') frontmatter.date = val;
      if (key === 'summary') frontmatter.summary = val;
    }
  }
  return frontmatter;
}

function getEnglishArticles(): { slug: string; hasEn: boolean }[] {
  try {
    return readdirSync(ARTICLES_DIR)
      .filter((f) => f.endsWith('-en.mdx'))
      .map((f) => ({ slug: f.replace(/-en\.mdx$/, ''), hasEn: true }));
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
  const filePath = join(ARTICLES_DIR, `${slug}-en.mdx`);

  let source: string;
  try {
    source = readFileSync(filePath, 'utf-8');
  } catch {
    return { title: 'Article Not Found — AimFast.Dev' };
  }

  const fm = parseFrontmatter(source);
  const title = fm.title || slug;
  const canonicalUrl = `https://aimfast.dev/articles/${slug}/en/`;
  const zhUrl = `https://aimfast.dev/articles/${slug}/`;

  return {
    title: `${title} — AimFast.Dev`,
    description: fm.summary || 'Deep-dive signal analysis for indie developers.',
    robots: { index: true, follow: true },
    alternates: {
      canonical: canonicalUrl,
      languages: { 'zh-CN': zhUrl },
    },
    openGraph: {
      title: `${title} — AimFast.Dev`,
      description: fm.summary || 'Deep-dive signal analysis for indie developers.',
      type: 'article',
      publishedTime: fm.date || undefined,
      url: canonicalUrl,
      siteName: 'AimFast.Dev',
      locale: 'en_US',
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
  return getEnglishArticles().map(({ slug }) => ({ slug }));
}

export default async function ArticleEnPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const filePath = join(ARTICLES_DIR, `${slug}-en.mdx`);

  let source: string;
  try {
    source = readFileSync(filePath, 'utf-8');
  } catch {
    return (
      <main className="container">
        <article className="article" style={{ padding: 'var(--space-10) 0', textAlign: 'center' as const }}>
          <h1>Article Not Found</h1>
          <p>
            No English version exists for this article.{' '}
            <a href={`/articles/${slug}/`}>View Chinese version</a>
          </p>
          <p><a href="/">Back to home</a></p>
        </article>
      </main>
    );
  }

  const frontmatter = parseFrontmatter(source);
  const content = source.replace(/^---\n[\s\S]*?\n---\n?/, '');
  const canonicalUrl = `https://aimfast.dev/articles/${slug}/en/`;
  const zhUrl = `https://aimfast.dev/articles/${slug}/`;

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
    inLanguage: 'en',
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
            <div style={{ marginTop: 'var(--space-3)', fontSize: '0.875rem' }}>
              <a href={zhUrl} hrefLang="zh-CN" rel="alternate">
                阅读中文版 →
              </a>
            </div>
          </header>
          {mdxContent}
        </article>
        <footer className="site-footer">
          <p>
            &copy; {new Date().getFullYear()} AimFast.Dev ·{' '}
            <a href="/">Home</a> · <a href="/dashboard/">Dashboard</a> ·{' '}
            <a href={zhUrl}>中文版</a>
          </p>
        </footer>
      </main>
    </>
  );
}
