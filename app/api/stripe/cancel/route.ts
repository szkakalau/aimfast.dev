import { NextResponse } from 'next/server';
import { auth } from '@/lib/auth';
import { stripe } from '@/lib/stripe';
import { prisma } from '@/lib/prisma';

export async function POST() {
  try {
    const session = await auth();
    if (!session?.user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const userId = (session.user as any).id;
    const subscription = await prisma.subscription.findUnique({ where: { userId } });

    if (!subscription) {
      return NextResponse.json({ error: 'No active subscription found.' }, { status: 404 });
    }

    await stripe.subscriptions.update(subscription.stripeSubscriptionId, {
      cancel_at_period_end: true,
    });

    await prisma.subscription.update({
      where: { userId },
      data: { cancelAtPeriodEnd: true },
    });

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Cancel error:', error);
    return NextResponse.json({ error: 'Failed to cancel subscription.' }, { status: 500 });
  }
}
