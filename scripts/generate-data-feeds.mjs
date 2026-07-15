/**
 * Generate machine-readable data feeds for AI crawlers and RSS consumers.
 * Outputs:
 *   public/trends.json    — all trend terms as JSON (AI crawler friendly)
 *   public/reports/rss.xml — RSS feed of daily reports
 *
 * Usage: node scripts/generate-data-feeds.mjs
 */
import { readFileSync, readdirSync, writeFileSync, mkdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..');
const PUBLIC = join(ROOT, 'public');
const SITE_URL = 'https://www.aimfast.dev';

function escXml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

/* ── trends.json ── */

try {
  const trendRaw = readFileSync(join(ROOT, 'tracking', 'trend_terms.json'), 'utf-8');
  const trendData = JSON.parse(trendRaw);

  const simplified = {
    updated_at: trendData.updated_at,
    total: (trendData.terms || []).length,
    terms: (trendData.terms || []).map((t) => ({
      id: t.id.replace('trend-', ''),
      canonical: t.canonical,
      canonical_zh: t.canonical_zh || null,
      stage: t.stage,
      score: t.score,
      category: t.category,
      source_count: t.source_count,
      total_mentions: t.total_mentions,
      growth_pct: t.growth_pct,
      first_seen: t.first_seen,
      summary_en: t.summary_en || null,
      summary_zh: t.summary_zh || null,
      suggested_products: t.suggested_products || [],
      opportunity_score: t.opportunity_score || null,
      revenue_potential: t.revenue_potential || null,
      url: `${SITE_URL}/trends/${t.id.replace('trend-', '')}/`,
    })),
  };

  writeFileSync(join(PUBLIC, 'trends.json'), JSON.stringify(simplified, null, 2), 'utf-8');
  console.log(`[data-feeds] trends.json: ${simplified.terms.length} terms → public/trends.json`);
} catch (err) {
  console.log(`[data-feeds] trends.json: skipped (${err.message})`);
}

/* ── reports RSS ── */

const REPORTS_DIR = join(ROOT, 'content', 'reports');

try {
  const files = readdirSync(REPORTS_DIR).filter((f) => f.endsWith('.md') && !f.includes('-en'));
  const reports = [];

  for (const file of files) {
    const date = file.replace('.md', '');
    const raw = readFileSync(join(REPORTS_DIR, file), 'utf-8');
    const fmMatch = raw.match(/^---\n([\s\S]*?)\n---/);
    let title = `Daily Report — ${date}`;
    let summary = '';
    if (fmMatch) {
      for (const line of fmMatch[1].split('\n')) {
        const idx = line.indexOf(':');
        if (idx > 0) {
          const key = line.slice(0, idx).trim();
          const val = line.slice(idx + 1).trim();
          if (key === 'title') title = val;
          if (key === 'summary') summary = val;
        }
      }
    }
    reports.push({ date, title, summary });
  }

  reports.sort((a, b) => b.date.localeCompare(a.date));

  const items = reports
    .map(
      (r) => `    <item>
      <title>${escXml(r.title)}</title>
      <link>${SITE_URL}/reports/${r.date}/</link>
      <description>${escXml(r.summary || `Daily signal intelligence report for ${r.date}`)}</description>
      <pubDate>${new Date(r.date + 'T00:00:00+08:00').toUTCString()}</pubDate>
      <guid>${SITE_URL}/reports/${r.date}/</guid>
    </item>`,
    )
    .join('\n');

  const rss = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>AimFast.Dev — Daily Reports</title>
    <link>${SITE_URL}/reports/</link>
    <description>Daily signal intelligence reports. Product opportunities, trend analysis, and buildable insights for indie developers.</description>
    <language>zh-CN</language>
    <lastBuildDate>${new Date().toUTCString()}</lastBuildDate>
    <atom:link href="${SITE_URL}/reports/rss.xml" rel="self" type="application/rss+xml"/>
${items}
  </channel>
</rss>`;

  mkdirSync(join(PUBLIC, 'reports'), { recursive: true });
  writeFileSync(join(PUBLIC, 'reports', 'rss.xml'), rss, 'utf-8');
  console.log(`[data-feeds] reports RSS: ${reports.length} reports → public/reports/rss.xml`);
} catch (err) {
  console.log(`[data-feeds] reports RSS: skipped (${err.message})`);
}

console.log('[data-feeds] Done.');
