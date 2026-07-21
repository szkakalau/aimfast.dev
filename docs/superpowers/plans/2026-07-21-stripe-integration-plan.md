# Stripe 支付集成 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 AimFast.Dev 接入 Stripe 订阅支付，支持 Starter/Builder/Team 三档计划，14 天免费试用（需信用卡），含用户注册登录和订阅管理。

**Architecture:** Next.js 16 App Router SSR 模式 + NextAuth.js 邮箱密码认证 + Neon Postgres (Prisma ORM) + Stripe Checkout 托管支付 + Stripe Webhook 同步订阅状态。

**Tech Stack:** Next.js 16, React 19, TypeScript 5.7, Prisma 7, NextAuth.js 5, Stripe SDK, Neon Postgres, Pure CSS (现有设计系统)

## Global Constraints

- 所有新增页面必须使用项目现有的 Pure CSS 设计系统（`public/_ds/`）
- 所有用户可见文案必须是英文（`.tsx` 文件主语言），中文变体后续跟进
- 定价页保持现有三档结构（Starter $19/mo, Builder $39/mo, Team $79/mo）
- 免费试用 14 天，需要信用卡
- 不使用 Google OAuth，仅邮箱+密码登录
- 取消订阅策略: `cancel_at_period_end`（到期失效，非立即）

---

## 文件结构

```
新增文件:
  prisma/schema.prisma                       — 数据库 Schema
  app/api/auth/[...nextauth]/route.ts        — NextAuth.js Route Handler
  app/api/auth/register/route.ts             — 注册 API
  app/api/stripe/checkout/route.ts           — 创建 Checkout Session
  app/api/stripe/webhook/route.ts            — 接收 Stripe Webhook
  app/api/stripe/cancel/route.ts             — 取消订阅
  middleware.ts                              — 路由保护
  app/login/page.tsx                         — 登录页
  app/register/page.tsx                      — 注册页
  app/dashboard/layout.tsx                   — 仪表盘布局
  app/dashboard/page.tsx                     — 仪表盘首页（重定向到 billing）
  app/dashboard/billing/page.tsx             — 订阅管理页
  app/dashboard/billing/cancel-button.tsx    — 取消按钮客户端组件
  app/pricing/pricing-cta.tsx                — 定价 CTA 客户端组件
  lib/auth.ts                                — NextAuth.js 配置
  lib/stripe.ts                              — Stripe 客户端单例

修改文件:
  app/pricing/page.tsx                       — CTA 改为支付逻辑
  next.config.ts                             — 移除 output: 'export'
  package.json                               — 新增依赖
```

---

### Task 1: 依赖安装和环境配置

**Files:**
- Modify: `package.json`
- Modify: `next.config.ts`
- Create: `.env.local`

**Interfaces:**
- Produces: `next.config.ts` 中移除 `output: 'export'`，项目切换为 SSR 模式
- Produces: `.env.local` 中定义的环境变量供后续所有任务使用

- [ ] **Step 1: 安装依赖**

```bash
npm install @prisma/client next-auth@beta @auth/prisma-adapter stripe @stripe/stripe-js bcryptjs
npm install -D prisma @types/bcryptjs
```

预期: 安装成功，无版本冲突。`next-auth@beta` 是 NextAuth.js v5（适配 Next.js 16）。

- [ ] **Step 2: 移除静态导出配置**

读取 [next.config.ts](next.config.ts)，找到 `output: 'export'` 并删除该行。如果该配置不存在则跳过。

- [ ] **Step 3: 创建 .env.local**

```env
# 数据库 (Neon — 稍后执行 prisma db push 前填入)
DATABASE_URL=postgresql://...

# NextAuth.js
AUTH_SECRET=your-secret-here
AUTH_URL=http://localhost:3000

# Stripe (Test Mode)
STRIPE_SECRET_KEY=sk_test_...
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Stripe Price IDs (在 Stripe Dashboard 创建产品后填入)
STRIPE_STARTER_PRICE_ID=price_...
STRIPE_BUILDER_PRICE_ID=price_...
STRIPE_TEAM_PRICE_ID=price_...
```

