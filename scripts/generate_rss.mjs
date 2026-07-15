/**
 * RSS feed generator — reads content/articles/*.mdx and writes two feeds:
 *   public/articles/rss.xml     — English articles (slugs ending in -en)
 *   public/articles/rss-zh.xml  — Chinese articles (original language)
 *
 * Filters out entries with empty summaries and placeholder dates.
 * Run before `next build` to include in static export.
 */
import { readFileSync, readdirSync, writeFileSync, mkdirSync, statSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..');
const ARTICLES_DIR = join(ROOT, 'content', 'articles');
const PUBLIC_DIR = join(ROOT, 'public', 'articles');
const SITE_URL = 'https://www.aimfast.dev';

const PLACEHOLDER_DATE = '2026-01-01';

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

const enArticles = [];
const zhArticles = [];
let skippedEmpty = 0;
let skippedPlaceholderDate = 0;

for (const file of files) {
  const slug = file.replace(/\.mdx$/, '');
  const raw = readFileSync(join(ARTICLES_DIR, file), 'utf-8');
  const fm = parseFrontmatter(raw);

  // Skip entries with empty summaries
  if (!fm.summary || fm.summary.trim() === '') {
    skippedEmpty++;
    continue;
  }

  let date = fm.date;
  // Use file mtime as fallback for placeholder dates
  if (!date || date === PLACEHOLDER_DATE) {
    try {
      const stat = statSync(join(ARTICLES_DIR, file));
      date = stat.mtime.toISOString().slice(0, 10);
      skippedPlaceholderDate++;
    } catch {
      date = PLACEHOLDER_DATE;
    }
  }

  const article = {
    slug,
    title: fm.title || slug,
    date,
    summary: fm.summary,
  };

  // Split by language: -en suffix → English, everything else → Chinese
  if (slug.endsWith('-en')) {
    enArticles.push(article);
  } else {
    zhArticles.push(article);
  }
}

function generateFeed(articles, language, filename) {
  articles.sort((a, b) => b.date.localeCompare(a.date));

  const items = articles
    .map(
      (a) => `    <item>
      <title>${escXml(a.title)}</title>
      <link>${SITE_URL}/articles/${a.slug}/</link>
      <description>${escXml(a.summary)}</description>
      <pubDate>${new Date(a.date + 'T00:00:00+08:00').toUTCString()}</pubDate>
      <guid>${SITE_URL}/articles/${a.slug}/</guid>
    </item>`,
    )
    .join('\n');

  return `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>AimFast.Dev — Articles${language === 'en' ? '' : ' (中文)'}</title>
    <link>${SITE_URL}/articles/</link>
    <description>Deep-dive signal analysis for indie developers. ${language === 'en' ? 'Weekly articles translating cross-platform signals into buildable opportunities.' : '深度信号分析文章，将跨平台信号转化为可执行的产品机会。'}</description>
    <language>${language === 'en' ? 'en' : 'zh-CN'}</language>
    <lastBuildDate>${new Date().toUTCString()}</lastBuildDate>
    <atom:link href="${SITE_URL}/articles/${filename}" rel="self" type="application/rss+xml"/>
${items}
  </channel>
</rss>`;
}

mkdirSync(PUBLIC_DIR, { recursive: true });

const enXml = generateFeed(enArticles, 'en', 'rss.xml');
writeFileSync(join(PUBLIC_DIR, 'rss.xml'), enXml, 'utf-8');
console.log(`[RSS] English: ${enArticles.length} articles → public/articles/rss.xml`);

const zhXml = generateFeed(zhArticles, 'zh-CN', 'rss-zh.xml');
writeFileSync(join(PUBLIC_DIR, 'rss-zh.xml'), zhXml, 'utf-8');
console.log(`[RSS] Chinese: ${zhArticles.length} articles → public/articles/rss-zh.xml`);

if (skippedEmpty > 0) console.log(`[RSS] Skipped ${skippedEmpty} article(s) with empty summary`);
if (skippedPlaceholderDate > 0) console.log(`[RSS] Fixed ${skippedPlaceholderDate} placeholder date(s) using file mtime`);
