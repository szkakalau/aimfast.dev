'use client';

import { usePathname } from 'next/navigation';

/* ── Declarative route table — single source of truth ── */

interface LangRoute {
  /** Regex that matches this route in either language */
  pattern: RegExp;
  /** Whether the pattern matches a Chinese page */
  zh: boolean;
  /** Build the alternate-language URL from the regex match groups */
  alt: (groups: string[]) => string;
}

const LANG_ROUTES: LangRoute[] = [
  // EN-primary exact paths
  { pattern: /^\/$/,              zh: false, alt: () => '/zh/' },
  { pattern: /^\/zh\/$/,          zh: true,  alt: () => '/' },
  { pattern: /^\/pricing\/$/,     zh: false, alt: () => '/pricing/zh/' },
  { pattern: /^\/pricing\/zh\/$/, zh: true,  alt: () => '/pricing/' },
  { pattern: /^\/about\/$/,       zh: false, alt: () => '/about/zh/' },
  { pattern: /^\/about\/zh\/$/,   zh: true,  alt: () => '/about/' },

  // Dashboard: client-side i18n toggle (localStorage), URL doesn't change
  { pattern: /^\/dashboard\/$/, zh: false, alt: () => '/dashboard/' },

  // Trends: EN primary, ZH at /zh/ suffix
  { pattern: /^\/trends\/(.+?)\/zh\/?$/, zh: true,  alt: (g) => `/trends/${g[1]}/` },
  { pattern: /^\/trends\/(.+?)\/?$/,     zh: false, alt: (g) => `/trends/${g[1]}/zh/` },

  // Reports: EN primary, ZH at /zh/ suffix
  { pattern: /^\/reports\/(.+?)\/zh\/?$/, zh: true,  alt: (g) => `/reports/${g[1]}/` },
  { pattern: /^\/reports\/(.+?)\/?$/,     zh: false, alt: (g) => `/reports/${g[1]}/zh/` },

  // Articles: EN primary, ZH at /zh/ suffix
  { pattern: /^\/articles\/(.+?)\/zh\/?$/, zh: true,  alt: (g) => `/articles/${g[1]}/` },
  { pattern: /^\/articles\/(.+?)\/?$/,     zh: false, alt: (g) => `/articles/${g[1]}/zh/` },
];

/* ── Helpers ── */

function resolveRoute(pathname: string): LangRoute | null {
  for (const route of LANG_ROUTES) {
    if (route.pattern.test(pathname)) return route;
  }
  return null;
}

function getAlternateUrl(pathname: string): string {
  const resolved = resolveRoute(pathname);
  if (resolved) {
    const m = pathname.match(resolved.pattern)!;
    return resolved.alt(Array.from(m));
  }
  // Fallback for unknown paths: link to Chinese homepage
  return '/zh/';
}

function isZhPath(pathname: string): boolean {
  return resolveRoute(pathname)?.zh ?? false;
}

/* ── Component ── */

export default function LangToggle() {
  const pathname = usePathname();
  const altUrl = getAlternateUrl(pathname);
  const isZh = isZhPath(pathname);

  return (
    <a
      href={altUrl}
      className="nav-lang"
      aria-label={isZh ? 'Switch to English' : '切换到中文'}
    >
      {isZh ? 'EN' : '中文'}
    </a>
  );
}
