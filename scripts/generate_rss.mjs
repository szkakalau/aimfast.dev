/**
 * RSS feed generator — reads content/articles/*.mdx and writes public/articles/rss.xml.
 * Run before `next build` to include in static export.
 */
import { readFileSync, readdirSync, writeFileSync, mkdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..');
const ARTICLES_DIR = join(ROOT, 'content', 'articles');
const PUBLIC_DIR = join(ROOT, 'public', 'articles');
const SITE_URL = 'https://aimfast.dev';

function parseFrontmatter(source) {
  const fm = {};
  const match = source.match(/^---\n([\s\S]*?)\n---/);
  if (!match) return fm;
  for (const line of match[1].split('\n')) {
    const idx = line.indexOf(':');
    if (idx > 0) {
      const key = line.slice(0, idx).trim();
      const val = line.slice(idx + 1).trim();
      if (key === 'title') fm.title = val;
      if (key === 'date') fm.date = val;
      if (key === 'summary') fm.summary = val;
    }
  }
  return fm;
}

function escXml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

let files;
try {
  files = readdirSync(ARTICLES_DIR).filter((f) => f.endsWith('.mdx'));
} catch {
  console.log('[RSS] No articles found. Skipping.');
  process.exit(0);
}

const articles = [];
for (const file of files) {
  const slug = file.replace(/\.mdx$/, '');
  const raw = readFileSync(join(ARTICLES_DIR, file), 'utf-8');
  const fm = parseFrontmatter(raw);
  articles.push({
    slug,
    title: fm.title || slug,
    date: fm.date || '2026-01-01',
    summary: fm.summary || '',
  });
}

articles.sort((a, b) => b.date.localeCompare(a.date));

const items = articles
  .map(
    (a) => `  <item>
    <title>${escXml(a.title)}</title>
    <link>${SITE_URL}/articles/${a.slug}/</link>
    <description>${escXml(a.summary)}</description>
    <pubDate>${new Date(a.date).toUTCString()}</pubDate>
    <guid>${SITE_URL}/articles/${a.slug}/</guid>
  </item>`
  )
  .join('\n');

const rss = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>AimFast.Dev — Articles</title>
  <link>${SITE_URL}/articles/</link>
  <description>Deep-dive signal analysis for indie developers. Weekly articles translating cross-platform signals into buildable opportunities.</description>
  <language>en</language>
  <lastBuildDate>${new Date().toUTCString()}</lastBuildDate>
  <atom:link href="${SITE_URL}/articles/rss.xml" rel="self" type="application/rss+xml"/>
${items}
</channel>
</rss>`;

mkdirSync(PUBLIC_DIR, { recursive: true });
writeFileSync(join(PUBLIC_DIR, 'rss.xml'), rss, 'utf-8');
console.log(`[RSS] Generated with ${articles.length} articles → public/articles/rss.xml`);
