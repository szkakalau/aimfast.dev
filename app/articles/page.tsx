import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import type { Metadata } from 'next';
import { parseFrontmatter } from '@/lib/frontmatter';

const ARTICLES_DIR = join(process.cwd(), 'content', 'articles');

export const metadata: Metadata = {
  title: 'Planet Articles — AimFast.Dev',
  description:
    'Deep-dive signal analysis articles. Each article unpacks a product opportunity with evidence, plain-English translation, and actionable steps.',
  robots: { index: true, follow: true },
  alternates: { canonical: 'https://www.aimfast.dev/articles/' },
  openGraph: {
    title: 'Planet Articles — AimFast.Dev',
    description: 'Deep-dive product opportunity analysis for indie developers.',
    url: 'https://www.aimfast.dev/articles/',
    siteName: 'AimFast.Dev',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Planet Articles — AimFast.Dev',
    description: 'Deep-dive product opportunity analysis for indie developers.',
  },
};

interface ArticleMeta {
  slug: string;
  title: string;
  date: string;
  summary: string;
  hasEn: boolean;
}

function getArticles(): ArticleMeta[] {
  try {
    const files = readdirSync(ARTICLES_DIR).filter((f) => f.endsWith('.mdx'));
    const zhFiles = files.filter((f) => !f.includes('-en'));
    const enSet = new Set(
      files.filter((f) => f.includes('-en')).map((f) => f.replace('-en.mdx', ''))
    );

    return zhFiles
      .map((f) => {
        const slug = f.replace('.mdx', '');
        const hasEn = enSet.has(slug);
        const filePath = join(ARTICLES_DIR, f);
        const source = readFileSync(filePath, 'utf-8');

        const fm = parseFrontmatter(source);
        return {
          slug,
          title: fm.title || slug,
          date: fm.date || '',
          summary: fm.summary || '',
          hasEn,
        };
      })
      .sort((a, b) => b.date.localeCompare(a.date)); // newest first
  } catch {
    return [];
  }
}

export default function ArticlesIndexPage() {
  const articles = getArticles();

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'CollectionPage',
    name: 'Planet Articles — AimFast.Dev',
    description: 'Deep-dive signal analysis articles for indie developers.',
    url: 'https://www.aimfast.dev/articles/',
    mainEntity: {
      '@type': 'ItemList',
      itemListElement: articles.map((a, i) => ({
        '@type': 'ListItem',
        position: i + 1,
        url: `https://www.aimfast.dev/articles/${a.slug}/`,
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
        <header style={{ padding: 'var(--space-8) 0 var(--space-4)' }}>
          <h1>Planet Articles</h1>
          <p className="hero-desc" style={{ maxWidth: '520px', margin: 0 }}>
            Deep-dive analysis unpacking one product opportunity per article — evidence,
            plain-English translation, and actionable next steps.
          </p>
          <nav style={{ marginTop: 'var(--space-3)', fontSize: '0.85rem' }}>
            <a href="/">← Home</a>
            {' · '}
            <a href="/reports/">Daily Reports</a>
          </nav>
        </header>

        {articles.length === 0 ? (
          <p style={{ padding: 'var(--space-8) 0', textAlign: 'center', color: 'var(--color-text-muted)' }}>
            No articles yet. Check back soon.
          </p>
        ) : (
          <ul className="article-list" style={{ listStyle: 'none', padding: 0, paddingBottom: 'var(--space-10)' }}>
            {articles.map((a) => (
              <li key={a.slug} className="article-list-item">
                <a href={`/articles/${a.slug}/`} className="article-list-link">
                  <time dateTime={a.date} className="article-list-date">
                    {a.date || '—'}
                  </time>
                  <h2 className="article-list-title">{a.title}</h2>
                  {a.summary && <p className="article-list-summary">{a.summary}</p>}
                </a>
                {a.hasEn && (
                  <span className="article-list-lang">
                    <a href={`/articles/${a.slug}/en/`} hrefLang="en">
                      EN →
                    </a>
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}

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
