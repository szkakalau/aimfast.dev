import { NextResponse } from 'next/server';
import { stripe } from '@/lib/stripe';
import { prisma } from '@/lib/prisma';

// Stripe webhook needs raw body — disable body parsing
export const dynamic = 'force-dynamic';

export async function POST(request: Request) {
  const rawBody = await request.text();
  const signature = request.headers.get('stripe-signature')!;

  let event: any;

  try {
    event = stripe.webhooks.constructEvent(rawBody, signature, process.env.STRIPE_WEBHOOK_SECRET!);
  } catch (error) {
    console.error('Webhook signature verification failed:', error);
    return NextResponse.json({ error: 'Invalid signature' }, { status: 400 });
  }

  try {
    switch (event.type) {
      case 'checkout.session.completed': {
        const data = event.data.object;
        const { userId, planId } = data.metadata ?? {};

        if (!userId) {
          console.error('Webhook: checkout.session.completed missing userId in metadata');
          return NextResponse.json({ error: 'Missing userId' }, { status: 400 });
        }

        const sub = await stripe.subscriptions.retrieve(data.subscription as string);
        const now = new Date();
        // Stripe SDK v22+: current_period_end 移到 Subscription Item 级别
        const itemPeriodEnd = sub.items.data[0]?.current_period_end;
        const periodEnd = itemPeriodEnd
          ? new Date(itemPeriodEnd * 1000)
          : new Date(now.getTime() + 14 * 24 * 60 * 60 * 1000);

        // upsert — 幂等处理 Stripe 重复事件
        await prisma.subscription.upsert({
          where: { stripeSubscriptionId: data.subscription as string },
          create: {
            userId,
            stripeCustomerId: data.customer as string,
            stripeSubscriptionId: data.subscription as string,
            stripePriceId: sub.items.data[0]?.price.id ?? '',
            status: sub.status,
            planId: planId ?? 'starter',
            currentPeriodEnd: periodEnd,
            trialEnd: sub.trial_end ? new Date(sub.trial_end * 1000) : null,
          },
          update: {
            status: sub.status,
            stripePriceId: sub.items.data[0]?.price.id ?? '',
            currentPeriodEnd: periodEnd,
            trialEnd: sub.trial_end ? new Date(sub.trial_end * 1000) : null,
          },
        });
        break;
      }

      case 'invoice.paid': {
        const data = event.data.object;
        if (data.subscription) {
          const sub = await stripe.subscriptions.retrieve(data.subscription as string);
          // Stripe SDK v22+: current_period_end 移到 Subscription Item 级别
          const itemPeriodEnd = sub.items.data[0]?.current_period_end;
          const periodEnd = itemPeriodEnd
            ? new Date(itemPeriodEnd * 1000)
            : undefined;
          await prisma.subscription.updateMany({
            where: { stripeSubscriptionId: data.subscription as string },
            data: {
              status: 'active',
              ...(periodEnd ? { currentPeriodEnd: periodEnd } : {}),
            },
          });
        }
        break;
      }

      case 'invoice.payment_failed': {
        const data = event.data.object;
        if (data.subscription) {
          await prisma.subscription.updateMany({
            where: { stripeSubscriptionId: data.subscription as string },
            data: { status: 'past_due' },
          });
        }
        break;
      }

      case 'customer.subscription.updated': {
        const data = event.data.object;
        const periodEnd = data.current_period_end
          ? new Date(data.current_period_end * 1000)
          : undefined;
        await prisma.subscription.updateMany({
          where: { stripeSubscriptionId: data.id },
          data: {
            status: data.status,
            stripePriceId: data.items.data[0]?.price.id ?? '',
            ...(periodEnd ? { currentPeriodEnd: periodEnd } : {}),
            trialEnd: data.trial_end ? new Date(data.trial_end * 1000) : null,
            cancelAtPeriodEnd: data.cancel_at_period_end,
          },
        });
        break;
      }

      case 'customer.subscription.deleted': {
        const data = event.data.object;
        await prisma.subscription.updateMany({
          where: { stripeSubscriptionId: data.id },
          data: { status: 'canceled' },
        });
        break;
      }

      default:
        // 未处理的 Stripe 事件类型 — 记录但不阻塞，便于运维排查
        console.warn(`Webhook: unhandled event type "${event.type}" (id: ${event.id})`);
    }

    return NextResponse.json({ received: true });
  } catch (error) {
    console.error('Webhook handler failed');
    return NextResponse.json({ error: 'Webhook handler error' }, { status: 500 });
  }
}
