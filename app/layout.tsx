import type { Metadata, Viewport } from 'next';
import LangToggle from '../components/LangToggle';
import './globals.css';

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
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
    images: [
      {
        url: 'https://www.aimfast.dev/og-image.png',
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
    images: ['https://www.aimfast.dev/og-image.png'],
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
      foundingDate: '2026',
    },
    {
      '@type': 'WebSite',
      name: 'AimFast.Dev',
      url: 'https://www.aimfast.dev/',
      description:
        'Daily market intelligence for indie builders. Product opportunities, competitor tracking, trend analysis from 11 global sources.',
      potentialAction: {
        '@type': 'SearchAction',
        target: {
          '@type': 'EntryPoint',
          urlTemplate: 'https://www.aimfast.dev/search?q={search_term_string}',
        },
        'query-input': 'required name=search_term_string',
      },
    },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
        <link rel="alternate" type="application/rss+xml" title="AimFast.Dev Articles RSS" href="/articles/rss.xml" />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
        <link rel="alternate" hrefLang="en" href="https://www.aimfast.dev/" />
        <link rel="alternate" hrefLang="zh-CN" href="https://www.aimfast.dev/zh/" />
        <link rel="alternate" hrefLang="x-default" href="https://www.aimfast.dev/" />
      </head>
      <body>
        <nav className="site-nav" aria-label="Main navigation">
          <a href="/" className="site-nav-logo">AimFast.Dev</a>
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
        </nav>
        {children}
        {/* Close mobile nav when a link is clicked */}
        <script dangerouslySetInnerHTML={{ __html: `
          (function(){
            var toggle = document.getElementById('nav-toggle');
            var links = document.querySelectorAll('.site-nav-links a');
            for (var i = 0; i < links.length; i++) {
              links[i].addEventListener('click', function(){ toggle.checked = false; });
            }
          })();
        `}} />
      </body>
    </html>
  );
}