- [ ] **Step 4: Commit**

```bash
git add package.json package-lock.json next.config.ts .env.local
git commit -m "chore: install Stripe + NextAuth.js + Prisma deps, switch to SSR mode"
```

---

### Task 2: Prisma Schema + Neon 数据库初始化

**Files:**
- Create: `prisma/schema.prisma`

**Interfaces:**
- Produces: `User`, `Account`, `Session`, `VerificationToken`, `Subscription` 表（Neon Postgres）
- Consumes: `DATABASE_URL` 环境变量

- [ ] **Step 1: 创建 prisma/schema.prisma**

```prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model User {
  id             String    @id @default(cuid())
  name           String?
  email          String    @unique
  emailVerified  DateTime?
  image          String?
  hashedPassword String?
  accounts       Account[]
  sessions       Session[]
  subscription   Subscription?

  createdAt      DateTime  @default(now())
  updatedAt      DateTime  @updatedAt
}

model Account {
  id                String  @id @default(cuid())
  userId            String
  type              String
  provider          String
  providerAccountId String
  refresh_token     String?
  access_token      String?
  expires_at        Int?
  token_type        String?
  scope             String?
  id_token          String?
  session_state     String?

  user User @relation(fields: [userId], references: [id], onDelete: Cascade)

  @@unique([provider, providerAccountId])
}

model Session {
  id           String   @id @default(cuid())
  sessionToken String   @unique
  userId       String
  expires      DateTime

  user User @relation(fields: [userId], references: [id], onDelete: Cascade)
}

model VerificationToken {
  identifier String
  token      String   @unique
  expires    DateTime

  @@unique([identifier, token])
}

model Subscription {
  id                   String   @id @default(cuid())
  userId               String   @unique
  stripeCustomerId     String   @unique
  stripeSubscriptionId String   @unique
  stripePriceId        String
  status               String
  planId               String
  currentPeriodEnd     DateTime
  trialEnd             DateTime?
  cancelAtPeriodEnd    Boolean  @default(false)

  user       User      @relation(fields: [userId], references: [id], onDelete: Cascade)
  createdAt  DateTime  @default(now())
  updatedAt  DateTime  @updatedAt
}
```

- [ ] **Step 2: 连接 Neon 并推送 Schema**

```bash
npx prisma db push
```

预期: `Your database is now in sync with your Prisma schema.`

- [ ] **Step 3: 生成 Prisma Client**

```bash
npx prisma generate
```

- [ ] **Step 4: Commit**

```bash
git add prisma/schema.prisma
git commit -m "feat: add Prisma schema — User, Account, Session, Subscription"
```

---

### Task 3: Stripe 客户端 + NextAuth.js 配置

**Files:**
- Create: `lib/stripe.ts`
- Create: `lib/auth.ts`

**Interfaces:**
- Produces: `stripe` — Stripe SDK 实例（`import { stripe } from '@/lib/stripe'`）
- Produces: `auth`, `signIn`, `signOut` — NextAuth.js 导出（`import { auth, signIn, signOut } from '@/lib/auth'`）
- Consumes: `STRIPE_SECRET_KEY`, `AUTH_SECRET`, `DATABASE_URL`

- [ ] **Step 1: 创建 lib/stripe.ts**

```typescript
import Stripe from 'stripe';

export const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: '2025-06-30.acacia' as any,
  typescript: true,
});
```

> 注意: `apiVersion` 使用最新稳定版。如果 Stripe SDK 版本不同，运行 `npx stripe versions` 查看可用版本并替换。

- [ ] **Step 2: 创建 lib/auth.ts**

