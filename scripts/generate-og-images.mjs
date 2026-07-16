/**
 * Generate per-section and per-trend OG images from SVG templates.
 * Uses `sharp` to convert SVGs to 1200×630 PNGs.
 *
 * Output:
 *   public/og-home.png       — homepage / root layout
 *   public/og-reports.png    — reports index & detail
 *   public/og-articles.png   — articles index & detail
 *   public/og-pricing.png    — pricing page
 *   public/og-dashboard.png  — dashboard
 *   public/og/trends/{slug}.png — per-trend detail pages
 *
 * Usage: node scripts/generate-og-images.mjs
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import sharp from 'sharp';

const PUBLIC = join(process.cwd(), 'public');
const OG_TRENDS_DIR = join(PUBLIC, 'og', 'trends');
const TREND_TERMS_PATH = join(process.cwd(), 'tracking', 'trend_terms.json');

/* ── SVG Template ── */

function ogSvg({ title, subtitle, tagline, accentLabel, domain = 'aimfast.dev' }) {
  const lines = Array.isArray(title) ? title : [title];
  const titleY = lines.length === 1 ? 310 : 280;
  const lineHeight = 58;

  const titleEls = lines
    .map(
      (line, i) =>
        `<text x="110" y="${titleY + i * lineHeight}" font-family="'Space Grotesk', 'DM Sans', sans-serif" font-size="48" font-weight="700" fill="#ffffff" letter-spacing="-0.5">${escapeXml(line)}</text>`,
    )
    .join('\n');

  return `<svg width="1200" height="630" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0a0a0a"/>
      <stop offset="100%" style="stop-color:#1a1a2e"/>
    </linearGradient>
    <linearGradient id="accent" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#6366f1"/>
      <stop offset="100%" style="stop-color:#06b6d4"/>
    </linearGradient>
  </defs>

  <rect width="1200" height="630" fill="url(#bg)"/>

  <!-- Grid -->
  <g opacity="0.03" stroke="#ffffff">
    ${Array.from({ length: 13 }, (_, i) => `<line x1="0" y1="${i * 50}" x2="1200" y2="${i * 50}" stroke-width="1"/>`).join('\n')}
  </g>

  <!-- Accent line -->
  <rect x="80" y="200" width="4" height="230" rx="2" fill="url(#accent)"/>

  <!-- Brand wordmark -->
  <text x="110" y="145" font-family="'Space Grotesk', 'DM Sans', sans-serif" font-size="22" font-weight="700" fill="#6366f1" letter-spacing="6">
    AIMFAST.DEV
  </text>

  ${accentLabel ? `<text x="110" y="235" font-family="'DM Sans', sans-serif" font-size="16" font-weight="600" fill="#06b6d4" letter-spacing="2">${escapeXml(accentLabel)}</text>` : ''}

  <!-- Title -->
  ${titleEls}

  <!-- Subtitle -->
  ${subtitle ? `<text x="110" y="${titleY + lines.length * lineHeight + 36}" font-family="'DM Sans', sans-serif" font-size="20" fill="#a0a0b8">${escapeXml(subtitle)}</text>` : ''}

  <!-- URL -->
  <text x="110" y="530" font-family="'JetBrains Mono', monospace" font-size="18" fill="#6366f1">${escapeXml(domain)}</text>

  <!-- Tagline -->
  ${tagline ? `<text x="110" y="560" font-family="'DM Sans', sans-serif" font-size="16" fill="#6b7280">${escapeXml(tagline)}</text>` : ''}
</svg>`;
}

