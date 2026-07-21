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
        const sub = await stripe.subscriptions.retrieve(data.subscription as string);

        await prisma.subscription.create({
          data: {
            userId: userId!,
            stripeCustomerId: data.customer as string,
            stripeSubscriptionId: data.subscription as string,
            stripePriceId: sub.items.data[0]?.price.id ?? '',
            status: sub.status,
            planId: planId ?? 'starter',
            currentPeriodEnd: new Date(sub.current_period_end * 1000),
            trialEnd: sub.trial_end ? new Date(sub.trial_end * 1000) : null,
          },
        });
        break;
      }

      case 'invoice.paid': {
        const data = event.data.object;
        if (data.subscription) {
          const sub = await stripe.subscriptions.retrieve(data.subscription as string);
          await prisma.subscription.updateMany({
            where: { stripeSubscriptionId: data.subscription as string },
            data: {
              status: 'active',
              currentPeriodEnd: new Date(sub.current_period_end * 1000),
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
        await prisma.subscription.updateMany({
          where: { stripeSubscriptionId: data.id },
          data: {
            status: data.status,
            stripePriceId: data.items.data[0]?.price.id ?? '',
            currentPeriodEnd: new Date(data.current_period_end * 1000),
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
    }

    return NextResponse.json({ received: true });
  } catch (error) {
    console.error('Webhook handler error:', error);
    return NextResponse.json({ error: 'Webhook handler error' }, { status: 500 });
  }
}
