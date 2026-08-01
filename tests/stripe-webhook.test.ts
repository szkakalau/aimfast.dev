/**
 * Stripe Webhook Handler Tests
 * Covers: signature verification + 5 event type handlers
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

// ── Mock factories (hoisted before imports) ──

const mockUpsert = vi.fn();
const mockUpdateMany = vi.fn();
const mockSubscribeRetrieve = vi.fn();

vi.mock('@/lib/prisma', () => ({
  prisma: {
    subscription: {
      get upsert() { return mockUpsert; },
      get updateMany() { return mockUpdateMany; },
    },
  },
}));

vi.mock('@/lib/stripe', () => ({
  stripe: {
    get subscriptions() { return { retrieve: mockSubscribeRetrieve }; },
  },
}));

vi.mock('stripe', () => ({
  default: {
    webhooks: {
      constructEvent: vi.fn(),
    },
  },
}));

import Stripe from 'stripe';
import { POST } from '@/app/api/stripe/webhook/route';

// ── Helpers ──

function buildRequest(body: string | object, sig?: string): Request {
  const raw = typeof body === 'string' ? body : JSON.stringify(body);
  const headers = new Headers();
  headers.set('Content-Type', 'application/json');
  if (sig) headers.set('stripe-signature', sig);
  return new Request('http://localhost/api/stripe/webhook', {
    method: 'POST',
    headers,
    body: raw,
  });
}

function fakeStripeEvent(type: string, overrides: Record<string, unknown> = {}): Stripe.Event {
  return {
    id: 'evt_test',
    object: 'event',
    api_version: '2026-06-24.dahlia',
    created: Math.floor(Date.now() / 1000),
    data: { object: overrides as Stripe.Event.Data['object'] },
    type,
    livemode: false,
    pending_webhooks: 0,
    request: null,
  } as unknown as Stripe.Event;
}

const VALID_SIG = 't=1234567890,v1=abcdef,v0=...';

// ── Tests ──

describe('Stripe Webhook POST', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubEnv('STRIPE_WEBHOOK_SECRET', 'whsec_test_secret');
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  // ── Signature Verification ──

  describe('signature verification', () => {
    it('returns 400 when stripe-signature header is missing', async () => {
      const req = buildRequest('{}'); // no signature header
      const res = await POST(req);
      expect(res.status).toBe(400);
      const body = await res.json();
      expect(body.error).toBe('Missing signature');
    });

    it('returns 500 when STRIPE_WEBHOOK_SECRET is not configured', async () => {
      vi.stubEnv('STRIPE_WEBHOOK_SECRET', undefined as unknown as string);
      const req = buildRequest('{}', VALID_SIG);
      const res = await POST(req);
      expect(res.status).toBe(500);
      const body = await res.json();
      expect(body.error).toBe('Server configuration error');
    });

    it('returns 400 when constructEvent throws (invalid signature)', async () => {
      const constructEvent = Stripe.webhooks.constructEvent as ReturnType<typeof vi.fn>;
      constructEvent.mockImplementation(() => {
        throw new Error('No signatures found matching the expected signature');
      });
      const req = buildRequest('{}', 't=bad,v1=wrong');
      const res = await POST(req);
      expect(res.status).toBe(400);
      const body = await res.json();
      expect(body.error).toBe('Invalid signature');
    });

    it('returns 200 when event type is unhandled (unknown event)', async () => {
      const constructEvent = Stripe.webhooks.constructEvent as ReturnType<typeof vi.fn>;
      constructEvent.mockReturnValue(fakeStripeEvent('some.unknown.event'));
      const req = buildRequest('{}', VALID_SIG);
      const res = await POST(req);
      expect(res.status).toBe(200);
      const body = await res.json();
      expect(body.received).toBe(true);
    });
  });

  // ── checkout.session.completed ──

  describe('checkout.session.completed', () => {
    function fakeCheckoutEvent(metadata?: Record<string, string>): Stripe.Event {
      return fakeStripeEvent('checkout.session.completed', {
        id: 'cs_test_123',
        object: 'checkout.session',
        customer: 'cus_test_123',
        subscription: 'sub_test_123',
        metadata: metadata ?? { userId: 'user-1', planId: 'builder' },
      });
    }

    beforeEach(() => {
      const constructEvent = Stripe.webhooks.constructEvent as ReturnType<typeof vi.fn>;
      constructEvent.mockReturnValue(fakeCheckoutEvent());

      mockSubscribeRetrieve.mockResolvedValue({
        id: 'sub_test_123',
        status: 'active',
        trial_end: null,
        items: {
          data: [{
            price: { id: 'price_test_123' },
            current_period_end: Math.floor(Date.now() / 1000) + 30 * 24 * 3600,
          }],
        },
      });
    });

    it('creates subscription via upsert with correct fields', async () => {
      const req = buildRequest({ type: 'checkout.session.completed' }, VALID_SIG);
      const res = await POST(req);

      expect(res.status).toBe(200);
      expect(mockUpsert).toHaveBeenCalledTimes(1);

      const upsertArgs = mockUpsert.mock.calls[0][0];
      expect(upsertArgs.where).toEqual({ stripeSubscriptionId: 'sub_test_123' });
      expect(upsertArgs.create.userId).toBe('user-1');
      expect(upsertArgs.create.stripeCustomerId).toBe('cus_test_123');
      expect(upsertArgs.create.stripeSubscriptionId).toBe('sub_test_123');
      expect(upsertArgs.create.stripePriceId).toBe('price_test_123');
      expect(upsertArgs.create.status).toBe('active');
      expect(upsertArgs.create.planId).toBe('builder');
      expect(upsertArgs.create.currentPeriodEnd).toBeInstanceOf(Date);
    });

    it('returns 400 when metadata is missing userId', async () => {
      const constructEvent = Stripe.webhooks.constructEvent as ReturnType<typeof vi.fn>;
      constructEvent.mockReturnValue(fakeCheckoutEvent({ planId: 'starter' }));
      const req = buildRequest({}, VALID_SIG);
      const res = await POST(req);

      expect(res.status).toBe(400);
      const body = await res.json();
      expect(body.error).toBe('Missing userId');
    });

    it('handles missing subscription items with default 14-day periodEnd', async () => {
      mockSubscribeRetrieve.mockResolvedValue({
        id: 'sub_test_123',
        status: 'active',
        trial_end: null,
        items: { data: [] },
      });

      const req = buildRequest({}, VALID_SIG);
      const res = await POST(req);

      expect(res.status).toBe(200);
      expect(mockUpsert).toHaveBeenCalledTimes(1);
      const upsertArgs = mockUpsert.mock.calls[0][0];
      // Default 14-day periodEnd should be a future date
      expect(upsertArgs.create.currentPeriodEnd.getTime()).toBeGreaterThan(Date.now());
    });
  });

  // ── invoice.paid ──

  describe('invoice.paid', () => {
    beforeEach(() => {
      const constructEvent = Stripe.webhooks.constructEvent as ReturnType<typeof vi.fn>;
      constructEvent.mockReturnValue(fakeStripeEvent('invoice.paid', {
        id: 'in_test_123',
        object: 'invoice',
        parent: {
          subscription_details: {
            subscription: 'sub_test_123',
          },
        },
      }));

      mockSubscribeRetrieve.mockResolvedValue({
        id: 'sub_test_123',
        items: {
          data: [{
            current_period_end: 1717200000,
          }],
        },
      });
    });

    it('updates subscription status to active', async () => {
      const req = buildRequest({}, VALID_SIG);
      const res = await POST(req);

      expect(res.status).toBe(200);
      expect(mockUpdateMany).toHaveBeenCalledTimes(1);

      const updateArgs = mockUpdateMany.mock.calls[0][0];
      expect(updateArgs.where).toEqual({ stripeSubscriptionId: 'sub_test_123' });
      expect(updateArgs.data.status).toBe('active');
      expect(updateArgs.data.currentPeriodEnd).toBeInstanceOf(Date);
    });

    it('does nothing when subscription reference is missing', async () => {
      const constructEvent = Stripe.webhooks.constructEvent as ReturnType<typeof vi.fn>;
      constructEvent.mockReturnValue(fakeStripeEvent('invoice.paid', {
        id: 'in_test_456',
        object: 'invoice',
        parent: undefined,
      }));

      const req = buildRequest({}, VALID_SIG);
      const res = await POST(req);

      expect(res.status).toBe(200);
      expect(mockUpdateMany).not.toHaveBeenCalled();
    });
  });

  // ── invoice.payment_failed ──

  describe('invoice.payment_failed', () => {
    it('updates subscription status to past_due', async () => {
      const constructEvent = Stripe.webhooks.constructEvent as ReturnType<typeof vi.fn>;
      constructEvent.mockReturnValue(fakeStripeEvent('invoice.payment_failed', {
        id: 'in_test_789',
        object: 'invoice',
        parent: {
          subscription_details: {
            subscription: 'sub_test_fail',
          },
        },
      }));

      const req = buildRequest({}, VALID_SIG);
      const res = await POST(req);

      expect(res.status).toBe(200);
      expect(mockUpdateMany).toHaveBeenCalledTimes(1);

      const updateArgs = mockUpdateMany.mock.calls[0][0];
      expect(updateArgs.where).toEqual({ stripeSubscriptionId: 'sub_test_fail' });
      expect(updateArgs.data.status).toBe('past_due');
    });
  });

  // ── customer.subscription.updated ──

  describe('customer.subscription.updated', () => {
    beforeEach(() => {
      const constructEvent = Stripe.webhooks.constructEvent as ReturnType<typeof vi.fn>;
      constructEvent.mockReturnValue(fakeStripeEvent('customer.subscription.updated', {
        id: 'sub_test_updated',
        object: 'subscription',
        status: 'active',
        trial_end: 1717200000,
        cancel_at_period_end: false,
        items: {
          data: [{
            price: { id: 'price_updated' },
            current_period_end: 1717200000,
          }],
        },
      }));
    });

    it('updates all subscription fields', async () => {
      const req = buildRequest({}, VALID_SIG);
      const res = await POST(req);

      expect(res.status).toBe(200);
      expect(mockUpdateMany).toHaveBeenCalledTimes(1);

      const updateArgs = mockUpdateMany.mock.calls[0][0];
      expect(updateArgs.where).toEqual({ stripeSubscriptionId: 'sub_test_updated' });
      expect(updateArgs.data.status).toBe('active');
      expect(updateArgs.data.stripePriceId).toBe('price_updated');
      expect(updateArgs.data.currentPeriodEnd).toBeInstanceOf(Date);
      expect(updateArgs.data.trialEnd).toBeInstanceOf(Date);
      expect(updateArgs.data.cancelAtPeriodEnd).toBe(false);
    });

    it('handles missing trial_end gracefully', async () => {
      const constructEvent = Stripe.webhooks.constructEvent as ReturnType<typeof vi.fn>;
      constructEvent.mockReturnValue(fakeStripeEvent('customer.subscription.updated', {
        id: 'sub_no_trial',
        object: 'subscription',
        status: 'active',
        trial_end: null,
        cancel_at_period_end: false,
        items: {
          data: [{
            price: { id: 'price_updated' },
            current_period_end: 1717200000,
          }],
        },
      }));

      const req = buildRequest({}, VALID_SIG);
      const res = await POST(req);

      expect(res.status).toBe(200);
      expect(mockUpdateMany).toHaveBeenCalledTimes(1);

      const updateArgs = mockUpdateMany.mock.calls[0][0];
      expect(updateArgs.data.trialEnd).toBeNull();
    });
  });

  // ── customer.subscription.deleted ──

  describe('customer.subscription.deleted', () => {
    it('sets subscription status to canceled', async () => {
      const constructEvent = Stripe.webhooks.constructEvent as ReturnType<typeof vi.fn>;
      constructEvent.mockReturnValue(fakeStripeEvent('customer.subscription.deleted', {
        id: 'sub_deleted_123',
        object: 'subscription',
      }));

      const req = buildRequest({}, VALID_SIG);
      const res = await POST(req);

      expect(res.status).toBe(200);
      expect(mockUpdateMany).toHaveBeenCalledTimes(1);

      const updateArgs = mockUpdateMany.mock.calls[0][0];
      expect(updateArgs.where).toEqual({ stripeSubscriptionId: 'sub_deleted_123' });
      expect(updateArgs.data.status).toBe('canceled');
    });
  });
});
