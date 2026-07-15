import type { Metadata, Viewport } from 'next';
import { Fira_Sans, Fira_Code, JetBrains_Mono } from 'next/font/google';
import LangToggle from '../components/LangToggle';
import './globals.css';

const firaSans = Fira_Sans({
  subsets: ['latin'],
  weight: ['300', '400', '500', '600', '700', '800'],
  variable: '--font-fira-sans',
  display: 'swap',
});

const firaCode = Fira_Code({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-fira-code',
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  variable: '--font-jetbrains-mono',
  display: 'swap',
});

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
  themeColor: '#0a0a0a',
};

export const metadata: Metadata = {
  title: 'AimFast.Dev — Free Trend Discovery & Market Intelligence',
  description:
    'Discover emerging tech terms before they trend. Free daily tracking across 11+ sources. Dashboard membership unlocks daily product opportunities — what to build, who will pay, and how much to charge.',
  robots: { index: true, follow: true },
  metadataBase: new URL('https://www.aimfast.dev'),
  alternates: {
    canonical: 'https://www.aimfast.dev/',
    languages: {
      en: 'https://www.aimfast.dev/',
      'zh-CN': 'https://www.aimfast.dev/zh/',
    },
  },
  openGraph: {
    type: 'website',
    title: 'AimFast.Dev — Free Trend Discovery & Market Intelligence',
    description:
      'Discover emerging tech terms before they trend. Free daily tracking. Dashboard: one validated product opportunity every morning.',
    url: 'https://www.aimfast.dev/',
    siteName: 'AimFast.Dev',
    locale: 'en',
    images: [
      {
        url: 'https://www.aimfast.dev/og-home.png',
        width: 1200,
        height: 630,
        alt: 'AimFast.Dev — Trend Discovery & Market Intelligence',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'AimFast.Dev — Free Trend Discovery',
    description: 'Discover emerging tech terms before they trend. Free daily tracking. Dashboard: daily product opportunities.',
    images: ['https://www.aimfast.dev/og-home.png'],
  },
};

const jsonLd = {
  '@context': 'https://schema.org',
  '@graph': [
    {
      '@type': 'Organization',
      name: 'AimFast.Dev',
      url: 'https://www.aimfast.dev/',
      description:
        'Daily market intelligence for indie builders. AI scans 11 sources to deliver one validated product opportunity every morning — what to build, who will pay, and how much to charge.',
      foundingDate: '2026-01-01',
      sameAs: [
        'https://github.com/szkakalau/aimfast.dev',
        'https://twitter.com/aimfastdev',
      ],
    },
    {
      '@type': 'WebSite',
      name: 'AimFast.Dev',
      url: 'https://www.aimfast.dev/',
      description:
        'Daily market intelligence for indie builders. Product opportunities, competitor tracking, trend analysis from 11 global sources.',
    },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${firaSans.variable} ${firaCode.variable} ${jetbrainsMono.variable}`}>
      <head>
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
        <link rel="manifest" href="/manifest.json" />
        <link rel="alternate" type="application/rss+xml" title="AimFast.Dev Articles RSS" href="/articles/rss.xml" />
        <link rel="alternate" type="application/rss+xml" title="AimFast.Dev 文章 RSS (中文)" href="/articles/rss-zh.xml" />
        <link rel="alternate" type="application/rss+xml" title="AimFast.Dev Reports RSS" href="/reports/rss.xml" />
        <link rel="llms.txt" href="/llms.txt" />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
        <link rel="alternate" hrefLang="en" href="https://www.aimfast.dev/" />
        <link rel="alternate" hrefLang="zh-CN" href="https://www.aimfast.dev/zh/" />
        <link rel="alternate" hrefLang="x-default" href="https://www.aimfast.dev/" />
      </head>
      <body>
        <a className="skip-link" href="#main-content">Skip to content</a>
        <nav className="site-nav" aria-label="Main navigation">
          <div className="site-nav-inner">
            <a href="/" className="site-nav-logo" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)' }}>
              <svg className="icon icon-accent" viewBox="0 0 24 24" aria-hidden="true" width="20" height="20" fill="none">
                <circle cx="12" cy="12" r="4" fill="currentColor" />
                <path d="M4.93 4.93a10 10 0 0 1 14.14 0M4.93 19.07a10 10 0 0 0 14.14 0" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
              </svg>
              AimFast.Dev
            </a>
            <input type="checkbox" id="nav-toggle" className="nav-toggle-input" aria-hidden="true" />
            <label htmlFor="nav-toggle" className="nav-toggle-label" aria-label="Toggle navigation menu">
              <span className="nav-toggle-icon" />
            </label>
            <div className="site-nav-links">
              <a href="/">Trends</a>
              <a href="/dashboard/">Dashboard</a>
              <a href="/pricing/">Pricing</a>
              <LangToggle />
            </div>
            <label htmlFor="nav-toggle" className="nav-overlay" aria-hidden="true" />
          </div>
        </nav>
        <span id="main-content" tabIndex={-1} />
        {children}
        {/* Close mobile nav when a link is clicked */}
        {/* Set lang attribute based on path prefix — dev mode fallback (build uses fix-en-lang.mjs) */}
        <script dangerouslySetInnerHTML={{ __html: `
          (function(){var p=location.pathname;document.documentElement.lang=p.startsWith('/zh')||p.startsWith('/zh/')?'zh-CN':'en';})();
        `}} />
        <script dangerouslySetInnerHTML={{ __html: `
          (function(){
            var toggle = document.getElementById('nav-toggle');
            var links = document.querySelectorAll('.site-nav-links a');
            for (var i = 0; i < links.length; i++) {
              links[i].addEventListener('click', function(){ toggle.checked = false; });
            }
            /* Fallback body scroll lock — only for browsers without :has() support */
            var supportsHas = false;
            try { document.querySelector(':has(*)'); supportsHas = true; } catch(e) {}
            if (!supportsHas) {
              toggle.addEventListener('change', function(){
                document.body.style.overflow = toggle.checked ? 'hidden' : '';
              });
            }
          })();
        `}} />
      </body>
    </html>
  );
}
