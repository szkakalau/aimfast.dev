import type { Metadata } from 'next';
import { DashboardClient } from './dashboard-client';
import { getAllTrendTerms } from '@/app/trends/data';
import { auth } from '@/lib/auth';
import { prisma } from '@/lib/prisma';
import { getUserId } from '@/lib/session';

export const metadata: Metadata = {
  title: 'Dashboard — AimFast.Dev',
  description:
    'Daily market intelligence dashboard. Signal scores, opportunity pipeline, and daily reports.',
  robots: { index: false, follow: false },
};

export default async function DashboardPage() {
  // Embed trend data at build time — no extra client fetch needed for Watchlist display
  const trendData = getAllTrendTerms();

  // 服务端获取订阅状态 — 用于功能门控（不做重定向，由 client 组件决定展示内容）
  const session = await auth();
  const userId = getUserId(session);
  const sub = userId
    ? await prisma.subscription.findUnique({ where: { userId } })
    : null;

  const subscription = sub
    ? {
        planId: sub.planId,
        status: sub.status,
        trialEnd: sub.trialEnd?.toISOString() ?? null,
        currentPeriodEnd: sub.currentPeriodEnd.toISOString(),
        cancelAtPeriodEnd: sub.cancelAtPeriodEnd,
      }
    : null;

  return (
    <>
      {/* Static SEO fallback: search engines and LLM crawlers see this when JS is disabled.
          The real dashboard loads client-side via DashboardClient. */}
      <noscript>
        <main className="container" style={{ padding: 'var(--space-8) 0' }}>
          <h1>AimFast.Dev — Dashboard</h1>
          <p>
            Daily market intelligence for indie builders. One validated product
            opportunity every morning — what to build, who will pay, and how much
            to charge. Monitor watchlist signals and get AI-powered decision
            support from 30+ global sources.
          </p>
          <ul>
            <li>Watchlist: monitor tracked terms with 7-day trend deltas</li>
            <li>Today&apos;s Decision: one actionable opportunity with evidence, buyer, pricing, and validation path</li>
            <li>Full Report: comprehensive daily signal digest with plain-English breakdowns</li>
          </ul>
          <p>
            <a href="/trends/">Browse all trends →</a>
          </p>
        </main>
      </noscript>
      <DashboardClient trendTerms={trendData.terms} subscription={subscription} />
    </>
  );
}
