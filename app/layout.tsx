import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AimFast.Dev — Daily Signal Intelligence for Indie Developers',
  description:
    'AI scans 14 sources daily (HN, GitHub, Reddit, Product Hunt). Every morning, get one validated product opportunity with a build plan and pricing strategy — free.',
  robots: { index: true, follow: true },
  metadataBase: new URL('https://aimfast.dev'),
  alternates: { canonical: 'https://aimfast.dev/' },
  openGraph: {
    type: 'website',
    title: 'AimFast.Dev — Daily Signal Intelligence for Indie Developers',
    description:
      'Every morning, get one validated product opportunity with a build plan and pricing strategy. Scanned from 14 global sources.',
    url: 'https://aimfast.dev/',
    siteName: 'AimFast.Dev',
    images: [
      {
        url: 'https://aimfast.dev/og-image.png',
        width: 1200,
        height: 630,
        alt: 'AimFast.Dev — Daily Signal Intelligence',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'AimFast.Dev — Daily Signal Intelligence',
    description: 'Daily product opportunities from 14 signal sources.',
    images: ['https://aimfast.dev/og-image.png'],
  },
};

const jsonLd = {
  '@context': 'https://schema.org',
  '@graph': [
    {
      '@type': 'Organization',
      name: 'AimFast.Dev',
      url: 'https://aimfast.dev/',
      description:
        'Daily signal intelligence for indie developers. AI scans 14 sources to deliver one validated product opportunity every morning.',
      foundingDate: '2026',
    },
    {
      '@type': 'WebSite',
      name: 'AimFast.Dev',
      url: 'https://aimfast.dev/',
      description:
        'Daily signal intelligence for indie developers. Product opportunities, trend analysis, and buildable insights from 14 global sources.',
      potentialAction: {
        '@type': 'SearchAction',
        target: {
          '@type': 'EntryPoint',
          urlTemplate: 'https://aimfast.dev/search?q={search_term_string}',
        },
        'query-input': 'required name=search_term_string',
      },
    },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;500;600&family=Space+Grotesk:wght@500;600;700&display=swap"
          rel="stylesheet"
        />
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
        {/* hreflang: root page has both zh-CN (default) and en alternates */}
        <link rel="alternate" hrefLang="zh-CN" href="https://aimfast.dev/" />
        <link rel="alternate" hrefLang="en" href="https://aimfast.dev/en/" />
        <link rel="alternate" hrefLang="x-default" href="https://aimfast.dev/" />
      </head>
      <body>{children}</body>
    </html>
  );
}
