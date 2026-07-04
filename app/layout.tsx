import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AimFast.Dev — Daily Market Intelligence for Indie Builders',
  description:
    'Every morning, get one validated product opportunity — what to build, who will pay, and how much to charge. AI scans 11 sources so you don\'t have to. 14-day free trial, $19/mo.',
  robots: { index: true, follow: true },
  metadataBase: new URL('https://aimfast.dev'),
  alternates: { canonical: 'https://www.aimfast.dev/' },
  openGraph: {
    type: 'website',
    title: 'AimFast.Dev — Daily Market Intelligence for Indie Builders',
    description:
      'Every morning, get one validated product opportunity with a build plan and pricing strategy. AI scans 11 global sources.',
    url: 'https://www.aimfast.dev/',
    siteName: 'AimFast.Dev',
    images: [
      {
        url: 'https://www.aimfast.dev/og-image.png',
        width: 1200,
        height: 630,
        alt: 'AimFast.Dev — Daily Market Intelligence',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'AimFast.Dev — Daily Market Intelligence',
    description: 'Daily validated product opportunities from 11 global signal sources.',
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
    <html lang="zh-CN">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
        <link rel="alternate" hrefLang="zh-CN" href="https://www.aimfast.dev/" />
        <link rel="alternate" hrefLang="x-default" href="https://www.aimfast.dev/" />
      </head>
      <body>{children}</body>
    </html>
  );
}