```typescript
import NextAuth from 'next-auth';
import Credentials from 'next-auth/providers/credentials';
import { PrismaAdapter } from '@auth/prisma-adapter';
import { PrismaClient } from '@prisma/client';
import bcrypt from 'bcryptjs';

const prisma = new PrismaClient();

export const { handlers, auth, signIn, signOut } = NextAuth({
  adapter: PrismaAdapter(prisma),
  session: { strategy: 'jwt' },
  pages: {
    signIn: '/login',
  },
  providers: [
    Credentials({
      name: 'credentials',
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null;

        const user = await prisma.user.findUnique({
          where: { email: credentials.email as string },
        });

        if (!user || !user.hashedPassword) return null;

        const passwordMatch = await bcrypt.compare(
          credentials.password as string,
          user.hashedPassword,
        );

        if (!passwordMatch) return null;

        return { id: user.id, name: user.name, email: user.email };
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        (session.user as any).id = token.id;
      }
      return session;
    },
  },
});
```

- [ ] **Step 3: Commit**

```bash
git add lib/stripe.ts lib/auth.ts
git commit -m "feat: Stripe client + NextAuth.js config with Credentials provider"
```

---

### Task 4: NextAuth.js API Route + Middleware

**Files:**
- Create: `app/api/auth/[...nextauth]/route.ts`
- Create: `middleware.ts`

**Interfaces:**
- Produces: `GET/POST /api/auth/*` — NextAuth.js 所有认证端点
- Produces: `middleware.ts` — 保护 `/dashboard/*` 路由

- [ ] **Step 1: 创建 app/api/auth/[...nextauth]/route.ts**

```typescript
import { handlers } from '@/lib/auth';

export const { GET, POST } = handlers;
```

- [ ] **Step 2: 创建 middleware.ts**

```typescript
import { auth } from '@/lib/auth';
import { NextResponse } from 'next/server';

export default auth((req) => {
  const { pathname } = req.nextUrl;

  if (pathname.startsWith('/dashboard') && !req.auth) {
    const loginUrl = new URL('/login', req.url);
    loginUrl.searchParams.set('callback', pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
});

export const config = {
  matcher: ['/dashboard/:path*'],
};
```

- [ ] **Step 3: 验证**

```bash
npm run dev
```

访问 `http://localhost:3000/dashboard` → 应重定向到 `http://localhost:3000/login?callback=/dashboard`

- [ ] **Step 4: Commit**

```bash
git add app/api/auth/\[...nextauth\]/route.ts middleware.ts
git commit -m "feat: NextAuth.js API route + dashboard middleware"
```

---

### Task 5: 注册页面 + API

**Files:**
- Create: `app/register/page.tsx`
- Create: `app/api/auth/register/route.ts`

**Interfaces:**
- Consumes: `signIn` from `@/lib/auth`
- Produces: `/register` 页面 + `POST /api/auth/register`

- [ ] **Step 1: 创建 app/register/page.tsx**

