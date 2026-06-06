# SEO Implementation Plan — KAKAOPC 情报科

## Problem
Daily generated content (report.md, article.md) lives in `daily/` (gitignored) and is only surfaced via the dashboard (noindex). Google sees none of it.

## Goal
Every daily report and article (Chinese + English) becomes a crawlable, indexable HTML page with full SEO metadata.

---

## Phase 1: Report Pages

### 1a. Create `app/reports/[date]/page.tsx`
- `generateStaticParams` reads from `content/reports/*.md` (committed directory)
- `generateMetadata` extracts title/description/date from frontmatter → OG tags + Twitter card
- Renders markdown to HTML with proper semantic structure
- JSON-LD `Article` structured data
- `<link rel="alternate" hreflang="en">` to English version
- `<html lang="zh-CN">` for Chinese, `lang="en"` for English

### 1b. Create `app/reports/[date]/en/page.tsx`
- Same as above but reads `content/reports/<date>-en.md`
- hreflang pointing back to Chinese version
- `lang="en"`

### 1c. Modify `generate_report.py`
- After writing `daily/<date>/report.md`, also write `content/reports/<date>.md` with frontmatter:
  ```yaml
  ---
  title: <extracted from report H1 or date>
  date: 2026-05-29
  summary: <first 150 chars of report as meta description>
  ---
  ```
- Same for English version → `content/reports/<date>-en.md`

### 1d. Commit `content/reports/` directory (not gitignored)

---

## Phase 2: Article Pages

### 2a. Enhance existing `app/articles/[slug]/page.tsx`
- Add JSON-LD `Article` structured data
- Add OG image (default shared image)
- Add hreflang `<link rel="alternate">` for English version
- Add breadcrumb structured data

### 2b. Create `app/articles/[slug]/en/page.tsx`
- English version of article detail page
- Reads from `content/articles/<slug>-en.mdx`
- hreflang back to Chinese version

### 2c. Modify `generate_article.py`
- After writing `daily/<date>/article.md`, also write `content/articles/<date-slug>.mdx` with proper frontmatter
- After translation, write `content/articles/<date-slug>-en.mdx`

---

## Phase 3: Technical SEO

### 3a. Auto-generate sitemap.xml
- Python script in pipeline (or Next.js build script) generates `public/sitemap.xml`
- Includes: homepage, all reports (zh + en), all articles (zh + en), landing pages
- Updates on every dashboard generation

### 3b. Add JSON-LD to layout
- `Organization` and `WebSite` schema in `app/layout.tsx`
- `BreadcrumbList` in article/report pages

### 3c. Create default OG image
- SVG-based OG image at `public/og-image.svg`
- Used as fallback for all pages without custom images

### 3d. Fix lang attribute
- Reports/Articles pages set `<html lang="zh-CN">` or `"en"` dynamically
- Homepage stays `lang="en"`

### 3e. Update robots.txt
- Keep `/dashboard/` noindex
- Everything else indexable

---

## Phase 4: Content-Level SEO

### 4a. Update `generate_report.py` prompt
- Add SEO constraints to system prompt:
  - Compelling title (50-60 chars, includes keywords)
  - First paragraph = meta description (150-160 chars)
  - Proper heading hierarchy (H1 → H2, never skip H3 without H2)
  - Use descriptive link text (not "click here")
  - Include target keywords naturally in the first 200 words

### 4b. Update `generate_article.py` prompt
- Same SEO constraints
- Article slug generation (English, kebab-case, <60 chars)
- Excerpt generation for meta description

### 4c. Update `translate_content.py` prompt
- Add SEO translation rules:
  - Keep translated titles at 50-60 chars
  - Translate meta description to 150-160 chars
  - Preserve heading hierarchy
  - Translate keywords naturally

---

## Phase 5: Pipeline Integration

### 5a. Update `daily_run.sh` / `daily_run.ps1`
- Add step after translation: "Generate SEO Content Files" (runs new script)
- Add step: "Generate Sitemap" (updates sitemap.xml)
- Commit: git add content/reports/ content/articles/ public/sitemap.xml

### 5b. Backfill historical content
- Run pipeline once for all existing `daily/` dates to generate `content/` files
- Commit all to update sitemap

---

## Files Changed (Estimate)
| File | Change |
|------|--------|
| `app/reports/[date]/page.tsx` | **NEW** |
| `app/reports/[date]/en/page.tsx` | **NEW** |
| `app/reports/[date]/layout.tsx` | **NEW** (lang switching) |
| `app/articles/[slug]/en/page.tsx` | **NEW** |
| `app/layout.tsx` | Add JSON-LD, OG image |
| `app/page.tsx` | Add JSON-LD WebSite |
| `app/articles/[slug]/page.tsx` | Add JSON-LD, OG image, hreflang |
| `scripts/generate_report.py` | Add content/ output + SEO prompt |
| `scripts/generate_article.py` | Add content/ output + SEO prompt |
| `scripts/translate_content.py` | Add SEO translation rules |
| `scripts/generate_seo_files.py` | **NEW** (content/ + sitemap) |
| `scripts/daily_run.sh` | Add SEO steps |
| `scripts/daily_run.ps1` | Add SEO steps |
| `public/sitemap.xml` | Auto-generated |
| `public/robots.txt` | Minor update |
| `next.config.ts` | No change needed |

---

## Verification
1. `npm run build` succeeds (static export with new routes)
2. Each report URL returns proper HTML with metadata
3. Sitemap lists all URLs
4. Google Search Console can fetch and render
5. hreflang tags validate correctly
