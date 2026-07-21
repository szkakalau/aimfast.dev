import { auth } from '@/lib/auth';
import { prisma } from '@/lib/prisma';
import { CancelButton } from './cancel-button';
import Link from 'next/link';

const PLAN_LABELS: Record<string, string> = {
  starter: 'Starter',
  builder: 'Builder',
  team: 'Team',
};

export default async function BillingPage({ searchParams }: { searchParams: Promise<{ success?: string }> }) {
  const session = await auth();
  const userId = (session?.user as any).id;
  const params = await searchParams;

  const subscription = await prisma.subscription.findUnique({ where: { userId } });

  const trialActive = subscription?.trialEnd && new Date(subscription.trialEnd) > new Date();

  return (
    <div>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 'var(--space-4)' }}>Billing</h1>

      {params.success && (
        <div style={{ padding: 'var(--space-3)', marginBottom: 'var(--space-4)', background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '8px', color: '#16a34a', fontSize: '0.875rem' }}>
          Subscription activated! Welcome to AimFast.
        </div>
      )}

      {!subscription || subscription.status === 'canceled' ? (
        <div style={{ padding: 'var(--space-6)', textAlign: 'center', border: '1px solid var(--color-border, #e5e7eb)', borderRadius: '12px' }}>
          <p style={{ marginBottom: 'var(--space-4)', color: 'var(--color-text-secondary)' }}>
            You don&apos;t have an active subscription.
          </p>
          <Link href="/pricing"
            style={{ display: 'inline-block', padding: '12px 24px', background: 'var(--color-accent, #2563eb)', color: '#fff', borderRadius: '8px', fontWeight: 600, textDecoration: 'none' }}>
            View plans →
          </Link>
        </div>
      ) : (
        <div style={{ padding: 'var(--space-6)', border: '1px solid var(--color-border, #e5e7eb)', borderRadius: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--space-4)' }}>
            <div>
              <h2 style={{ fontSize: '1.125rem', fontWeight: 700 }}>
                {PLAN_LABELS[subscription.planId] ?? subscription.planId} Plan
              </h2>
              <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.875rem' }}>
                {subscription.status === 'active' && trialActive
                  ? `14-day trial — ends on ${new Date(subscription.trialEnd!).toLocaleDateString()}`
                  : subscription.status === 'active'
                    ? `Next billing: ${new Date(subscription.currentPeriodEnd).toLocaleDateString()}`
                    : `Status: ${subscription.status}`
                }
              </p>
              {subscription.cancelAtPeriodEnd && (
                <p style={{ marginTop: 'var(--space-2)', fontSize: '0.8125rem', color: '#dc2626' }}>
                  Cancels on {new Date(subscription.currentPeriodEnd).toLocaleDateString()} — access until then.
                </p>
              )}
            </div>

            {!subscription.cancelAtPeriodEnd && subscription.status === 'active' && (
              <CancelButton />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