function escapeXml(s) {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

/* ── SVG → PNG ── */

async function svgToPng(svg, outPath) {
  const dir = dirname(outPath);
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
  await sharp(Buffer.from(svg)).png().toFile(outPath);
  console.log(`  ✓ ${outPath}`);
}

/* ── Section-level images ── */

const SECTIONS = [
  {
    file: 'og-home.png',
    title: ['Discover What\'s Emerging', 'Before Everyone Else'],
    subtitle: 'Daily tracking of new tech terms, concepts & market signals',
    tagline: 'Free trend discovery — no signup required',
  },
  {
    file: 'og-reports.png',
    title: 'Daily Signal Intelligence',
    subtitle: 'Product opportunities, trend analysis & buildable insights',
    accentLabel: 'REPORTS',
    tagline: 'Signal Intelligence for Indie Developers',
  },
  {
    file: 'og-articles.png',
    title: 'Deep-Dive Signal Analysis',
    subtitle: 'Evidence-backed product opportunity breakdowns',
    accentLabel: 'ARTICLES',
    tagline: 'Signal Intelligence for Indie Developers',
  },
  {
    file: 'og-pricing.png',
    title: 'One Plan, Everything Included',
    subtitle: 'Starter $19/mo · Builder $39/mo · Team $79/mo',
    accentLabel: 'PRICING',
    tagline: 'Signal Intelligence for Indie Developers',
  },
  {
    file: 'og-dashboard.png',
    title: 'Your Market Intelligence Hub',
    subtitle: 'Monitor trends, get daily briefs',
    accentLabel: 'DASHBOARD',
    tagline: 'Signal Intelligence for Indie Developers',
  },
];

/* ── Trend detail images ── */

function trendOgSvg(term) {
  const maxTitleLen = 45;
  const title =
    term.canonical.length > maxTitleLen
      ? term.canonical.slice(0, maxTitleLen - 1) + '…'
      : term.canonical;

  const stageMap = {
    nascent: 'Nascent (0–7d)',
    emergent: 'Emergent (8–30d)',
    validating: 'Validating (31–90d)',
    rising: 'Rising (90d+)',
  };
  const stage = stageMap[term.stage] || term.stage;
  const subtitle = `${stage}  ·  Score ${term.score}/100  ·  ${term.source_count} sources`;

  return ogSvg({
    title: [title],
    subtitle,
    accentLabel: 'TREND REPORT',
    tagline: `Category: ${term.category}  ·  ${term.total_mentions} mentions`,
    domain: 'aimfast.dev',
  });
}

/* ── Main ── */

async function main() {
  console.log('\n🔮 Generating OG images...\n');

  // Section-level images
  console.log('─ Section OG images ─');
  for (const s of SECTIONS) {
    const svg = ogSvg({
      title: s.title,
      subtitle: s.subtitle,
      tagline: s.tagline,
      accentLabel: s.accentLabel,
    });
    await svgToPng(svg, join(PUBLIC, s.file));
  }

  // Per-trend images
  console.log('\n─ Trend detail OG images ─');
  if (!existsSync(TREND_TERMS_PATH)) {
    console.log('  ⚠ tracking/trend_terms.json not found — skipping trend OGs');
  } else {
    const data = JSON.parse(readFileSync(TREND_TERMS_PATH, 'utf-8'));
    const terms = data.terms || [];
    console.log(`  Found ${terms.length} terms`);

    let count = 0;
    for (const term of terms) {
      const slug = term.id.replace('trend-', '');
      const svg = trendOgSvg(term);
      await svgToPng(svg, join(OG_TRENDS_DIR, `${slug}.png`));
      count++;
    }
    console.log(`  ✓ ${count} trend OG images generated`);
  }

  // Also update the canonical og-image.png (for backward compat / fallback)
  console.log('\n─ Canonical fallback ─');
  const fallbackSvg = ogSvg({
    title: ['Discover What\'s Emerging', 'Before Everyone Else'],
    subtitle: 'Daily tracking of new tech terms, concepts & market signals',
    tagline: 'Signal Intelligence for Indie Developers',
  });
  await svgToPng(fallbackSvg, join(PUBLIC, 'og-image.png'));

  console.log('\n✅ All OG images generated.\n');
}

main().catch((err) => {
  console.error('OG image generation failed:', err);
  process.exit(1);
});
