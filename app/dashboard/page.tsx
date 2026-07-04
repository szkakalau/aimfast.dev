import type { Metadata } from 'next';
import { DashboardClient } from './dashboard-client';

export const metadata: Metadata = {
  title: 'Dashboard — AimFast.Dev',
  description:
    'Daily market intelligence dashboard. Signal scores, competitor tracking, opportunity pipeline, and daily reports.',
  robots: { index: false, follow: false },
};

export default function DashboardPage() {
  return <DashboardClient />;
}
