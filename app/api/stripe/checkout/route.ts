import { NextResponse } from 'next/server';
import { auth } from '@/lib/auth';
import { stripe } from '@/lib/stripe';
import { prisma } from '@/lib/prisma';

const PRICE_IDS: Record<string, string> = {
  starter: process.env.STRIPE_STARTER_PRICE_ID!,
  builder: process.env.STRIPE_BUILDER_PRICE_ID!,
  team: process.env.STRIPE_TEAM_PRICE_ID!,
};

export async function POST(request: Request) {
  try {
    const session = await auth();
    if (!session?.user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const userId = (session.user as any).id;
    const { planId } = await request.json();

    if (!planId || !['starter', 'builder', 'team'].includes(planId)) {
      return NextResponse.json({ error: 'Invalid plan' }, { status: 400 });
    }

    const existing = await prisma.subscription.findUnique({ where: { userId } });

    if (existing && ['active', 'past_due', 'trialing'].includes(existing.status)) {
      return NextResponse.json({ error: 'You already have an active subscription.' }, { status: 409 });
    }

    const priceId = PRICE_IDS[planId];
    if (!priceId) {
      return NextResponse.json({ error: 'Price not configured.' }, { status: 500 });
    }

    const user = await prisma.user.findUnique({ where: { id: userId } });
    let stripeCustomerId = existing?.stripeCustomerId;

    if (!stripeCustomerId) {
      const customer = await stripe.customers.create({
        email: user?.email ?? undefined,
        metadata: { userId },
      });
      stripeCustomerId = customer.id;
    }

    const origin = request.headers.get('origin') || process.env.AUTH_URL || 'http://localhost:3000';

    const checkoutSession = await stripe.checkout.sessions.create({
      customer: stripeCustomerId,
      mode: 'subscription',
      line_items: [{ price: priceId, quantity: 1 }],
      subscription_data: { trial_period_days: 14 },
      success_url: `${origin}/dashboard/billing?success=true`,
      cancel_url: `${origin}/pricing?canceled=true`,
      metadata: { userId, planId },
    });

    return NextResponse.json({ url: checkoutSession.url! });
  } catch (error: any) {
    console.error('Checkout error:', error);
    return NextResponse.json({ error: 'Failed to create checkout session.' }, { status: 500 });
  }
}
