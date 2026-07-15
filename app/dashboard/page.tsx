import type { Metadata } from 'next';
import { DashboardClient } from './dashboard-client';
import { getAllTrendTerms } from '@/app/trends/data';

export const metadata: Metadata = {
  title: 'Dashboard — AimFast.Dev',
  description:
    'Daily market intelligence dashboard. Signal scores, competitor tracking, opportunity pipeline, and daily reports.',
  robots: { index: false, follow: false },
};

export default function DashboardPage() {
  // Embed trend data at build time — no extra client fetch needed for Watchlist display
  const trendData = getAllTrendTerms();
  return <DashboardClient trendTerms={trendData.terms} />;
}
