"""
SEO 文件生成器
将 daily/ 中的报告和文章转化为 content/ 中的可索引文件，
并自动更新 sitemap.xml。
"""
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAILY_DIR = ROOT / "daily"
CONTENT_REPORTS = ROOT / "content" / "reports"
CONTENT_ARTICLES = ROOT / "content" / "articles"
TRACKING_PATH = ROOT / "tracking" / "opportunities.json"
PUBLIC = ROOT / "public"
SITEMAP_PATH = PUBLIC / "sitemap.xml"
LP_INDEX_PATH = PUBLIC / "lp-index.json"

TZ_SHANGHAI = timezone(timedelta(hours=8))
BASE_URL = "https://www.aimfast.dev"


def extract_title_and_summary(md_text: str, max_summary: int = 160) -> tuple[str, str]:
    """Extract H1 title and first substantial paragraph from markdown."""
    title = ""
    summary = ""

    # Extract first H1 heading
    h1_match = re.search(r'^#\s+(.+)$', md_text, re.MULTILINE)
    if h1_match:
        title = h1_match.group(1).strip()
        # Remove common emojis from title for SEO
        title = re.sub(r'[📝🎯📊📖🔍🛰️🏭📈🎬🔗🔥⚠️✅❌⭐]', '', title).strip()

    # Extract first substantial paragraph (skip headings, separators, empty lines)
    lines = md_text.split('\n')
    in_content = False
    for line in lines:
        stripped = line.strip()
        # Skip YAML frontmatter, headings, horizontal rules, blockquotes, code blocks
        if stripped in ('---', '') or stripped.startswith('```'):
            continue
        if re.match(r'^#{1,6}\s', stripped):
            in_content = True
            continue
        if in_content and len(stripped) > 60:
            # Found a substantial paragraph
            summary = stripped
            # Clean markdown formatting
            summary = re.sub(r'\*\*(.+?)\*\*', r'\1', summary)
            summary = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', summary)
            summary = re.sub(r'[*_`]', '', summary)
            break
        if len(stripped) > 0:
            in_content = True

    if not title:
        title = "Daily Report"
    if not summary:
        summary = "Daily signal intelligence report with product opportunities and trend analysis for indie developers."
    if len(summary) > max_summary:
        summary = summary[:max_summary - 3].rsplit(' ', 1)[0] + "..."

    return title, summary


def escape_mdx_comparison_operators(content: str) -> str:
    """Escape < and > when used as comparison operators to prevent MDX from
    parsing them as JSX tags. Only escapes patterns that are definitely
    comparisons, not legitimate HTML/MDX tags (tags start with a letter).

    Examples: <5 → &lt;5, <30% → &lt;30%, <$10 → &lt;$10, >$0.01 → &gt;$0.01
    """
    # < followed by digit → comparison operator
    content = re.sub(r'<(\d)', r'&lt;\1', content)
    # < followed by $ → comparison operator (e.g., <$10)
    content = re.sub(r'<(\$)', r'&lt;\1', content)
    # > followed by $ → comparison operator (e.g., >$0.01)
    content = re.sub(r'>(\$)', r'&gt;\1', content)
    return content


def wrap_frontmatter(content: str, title: str, date: str, summary: str) -> str:
    """Add YAML frontmatter to markdown content."""
    # Escape quotes in title and summary
    title_escaped = title.replace('"', '\\"')
    summary_escaped = summary.replace('"', '\\"')
    fm = f'''---
title: "{title_escaped}"
date: {date}
summary: "{summary_escaped}"
---

'''
    return fm + content


def process_reports(date_str: str) -> int:
    """Generate content/reports/<date>.md and <date>-en.md from daily/. Returns count."""
    CONTENT_REPORTS.mkdir(parents=True, exist_ok=True)
    count = 0

    zh_src = DAILY_DIR / date_str / "report.md"
    zh_dst = CONTENT_REPORTS / f"{date_str}.md"
    if zh_src.exists():
        content = zh_src.read_text(encoding="utf-8")
        content = escape_mdx_comparison_operators(content)
        title, summary = extract_title_and_summary(content)
        wrapped = wrap_frontmatter(content, title, date_str, summary)
        zh_dst.write_text(wrapped, encoding="utf-8")
        print(f"  [SEO] report.md → {zh_dst}")
        count += 1

    en_src = DAILY_DIR / date_str / "report-en.md"
    en_dst = CONTENT_REPORTS / f"{date_str}-en.md"
    if en_src.exists():
        content = en_src.read_text(encoding="utf-8")
        content = escape_mdx_comparison_operators(content)
        title, summary = extract_title_and_summary(content)
        wrapped = wrap_frontmatter(content, title, date_str, summary)
        en_dst.write_text(wrapped, encoding="utf-8")
        print(f"  [SEO] report-en.md → {en_dst}")
        count += 1

    return count