```typescript
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { signIn } from 'next-auth/react';

export default function RegisterPage() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);

    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password }),
    });

    const data = await res.json();

    if (!res.ok) {
      setError(data.error || 'Registration failed');
      setLoading(false);
      return;
    }

    const result = await signIn('credentials', {
      email,
      password,
      redirect: false,
    });

    if (result?.error) {
      setError('Account created but auto-login failed. Please sign in.');
      setLoading(false);
      return;
    }

    router.push('/dashboard/billing');
  }

  return (
    <main className="container" style={{ maxWidth: '400px', margin: '0 auto', padding: 'var(--space-10) var(--space-3)' }}>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 'var(--space-6)' }}>Create your account</h1>

      {error && (
        <div style={{ padding: 'var(--space-3)', marginBottom: 'var(--space-4)', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '8px', color: '#dc2626', fontSize: '0.875rem' }}>
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
        <div>
          <label htmlFor="name" style={{ display: 'block', marginBottom: 'var(--space-1)', fontWeight: 500, fontSize: '0.875rem' }}>Name</label>
          <input id="name" type="text" value={name} onChange={(e) => setName(e.target.value)} required
            style={{ width: '100%', padding: '10px 12px', border: '1px solid var(--color-border, #d1d5db)', borderRadius: '8px', fontSize: '0.95rem' }} />
        </div>
        <div>
          <label htmlFor="email" style={{ display: 'block', marginBottom: 'var(--space-1)', fontWeight: 500, fontSize: '0.875rem' }}>Email</label>
          <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required
            style={{ width: '100%', padding: '10px 12px', border: '1px solid var(--color-border, #d1d5db)', borderRadius: '8px', fontSize: '0.95rem' }} />
        </div>
        <div>
          <label htmlFor="password" style={{ display: 'block', marginBottom: 'var(--space-1)', fontWeight: 500, fontSize: '0.875rem' }}>Password</label>
          <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8}
            style={{ width: '100%', padding: '10px 12px', border: '1px solid var(--color-border, #d1d5db)', borderRadius: '8px', fontSize: '0.95rem' }} />
        </div>
        <button type="submit" disabled={loading}
          style={{ padding: '12px', background: 'var(--color-accent, #2563eb)', color: '#fff', border: 'none', borderRadius: '8px', fontWeight: 600, fontSize: '0.95rem', cursor: 'pointer', opacity: loading ? 0.6 : 1 }}>
          {loading ? 'Creating account...' : 'Create account →'}
        </button>
      </form>

      <p style={{ textAlign: 'center', marginTop: 'var(--space-4)', fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>
        Already have an account? <a href="/login" style={{ color: 'var(--color-accent, #2563eb)' }}>Sign in</a>
      </p>
    </main>
  );
}
```

- [ ] **Step 2: 创建 app/api/auth/register/route.ts**

```typescript
import { NextResponse } from 'next/server';
import { PrismaClient } from '@prisma/client';
import bcrypt from 'bcryptjs';

const prisma = new PrismaClient();

export async function POST(request: Request) {
  try {
    const { name, email, password } = await request.json();

    if (!email || !password) {
      return NextResponse.json({ error: 'Email and password are required.' }, { status: 400 });
    }

    if (password.length < 8) {
      return NextResponse.json({ error: 'Password must be at least 8 characters.' }, { status: 400 });
    }

    const existing = await prisma.user.findUnique({ where: { email } });
    if (existing) {
      return NextResponse.json({ error: 'An account with this email already exists.' }, { status: 409 });
    }

    const hashedPassword = await bcrypt.hash(password, 12);

    await prisma.user.create({
      data: { name: name || null, email, hashedPassword },
    });

    return NextResponse.json({ success: true });
  } catch (error) {
    return NextResponse.json({ error: 'Registration failed. Please try again.' }, { status: 500 });
  }
}
```

- [ ] **Step 3: Commit**

```bash
git add app/register/page.tsx app/api/auth/register/route.ts
git commit -m "feat: registration page + register API route"
```

---

### Task 6: 登录页面

**Files:**
- Create: `app/login/page.tsx`

**Interfaces:**
- Consumes: `signIn` from `next-auth/react`
- Produces: `/login` 页面

- [ ] **Step 1: 创建 app/login/page.tsx**

