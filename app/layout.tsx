import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'KAKAOPC Intel — Daily Signal Intelligence for Indie Developers',
  description:
    'AI scans 14 sources daily (HN, GitHub, Reddit, Product Hunt). Every morning, get one validated product opportunity with a build plan and pricing strategy — free.',
  robots: { index: true, follow: true },
  metadataBase: new URL('https://aimfast.dev'),
  alternates: { canonical: 'https://aimfast.dev/' },
  openGraph: {
    type: 'website',
    title: 'KAKAOPC Intel — Daily Signal Intelligence for Indie Developers',
    description:
      'Every morning, get one validated product opportunity with a build plan and pricing strategy. Scanned from 14 global sources.',
    url: 'https://aimfast.dev/',
    siteName: 'KAKAOPC Intel',
  },
  twitter: {
    card: 'summary',
    title: 'KAKAOPC Intel — Daily Signal Intelligence',
    description: 'Daily product opportunities from 14 signal sources.',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;500;600&family=Space+Grotesk:wght@500;600;700&display=swap"
          rel="stylesheet"
        />
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
      </head>
      <body>{children}</body>
    </html>
  );
}
