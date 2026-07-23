"""
Tests for sitemap generation (scripts/generate_seo_files.py).
Run: python -m pytest tests/test_generate_seo.py -v
"""
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.generate_seo_files import generate_sitemap

# ── Helpers ──

def _build_sitemap_xml() -> str:
    """Build sitemap XML and return as string."""
    count = generate_sitemap()
    sitemap_path = Path(__file__).resolve().parent.parent / "public" / "sitemap.xml"
    xml = sitemap_path.read_text(encoding="utf-8")
    return xml


def _extract_locs(xml: str) -> list[str]:
    """Extract all <loc> URLs from sitemap XML."""
    return re.findall(r"<loc>(https://[^<]+)</loc>", xml)


# ── Tests ──

class TestSitemapStructure:
    """Structural correctness of generated sitemap."""

    def test_xml_valid(self):
        """Sitemap is valid XML with correct namespaces."""
        xml = _build_sitemap_xml()
        assert '<?xml version="1.0" encoding="UTF-8"?>' in xml
        assert 'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"' in xml
        assert 'xmlns:xhtml="http://www.w3.org/1999/xhtml"' in xml
        assert xml.startswith("<?xml")
        assert xml.endswith("</urlset>\n")

    def test_url_count_reasonable(self):
        """Sitemap has a reasonable number of URLs (200-1000)."""
        xml = _build_sitemap_xml()
        locs = _extract_locs(xml)
        assert 200 <= len(locs) <= 1000, f"Expected 200-1000 URLs, got {len(locs)}"

    def test_no_duplicate_locs(self):
        """No duplicate <loc> entries."""
        xml = _build_sitemap_xml()
        locs = _extract_locs(xml)
        assert len(locs) == len(set(locs)), f"Found {len(locs) - len(set(locs))} duplicate URLs"


class TestSitemapKeyUrls:
    """Critical URLs are present or absent as expected."""

    @staticmethod
    def _locs() -> list[str]:
        return _extract_locs(_build_sitemap_xml())

    def test_homepage_present(self):
        locs = self._locs()
        assert "https://www.aimfast.dev/" in locs

    def test_zh_homepage_present(self):
        locs = self._locs()
        assert "https://www.aimfast.dev/zh/" in locs

    def test_pricing_en_present(self):
        locs = self._locs()
        assert "https://www.aimfast.dev/pricing/" in locs

    def test_pricing_zh_present(self):
        locs = self._locs()
        assert "https://www.aimfast.dev/pricing/zh/" in locs

    def test_dashboard_present(self):
        locs = self._locs()
        assert "https://www.aimfast.dev/dashboard/" in locs

    def test_reports_index_present(self):
        locs = self._locs()
        assert "https://www.aimfast.dev/reports/" in locs

    def test_articles_index_present(self):
        locs = self._locs()
        assert "https://www.aimfast.dev/articles/" in locs

    def test_trends_listing_absent(self):
        """IA restructure: trends listing moved to homepage, must not be in sitemap."""
        locs = self._locs()
        assert "https://www.aimfast.dev/trends/" not in locs, (
            "/trends/ found in sitemap — listing page was moved to homepage"
        )

    def test_trends_detail_pages_present(self):
        """Trend detail pages (e.g. /trends/claude-agent-sdk/) still in sitemap."""
        locs = self._locs()
        detail_locs = [l for l in locs if re.match(r"https://www\.aimfast\.dev/trends/[^/]+/$", l)]
        assert len(detail_locs) > 40, f"Expected 40+ trend detail pages, got {len(detail_locs)}"

    def test_trends_zh_detail_pages_present(self):
        """ZH trend detail pages (e.g. /trends/claude-agent-sdk/zh/) still in sitemap."""
        locs = self._locs()
        zh_detail_locs = [l for l in locs if re.match(r"https://www\.aimfast\.dev/trends/[^/]+/zh/$", l)]
        assert len(zh_detail_locs) > 40, f"Expected 40+ ZH trend detail pages, got {len(zh_detail_locs)}"

    def test_hreflang_alternates_present(self):
        """Key pages have hreflang alternates."""
        xml = _build_sitemap_xml()
        assert 'hreflang="en"' in xml
        assert 'hreflang="zh-CN"' in xml
