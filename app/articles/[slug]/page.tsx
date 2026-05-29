import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { compileMDX } from 'next-mdx-remote/rsc';
import type { Metadata } from 'next';

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
  const filePath = join(process.cwd(), 'content', 'articles', `${slug}.mdx`);
  let source: string;
  try {
    source = readFileSync(filePath, 'utf-8');
  } catch {
    return { title: 'Article Not Found — KAKAOPC Intel' };
  }

  const fm = parseFrontmatter(source);
  const title = fm.title || slug;
  const canonicalUrl = `https://aimfast.dev/articles/${slug}/`;

  const alternates: Record<string, string> = { canonical: canonicalUrl };
  if (hasEnglishVersion(slug)) {
    alternates['languages'] = { en: `https://aimfast.dev/articles/${slug}/en/` } as any;
  }

  return {
    title: `${title} — KAKAOPC Intel`,
    description: fm.summary || 'Deep-dive signal analysis for indie developers.',
    robots: { index: true, follow: true },
    alternates,
    openGraph: {
      title: `${title} — KAKAOPC Intel`,
      description: fm.summary || 'Deep-dive signal analysis for indie developers.',
      type: 'article',
      publishedTime: fm.date || undefined,
      url: canonicalUrl,
      siteName: 'KAKAOPC Intel',
      locale: 'zh_CN',
      images: [
        {
          url: 'https://aimfast.dev/og-image.png',
          width: 1200,
          height: 630,
          alt: 'KAKAOPC Intel — Daily Signal Intelligence',
        },
      ],
    },
    twitter: {
      card: 'summary_large_image',
      title: `${title} — KAKAOPC Intel`,
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
  const content = source.replace(/^---\n[\s\S]*?\n---\n?/, '');
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
    author: { '@type': 'Organization', name: 'KAKAOPC Intel' },
    publisher: { '@type': 'Organization', name: 'KAKAOPC Intel' },
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
            &copy; {new Date().getFullYear()} KAKAOPC Intel ·{' '}
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