def generate_slug(date_str: str, md_text: str) -> str:
    """Generate an English kebab-case slug from article content."""
    # Try to extract a meaningful slug from the title
    h1_match = re.search(r'^#\s+(.+)$', md_text, re.MULTILINE)
    if h1_match:
        title = h1_match.group(1).strip()
        # If title contains English words, extract them
        eng_words = re.findall(r'[A-Za-z0-9]+', title)
        if len(eng_words) >= 2:
            slug = '-'.join(eng_words[:8]).lower()
            if len(slug) <= 60:
                return slug
    # Fallback: date-based slug
    return f"daily-signal-{date_str}"


def process_articles(date_str: str) -> int:
    """Generate content/articles/<slug>.mdx from daily/article.md. Returns count."""
    CONTENT_ARTICLES.mkdir(parents=True, exist_ok=True)
    count = 0

    zh_src = DAILY_DIR / date_str / "article.md"
    if zh_src.exists():
        content = zh_src.read_text(encoding="utf-8")
        content = escape_mdx_comparison_operators(content)
        title, summary = extract_title_and_summary(content)
        slug = generate_slug(date_str, content)
        wrapped = wrap_frontmatter(content, title, date_str, summary)
        dst = CONTENT_ARTICLES / f"{slug}.mdx"
        dst.write_text(wrapped, encoding="utf-8")
        print(f"  [SEO] article.md → {dst}")
        count += 1

    en_src = DAILY_DIR / date_str / "article-en.md"
    if en_src.exists():
        content = en_src.read_text(encoding="utf-8")
        content = escape_mdx_comparison_operators(content)
        title, summary = extract_title_and_summary(content)
        # For English version, use same slug with -en suffix
        zh_content = ""
        zh_src_path = DAILY_DIR / date_str / "article.md"
        if zh_src_path.exists():
            zh_content = zh_src_path.read_text(encoding="utf-8")
        slug = generate_slug(date_str, zh_content if zh_content else content)
        wrapped = wrap_frontmatter(content, title, date_str, summary)
        dst = CONTENT_ARTICLES / f"{slug}-en.mdx"
        dst.write_text(wrapped, encoding="utf-8")
        print(f"  [SEO] article-en.md → {dst}")
        count += 1

    return count