```typescript
'use client';

import { useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { signIn } from 'next-auth/react';

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const callback = searchParams.get('callback') || '/dashboard/billing';
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const result = await signIn('credentials', { email, password, redirect: false });

      if (result?.error) {
        setError('Invalid email or password.');
      } else {
        router.push(callback);
      }
    } catch {
      setError('Something went wrong. Please try again.');
    }

    setLoading(false);
  }

  return (
    <div>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 'var(--space-6)' }}>Sign in to AimFast</h1>

      {error && (
        <div style={{ padding: 'var(--space-3)', marginBottom: 'var(--space-4)', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '8px', color: '#dc2626', fontSize: '0.875rem' }}>
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
        <div>
          <label htmlFor="email" style={{ display: 'block', marginBottom: 'var(--space-1)', fontWeight: 500, fontSize: '0.875rem' }}>Email</label>
          <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required
            style={{ width: '100%', padding: '10px 12px', border: '1px solid var(--color-border, #d1d5db)', borderRadius: '8px', fontSize: '0.95rem' }} />
        </div>
        <div>
          <label htmlFor="password" style={{ display: 'block', marginBottom: 'var(--space-1)', fontWeight: 500, fontSize: '0.875rem' }}>Password</label>
          <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required
            style={{ width: '100%', padding: '10px 12px', border: '1px solid var(--color-border, #d1d5db)', borderRadius: '8px', fontSize: '0.95rem' }} />
        </div>
        <button type="submit" disabled={loading}
          style={{ padding: '12px', background: 'var(--color-accent, #2563eb)', color: '#fff', border: 'none', borderRadius: '8px', fontWeight: 600, fontSize: '0.95rem', cursor: 'pointer', opacity: loading ? 0.6 : 1 }}>
          {loading ? 'Signing in...' : 'Sign in →'}
        </button>
      </form>

      <p style={{ textAlign: 'center', marginTop: 'var(--space-4)', fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>
        Don&apos;t have an account? <a href="/register" style={{ color: 'var(--color-accent, #2563eb)' }}>Create one</a>
      </p>
    </div>
  );
}

export default function LoginPage() {
  return (
    <main className="container" style={{ maxWidth: '400px', margin: '0 auto', padding: 'var(--space-10) var(--space-3)' }}>
      <Suspense fallback={<div style={{ textAlign: 'center', padding: 'var(--space-8)' }}>Loading...</div>}>
        <LoginForm />
      </Suspense>
    </main>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add app/login/page.tsx
git commit -m "feat: login page with credentials auth"
```

---

### Task 7: Stripe Checkout API Route

**Files:**
- Create: `app/api/stripe/checkout/route.ts`

**Interfaces:**
- Consumes: `auth()` from `@/lib/auth`, `stripe` from `@/lib/stripe`, Price ID 环境变量
- Produces: `POST /api/stripe/checkout` — `{ url: string }` 或 `{ error: string }`

- [ ] **Step 1: 创建 app/api/stripe/checkout/route.ts**

```typescript
import { NextResponse } from 'next/server';
import { auth } from '@/lib/auth';
import { stripe } from '@/lib/stripe';
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

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
```

- [ ] **Step 2: Commit**

```bash
git add app/api/stripe/checkout/route.ts
git commit -m "feat: Stripe Checkout Session API route"
```

---

### Task 8: Stripe Webhook API Route

**Files:**
- Create: `app/api/stripe/webhook/route.ts`

**Interfaces:**
- Consumes: `stripe` from `@/lib/stripe`, `STRIPE_WEBHOOK_SECRET`
- Produces: `POST /api/stripe/webhook` — 同步订阅状态

- [ ] **Step 1: 创建 app/api/stripe/webhook/route.ts**

```typescript
import { NextResponse } from 'next/server';
import { stripe } from '@/lib/stripe';
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

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
        const subscription = await stripe.subscriptions.retrieve(data.subscription as string);

        await prisma.subscription.create({
          data: {
            userId: userId!,
            stripeCustomerId: data.customer as string,
            stripeSubscriptionId: data.subscription as string,
            stripePriceId: data.metadata?.priceId ?? '',
            status: subscription.status,
            planId: planId ?? 'starter',
            currentPeriodEnd: new Date(subscription.current_period_end * 1000),
            trialEnd: subscription.trial_end ? new Date(subscription.trial_end * 1000) : null,
          },
        });
        break;
      }

      case 'invoice.paid': {
        const data = event.data.object;
        if (data.subscription) {
          const subscription = await stripe.subscriptions.retrieve(data.subscription as string);
          await prisma.subscription.updateMany({
            where: { stripeSubscriptionId: data.subscription as string },
            data: {
              status: 'active',
              currentPeriodEnd: new Date(subscription.current_period_end * 1000),
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
```

- [ ] **Step 2: Commit**

```bash
git add app/api/stripe/webhook/route.ts
git commit -m "feat: Stripe webhook handler — sync subscription status"
```

---

### Task 9: 取消订阅 API Route

**Files:**
- Create: `app/api/stripe/cancel/route.ts`

