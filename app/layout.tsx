import type { Metadata, Viewport } from 'next';
import { headers } from 'next/headers';
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
  title: 'AimFast.Dev — Signal Over Hype: AI-Curated Tech Trends',
  description:
    'AI scans 30+ channels daily, cross-validates every term, and ranks by builder relevance — signal over hype. Dashboard membership unlocks daily product opportunities — what to build, who will pay, and how much to charge.',
  robots: { index: true, follow: true },
  metadataBase: new URL('https://www.aimfast.dev'),
  // NOTE: alternates (canonical + hreflang) are set per-page.
  // Setting them here leaks homepage hreflang to every child page — don't do it.
  openGraph: {
    type: 'website',
    title: 'AimFast.Dev — Signal Over Hype: AI-Curated Tech Trends',
    description:
      'AI ranks tech terms by builder relevance, not hype. Free daily tracking. Dashboard: one validated product opportunity every morning.',
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
    title: 'AimFast.Dev — Signal Over Hype',
    description: 'AI ranks tech terms by builder relevance, not hype. Free daily tracking. Dashboard: daily product opportunities.',
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
      logo: 'https://www.aimfast.dev/og-home.png',
      image: 'https://www.aimfast.dev/og-home.png',
      description:
        'Daily market intelligence for indie builders. AI scans 30+ channels to deliver one validated product opportunity every morning — what to build, who will pay, and how much to charge.',
      foundingDate: '2026-01-01',
      sameAs: [
        'https://github.com/szkakalau/aimfast.dev',
        'https://twitter.com/aimfastdev',
        'https://buttondown.com/aimfast',
      ],
      contactPoint: {
        '@type': 'ContactPoint',
        contactType: 'customer support',
        email: 'support@aimfast.dev',
        url: 'https://www.aimfast.dev/about/',
      },
    },
    {
      '@type': 'WebSite',
      name: 'AimFast.Dev',
      url: 'https://www.aimfast.dev/',
      description:
        'Daily market intelligence for indie builders. Product opportunities, trend analysis from 30+ global channels.',
      potentialAction: {
        '@type': 'SearchAction',
        target: {
          '@type': 'EntryPoint',
          urlTemplate: 'https://www.aimfast.dev/search/?q={search_term_string}',
        },
        'query-input': 'required name=search_term_string',
      },
    },
  ],
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  // Server-side lang detection via middleware-set header — no client-side JS needed.
  const headersList = await headers();
  const lang = headersList.get('x-lang') || 'en';

  return (
    <html lang={lang} className={`${firaSans.variable} ${firaCode.variable} ${jetbrainsMono.variable}`}>
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
        {/* Per-page hreflang alternates are set via generateMetadata in each page. */}
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
              <a href="/about/">About</a>
              <LangToggle />
            </div>
            <label htmlFor="nav-toggle" className="nav-backdrop" aria-hidden="true" />
          </div>
        </nav>
        <span id="main-content" tabIndex={-1} />
        {children}
        {/* Close mobile nav when a link is clicked */}
        {/* lang attribute is now set server-side via middleware x-lang header */}
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
