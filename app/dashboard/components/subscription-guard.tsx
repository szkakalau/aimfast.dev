'use client';

import Link from 'next/link';
import { Lock, AlertTriangle, Clock } from 'lucide-react';

type SubscriptionStatus = {
  planId: string | null;
  status: string | null;
  trialEnd: string | null;
  currentPeriodEnd: string | null;
  cancelAtPeriodEnd: boolean;
};

/**
 * 订阅门控组件 — 根据订阅状态决定是否展示付费内容。
 *
 * - 无订阅或无试用 → 显示升级提示
 * - 试用中 → 正常渲染 + 试用剩余天数
 * - active → 正常渲染
 * - past_due → 显示支付失败提示
 */
export default function SubscriptionGuard({
  subscription,
  children,
  isAdmin = false,
}: {
  subscription: SubscriptionStatus | null;
  children: React.ReactNode;
  isAdmin?: boolean;
}) {
  // ── 管理员自动放行 ──
  if (isAdmin) return <>{children}</>;

  // ── 无订阅 ──
  if (!subscription || !subscription.status) {
    return (
      <div className="sub-guard">
        <div className="sub-guard-card">
          <Lock size={32} className="sub-guard-icon" aria-hidden="true" />
          <h2 className="sub-guard-title">Unlock Full Access</h2>
          <p className="sub-guard-desc">
            Daily verified decisions, topic monitoring, and full research reports are available on Builder and Team plans.
          </p>
          <div className="sub-guard-features">
            <span>✅ Daily decision card</span>
            <span>✅ Topic monitoring (up to 10)</span>
            <span>✅ Full deep research reports</span>
            <span>✅ Unlimited term tracking</span>
            <span>✅ 14-day free trial</span>
          </div>
          <Link href="/pricing" className="sub-guard-cta">
            View Plans →
          </Link>
        </div>
      </div>
    );
  }

  const { status, trialEnd, planId } = subscription;
  const isActive = status === 'active' || status === 'trialing';
  const trialDaysLeft = trialEnd
    ? Math.max(0, Math.ceil((new Date(trialEnd).getTime() - Date.now()) / 86400000))
    : 0;
  const isTrialing = status === 'trialing' || (status === 'active' && trialDaysLeft > 0);

  // ── 支付失败 ──
  if (status === 'past_due') {
    return (
      <div className="sub-guard">
        <div className="sub-guard-card sub-guard-error">
          <AlertTriangle size={32} className="sub-guard-icon" aria-hidden="true" />
          <h2 className="sub-guard-title">Payment Failed</h2>
          <p className="sub-guard-desc">
            Your last payment did not go through. Please update your billing details to restore full access.
          </p>
          <Link href="/dashboard/billing" className="sub-guard-cta">
            Manage Billing →
          </Link>
        </div>
      </div>
    );
  }

  // ── 已取消 ──
  if (status === 'canceled') {
    return (
      <div className="sub-guard">
        <div className="sub-guard-card">
          <Lock size={32} className="sub-guard-icon" aria-hidden="true" />
          <h2 className="sub-guard-title">Subscription Ended</h2>
          <p className="sub-guard-desc">
            Your subscription has ended. Re-activate to regain full access to daily decisions and topic monitoring.
          </p>
          <Link href="/pricing" className="sub-guard-cta">
            View Plans →
          </Link>
        </div>
      </div>
    );
  }

  // ── 试用提示条 ──
  if (isTrialing && trialDaysLeft > 0) {
    return (
      <>
        <div className="sub-guard-trial-banner" role="alert">
          <Clock size={14} aria-hidden="true" />
          <span>
            {trialDaysLeft} day{trialDaysLeft !== 1 ? 's' : ''} left in your {planId ?? 'Builder'} trial.&nbsp;
            <Link href="/dashboard/billing" style={{ color: 'inherit', fontWeight: 600, textDecoration: 'underline' }}>
              Add payment method →
            </Link>
          </span>
        </div>
        {children}
      </>
    );
  }

  // ── 正常激活 ──
  return <>{children}</>;
}