**Interfaces:**
- Consumes: `auth()` from `@/lib/auth`, `stripe` from `@/lib/stripe`
- Produces: `POST /api/stripe/cancel` — `{ success: true }` 或 `{ error: string }`

- [ ] **Step 1: 创建 app/api/stripe/cancel/route.ts**

```typescript
import { NextResponse } from 'next/server';
import { auth } from '@/lib/auth';
import { stripe } from '@/lib/stripe';
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

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
```

- [ ] **Step 2: Commit**

```bash
git add app/api/stripe/cancel/route.ts
git commit -m "feat: cancel subscription API — cancel_at_period_end"
```

---

### Task 10: 订阅管理页面 + 仪表盘布局

**Files:**
- Create: `app/dashboard/layout.tsx`
- Create: `app/dashboard/page.tsx`
- Create: `app/dashboard/billing/page.tsx`
- Create: `app/dashboard/billing/cancel-button.tsx`

**Interfaces:**
- Consumes: `auth()` from `@/lib/auth`, Prisma Subscription 表
- Produces: `/dashboard/billing` 页面

- [ ] **Step 1: 创建 app/dashboard/layout.tsx**

```typescript
import { auth } from '@/lib/auth';
import { redirect } from 'next/navigation';
import Link from 'next/link';

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const session = await auth();
  if (!session?.user) {
    redirect('/login?callback=/dashboard');
  }

  return (
    <main className="container" style={{ maxWidth: '960px', margin: '0 auto', padding: 'var(--space-6) var(--space-3)' }}>
      <nav style={{ display: 'flex', gap: 'var(--space-4)', marginBottom: 'var(--space-6)', borderBottom: '1px solid var(--color-border, #e5e7eb)', paddingBottom: 'var(--space-3)' }}>
        <Link href="/dashboard/billing" style={{ color: 'var(--color-accent, #2563eb)', fontWeight: 600, fontSize: '0.875rem', textDecoration: 'none' }}>
          Billing
        </Link>
        <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.875rem' }}>{session.user.email}</span>
        <a href="/api/auth/signout" style={{ marginLeft: 'auto', color: 'var(--color-text-secondary)', fontSize: '0.875rem', textDecoration: 'none' }}>
          Sign out
        </a>
      </nav>
      {children}
    </main>
  );
}
```

- [ ] **Step 2: 创建 app/dashboard/page.tsx**

```typescript
import { redirect } from 'next/navigation';

export default function DashboardPage() {
  redirect('/dashboard/billing');
}
```

- [ ] **Step 3: 创建 app/dashboard/billing/page.tsx**

```typescript
import { auth } from '@/lib/auth';
import { PrismaClient } from '@prisma/client';
import { CancelButton } from './cancel-button';
import Link from 'next/link';

const prisma = new PrismaClient();

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
                {subscription.status === 'active' && subscription.trialEnd && new Date(subscription.trialEnd) > new Date()
                  ? `14-day trial — ends on ${new Date(subscription.trialEnd).toLocaleDateString()}`
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
```

- [ ] **Step 4: 创建 app/dashboard/billing/cancel-button.tsx**

