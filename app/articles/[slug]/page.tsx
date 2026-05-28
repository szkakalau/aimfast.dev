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
    return readdirSync(dir).filter((f) => f.endsWith('.mdx')).map((f) => f.replace(/\.mdx$/, ''));
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
  const filePath = join(process.cwd(), 'content', 'articles', `${slug}.mdx`);
  let source: string;
  try {
    source = readFileSync(filePath, 'utf-8');
  } catch {
    return { title: 'Article Not Found — KAKAOPC Intel' };
  }

  const fm = parseFrontmatter(source);
  const title = fm.title || slug;
  return {
    title: `${title} — KAKAOPC Intel`,
    description: fm.summary || 'Deep-dive signal analysis for indie developers.',
    openGraph: {
      title: `${title} — KAKAOPC Intel`,
      description: fm.summary || 'Deep-dive signal analysis for indie developers.',
      type: 'article',
      publishedTime: fm.date || undefined,
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

  const { content: mdxContent } = await compileMDX({
    source: content,
    options: { parseFrontmatter: false },
  });

  return (
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
        </header>
        {mdxContent}
      </article>
      <footer className="site-footer">
        <p>
          &copy; {new Date().getFullYear()} KAKAOPC Intel ·{' '}
          <a href="/">Home</a> · <a href="/dashboard/">Dashboard</a>
        </p>
      </footer>
    </main>
  );
}