def generate_lp_index() -> int:
    """Generate public/lp-index.json from tracking data. Returns LP count."""
    PUBLIC.mkdir(parents=True, exist_ok=True)

    live_lps = []
    if TRACKING_PATH.exists():
        tracking = json.loads(TRACKING_PATH.read_text(encoding="utf-8"))
        for opp in tracking.get("opportunities", []):
            if opp.get("lp_status") == "live":
                live_lps.append({
                    "id": opp.get("id", ""),
                    "date": opp.get("date", ""),
                    "opportunity": opp.get("opportunity", ""),
                    "url": opp.get("landing_page_url", ""),
                    "score": opp.get("score", 0),
                    "buyer": opp.get("buyer", ""),
                    "current_status": opp.get("current_status", "monitoring"),
                })

    LP_INDEX_PATH.write_text(json.dumps(live_lps, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  [SEO] lp-index.json → {len(live_lps)} live LPs → {LP_INDEX_PATH}")

    # Also generate the LP sitemap data for use in generate_sitemap()
    return len(live_lps)


def generate_sitemap() -> int:
    """Regenerate sitemap.xml from content/ directories. Returns URL count."""
    urls = []

    # Homepage
    urls.append({
        'loc': f'{BASE_URL}/',
        'changefreq': 'daily',
        'priority': '1.0',
    })

    # Reports index
    urls.append({
        'loc': f'{BASE_URL}/reports/',
        'changefreq': 'daily',
        'priority': '0.9',
    })

    # Articles index
    urls.append({
        'loc': f'{BASE_URL}/articles/',
        'changefreq': 'daily',
        'priority': '0.9',
    })

    # Dashboard
    urls.append({
        'loc': f'{BASE_URL}/dashboard/',
        'changefreq': 'daily',
        'priority': '0.8',
    })

    # Reports
    if CONTENT_REPORTS.exists():
        for f in sorted(CONTENT_REPORTS.glob('*.md')):
            if '-en' in f.name:
                continue
            date = f.stem
            en_file = CONTENT_REPORTS / f"{date}-en.md"
            has_en = en_file.exists()

            urls.append({
                'loc': f'{BASE_URL}/reports/{date}/',
                'lastmod': date,
                'changefreq': 'weekly',
                'priority': '0.8',
                'alternates': {
                    'zh-CN': f'{BASE_URL}/reports/{date}/',
                    'en': f'{BASE_URL}/reports/{date}/en/',
                } if has_en else None,
            })
            if has_en:
                urls.append({
                    'loc': f'{BASE_URL}/reports/{date}/en/',
                    'lastmod': date,
                    'changefreq': 'weekly',
                    'priority': '0.8',
                    'alternates': {
                        'en': f'{BASE_URL}/reports/{date}/en/',
                        'zh-CN': f'{BASE_URL}/reports/{date}/',
                    },
                })

    # Articles
    if CONTENT_ARTICLES.exists():
        seen_slugs = set()
        for f in sorted(CONTENT_ARTICLES.glob('*.mdx')):
            if '-en' in f.name:
                continue
            slug = f.stem
            seen_slugs.add(slug)
            en_file = CONTENT_ARTICLES / f"{slug}-en.mdx"
            has_en = en_file.exists()

            # Extract date from frontmatter for lastmod
            lastmod = ""
            try:
                raw = f.read_text(encoding='utf-8')[:500]
                date_match = re.search(r'date:\s*([\d-]+)', raw)
                if date_match:
                    lastmod = date_match.group(1)
            except Exception:
                pass

            urls.append({
                'loc': f'{BASE_URL}/articles/{slug}/',
                'lastmod': lastmod,
                'changefreq': 'weekly',
                'priority': '0.8',
                'alternates': {
                    'zh-CN': f'{BASE_URL}/articles/{slug}/',
                    'en': f'{BASE_URL}/articles/{slug}/en/',
                } if has_en else None,
            })
            if has_en:
                urls.append({
                    'loc': f'{BASE_URL}/articles/{slug}/en/',
                    'lastmod': lastmod,
                    'changefreq': 'weekly',
                    'priority': '0.8',
                    'alternates': {
                        'en': f'{BASE_URL}/articles/{slug}/en/',
                        'zh-CN': f'{BASE_URL}/articles/{slug}/',
                    },
                })

    # Landing Pages
    if TRACKING_PATH.exists():
        tracking = json.loads(TRACKING_PATH.read_text(encoding="utf-8"))
        for opp in tracking.get("opportunities", []):
            if opp.get("lp_status") != "live":
                continue
            lp_url = opp.get("landing_page_url", "")
            if not lp_url:
                continue
            slug = lp_url.rstrip("/").split("/")[-1] if "/" in lp_url else ""
            if not slug:
                continue

            # Active monitoring LPs get daily + high priority; archived get monthly
            status = opp.get("current_status", "monitoring")
            if status in ("monitoring", "building"):
                changefreq = "daily"
                priority = "0.9"
            elif status == "archived":
                changefreq = "monthly"
                priority = "0.5"
            else:
                changefreq = "weekly"
                priority = "0.8"

            urls.append({
                'loc': lp_url + "/",
                'lastmod': opp.get("date", ""),
                'changefreq': changefreq,
                'priority': priority,
            })

    # Generate XML
    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ]

    for u in urls:
        xml_lines.append('  <url>')
        xml_lines.append(f'    <loc>{u["loc"]}</loc>')
        if u.get('lastmod'):
            xml_lines.append(f'    <lastmod>{u["lastmod"]}</lastmod>')
        xml_lines.append(f'    <changefreq>{u.get("changefreq", "weekly")}</changefreq>')
        xml_lines.append(f'    <priority>{u.get("priority", "0.8")}</priority>')
        if u.get('alternates'):
            for lang, href in u['alternates'].items():
                xml_lines.append(f'    <xhtml:link rel="alternate" hreflang="{lang}" href="{href}"/>')
        xml_lines.append('  </url>')

    xml_lines.append('</urlset>')
    xml_lines.append('')  # trailing newline

    sitemap_xml = '\n'.join(xml_lines)
    SITEMAP_PATH.write_text(sitemap_xml, encoding='utf-8')
    print(f"\n  [SEO] Sitemap generated: {len(urls)} URLs → {SITEMAP_PATH}")

    return len(urls)


def run(date_str: str | None = None) -> dict:
    """Main entry point: generate all SEO files for a given date."""
    date = date_str or datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")

    print(f"\n{'='*50}")
    print(f"[SEO] Content & Sitemap Generation — {date}")
    print(f"{'='*50}")

    date_dir = DAILY_DIR / date
    if not date_dir.exists():
        print(f"[SEO] No daily dir for {date}, skipping")
        return {"date": date, "reports": 0, "articles": 0, "sitemap_urls": 0}

    report_count = process_reports(date)
    article_count = process_articles(date)
    lp_count = generate_lp_index()
    sitemap_urls = generate_sitemap()

    print(f"\n[SEO] Done: {report_count} reports + {article_count} articles + {lp_count} LPs → sitemap ({sitemap_urls} URLs)")

    return {
        "date": date,
        "reports": report_count,
        "articles": article_count,
        "lps": lp_count,
        "sitemap_urls": sitemap_urls,
    }


if __name__ == "__main__":
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    date_arg = sys.argv[1] if len(sys.argv) > 1 else today
    result = run(date_arg)
    total = result["reports"] + result["articles"]
    if total == 0:
        print("\n[SEO] WARN: No content files generated -- check if daily/ source files exist")
    else:
        print(f"\n[SEO] OK: {total} content files + sitemap ready for deployment")