```typescript
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export function CancelButton() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [confirming, setConfirming] = useState(false);

  async function handleCancel() {
    setLoading(true);
    const res = await fetch('/api/stripe/cancel', { method: 'POST' });
    if (res.ok) {
      router.refresh();
    }
    setLoading(false);
  }

  if (!confirming) {
    return (
      <button onClick={() => setConfirming(true)}
        style={{ padding: '8px 16px', border: '1px solid #dc2626', color: '#dc2626', background: 'transparent', borderRadius: '8px', fontSize: '0.8125rem', fontWeight: 500, cursor: 'pointer' }}>
        Cancel subscription
      </button>
    );
  }

  return (
    <div style={{ textAlign: 'right' }}>
      <p style={{ fontSize: '0.8125rem', color: '#dc2626', marginBottom: 'var(--space-2)' }}>
        Cancel subscription? Access continues until period end.
      </p>
      <div style={{ display: 'flex', gap: 'var(--space-2)', justifyContent: 'flex-end' }}>
        <button onClick={() => setConfirming(false)}
          style={{ padding: '6px 12px', border: '1px solid var(--color-border, #d1d5db)', background: 'transparent', borderRadius: '6px', fontSize: '0.8125rem', cursor: 'pointer' }}>
          Keep
        </button>
        <button onClick={handleCancel} disabled={loading}
          style={{ padding: '6px 12px', background: '#dc2626', color: '#fff', border: 'none', borderRadius: '6px', fontSize: '0.8125rem', fontWeight: 500, cursor: 'pointer', opacity: loading ? 0.6 : 1 }}>
          {loading ? 'Canceling...' : 'Yes, cancel'}
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Commit**

```bash
git add app/dashboard/layout.tsx app/dashboard/page.tsx app/dashboard/billing/page.tsx app/dashboard/billing/cancel-button.tsx
git commit -m "feat: dashboard billing page + cancel subscription UI"
```

---

### Task 11: Pricing 页面 CTA 改造

**Files:**
- Create: `app/pricing/pricing-cta.tsx`
- Modify: `app/pricing/page.tsx`

**Interfaces:**
- Consumes: `auth()` from `@/lib/auth`
- Produces: 定价页 CTA 从 Tally 链接改为动态支付流程

- [ ] **Step 1: 创建 app/pricing/pricing-cta.tsx**

```typescript
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import type { Session } from 'next-auth';

interface Props {
  planId: string;
  session: Session | null;
  highlight?: boolean;
  cta: string;
}

export function PricingCTA({ planId, session, highlight, cta }: Props) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleClick() {
    setError('');

    if (!session) {
      router.push(`/login?callback=/pricing`);
      return;
    }

    setLoading(true);
    const res = await fetch('/api/stripe/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ planId }),
    });

    const data = await res.json();

    if (data.url) {
      window.location.href = data.url;
    } else {
      setError(data.error || 'Something went wrong.');
      setLoading(false);
    }
  }

  const buttonLabel = !session ? 'Sign in to Start →' : loading ? 'Redirecting...' : `${cta} →`;

  return (
    <div>
      <button onClick={handleClick} disabled={loading}
        style={{
          display: 'block', width: '100%', textAlign: 'center', padding: '12px 0', borderRadius: '8px',
          fontWeight: 600, fontSize: '0.95rem', textDecoration: 'none', marginBottom: error ? 'var(--space-2)' : 'var(--space-5)',
          border: 'none', cursor: 'pointer', transition: 'all 150ms ease-out',
          background: highlight ? 'var(--color-accent, #2563eb)' : 'var(--color-bg, #f3f4f6)',
          color: highlight ? '#fff' : 'var(--color-text, #111827)',
          boxShadow: highlight ? 'none' : 'inset 0 0 0 1px var(--color-border, #d1d5db)',
          opacity: loading ? 0.6 : 1,
        }}>
        {buttonLabel}
      </button>
      {error && (
        <p style={{ fontSize: '0.8125rem', color: '#dc2626', marginBottom: 'var(--space-5)', textAlign: 'center' }}>
          {error}
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 2: 更新 app/pricing/page.tsx**

1. 顶部添加: `import { auth } from '@/lib/auth';` 和 `import { PricingCTA } from './pricing-cta';`
2. `PricingPage` 改为 `async function PricingPage()`
3. 函数开头添加: `const session = await auth();`
4. 替换 `<a href="https://tally.so/r/placeholder" ...>` 为 `<PricingCTA planId={plan.id} session={session} highlight={plan.highlight} cta={plan.cta} />`
5. 底部 Footer CTA 替换为: `<PricingCTA planId="builder" session={session} highlight cta="Start Building" />`
6. 底部文案 "No credit card required. Cancel anytime." → "Cancel anytime."

- [ ] **Step 3: Commit**

```bash
git add app/pricing/page.tsx app/pricing/pricing-cta.tsx
git commit -m "feat: pricing CTA wired to Stripe Checkout"
```

---

### Task 12: 权限控制

**Files:**
- Modify: `middleware.ts`

- [ ] **Step 1: 更新 middleware.ts**

```typescript
import { auth } from '@/lib/auth';
import { NextResponse } from 'next/server';
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

export default auth(async (req) => {
  const { pathname } = req.nextUrl;

  // /dashboard/* 需要登录
  if (pathname.startsWith('/dashboard') && !req.auth) {
    const loginUrl = new URL('/login', req.url);
    loginUrl.searchParams.set('callback', pathname);
    return NextResponse.redirect(loginUrl);
  }

  // /reports/* 深度报告需要活跃订阅
  if (pathname.startsWith('/reports/') && pathname !== '/reports/') {
    if (!req.auth) {
      const loginUrl = new URL('/login', req.url);
      loginUrl.searchParams.set('callback', pathname);
      return NextResponse.redirect(loginUrl);
    }

    const userId = (req.auth.user as any).id;
    const subscription = await prisma.subscription.findUnique({ where: { userId } });

    const hasAccess =
      subscription &&
      (subscription.status === 'active' || subscription.status === 'trialing');

    if (!hasAccess) {
      return NextResponse.redirect(new URL('/pricing?access=required', req.url));
    }
  }

  return NextResponse.next();
});

export const config = {
  matcher: ['/dashboard/:path*', '/reports/:path*'],
};
```

- [ ] **Step 2: Commit**

```bash
git add middleware.ts
git commit -m "feat: middleware — premium content requires active subscription"
```

---

### Task 13: 最终验证 & Stripe 生产准备

- [ ] **Step 1: 端到端测试（Stripe Test Mode）**

Stripe Test Card: `4242 4242 4242 4242`，任意未来日期 CVC `123`

流程:
1. `/register` → 注册账号
2. `/pricing` → 选择 Builder → 点击 CTA
3. Stripe Checkout → 输入测试卡号 → 确认
4. 跳回 `/dashboard/billing?success=true` → 看到 "Builder Plan — 14-day trial"
5. 点击 "Cancel subscription" → 确认 → 显示 "Cancels on {date}"
6. `/reports/2026-07-18` → 正常访问（试用期内）

- [ ] **Step 2: Stripe Dashboard 生产准备**

在 [dashboard.stripe.com](https://dashboard.stripe.com):
1. 切换到 Live Mode
2. Products → 重新创建 3 个产品（Live 和 Test 独立）
3. 获取 Live Key: `sk_live_...` / `pk_live_...`
4. 添加生产 Webhook endpoint
5. 设置品牌（logo + 颜色 `#2563eb`）
6. 配置结算信息

- [ ] **Step 3: 部署**

```bash
# Vercel Dashboard 添加所有环境变量（Live Key）
# DATABASE_URL, AUTH_SECRET, STRIPE_SECRET_KEY,
# NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY, STRIPE_WEBHOOK_SECRET,
# STRIPE_STARTER_PRICE_ID, STRIPE_BUILDER_PRICE_ID, STRIPE_TEAM_PRICE_ID

vercel --prod
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: final Stripe integration — ready for production"
```

---

## 实施总览

| Task | 内容 | 文件数 |
|------|------|--------|
| 1 | 依赖安装 + 环境配置 | 3 |
| 2 | Prisma Schema + Neon | 1 |
| 3 | Stripe 客户端 + NextAuth.js 配置 | 2 |
| 4 | NextAuth.js API + Middleware | 2 |
| 5 | 注册页面 + API | 2 |
| 6 | 登录页面 | 1 |
| 7 | Stripe Checkout API | 1 |
| 8 | Stripe Webhook API | 1 |
| 9 | 取消订阅 API | 1 |
| 10 | 仪表盘 + 订阅管理页面 | 4 |
| 11 | Pricing CTA 改造 | 2 |
| 12 | 权限控制 | 1 |
| 13 | E2E 验证 + 生产准备 | 0 |

**共 13 个任务，约 22 个文件。**
