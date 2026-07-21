# Stripe 支付集成 — 设计方案

**日期**: 2026-07-21
**状态**: 已确认

---

## 技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| 支付 | Stripe Checkout | 托管页面，Stripe 处理 PCI 合规，最快上线 |
| 认证 | NextAuth.js (Auth.js) | Next.js 生态标准，邮箱+密码登录 |
| 数据库 | Neon (Postgres) | Serverless Postgres，Vercel 一键接入 |
| ORM | Prisma | 声明式 schema，NextAuth.js 官方 adapter，社区最大 |

---

## 1. 架构变更

```
当前（纯静态）                      改造后（服务端）
─────────────────────────      ─────────────────────────
                               app/api/                      ← 新增 API Routes
                                   ├─ auth/[...nextauth]/   ← NextAuth.js
                                   ├─ stripe/checkout/      ← Stripe Checkout Session
                                   ├─ stripe/webhook/       ← Stripe 事件
                                   └─ stripe/cancel/        ← 取消订阅

Next.js build                   Next.js SSR
  └─ output: 'export'           └─ output: 'server' (默认)
     (静态 HTML)                   (服务端渲染 + API Routes)

无数据库                         Neon Postgres
                                   ├─ User + Account + Session (NextAuth.js)
                                   └─ Subscription (业务表)
```

**改动范围：**
- `next.config.ts` — 移除 `output: 'export'`
- 新增 `prisma/schema.prisma`
- 新增 `app/api/auth/[...nextauth]/route.ts`
- 新增 `app/api/stripe/checkout/route.ts`
- 新增 `app/api/stripe/webhook/route.ts`
- 新增 `app/api/stripe/cancel/route.ts`
- 新增 `middleware.ts`
- 新增 `app/login/page.tsx`、`app/register/page.tsx`
- 新增 `app/dashboard/billing/page.tsx`、`app/dashboard/layout.tsx`
- 修改 `app/pricing/page.tsx`（CTA 从 Tally 链接改为支付逻辑）

---

## 2. 数据库 Schema

```prisma
model User {
  id            String    @id @default(cuid())
  name          String?
  email         String    @unique
  emailVerified DateTime?
  image         String?
  accounts      Account[]
  sessions      Session[]
  subscription  Subscription?

  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @updatedAt
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
  status               String   // active | past_due | canceled | unpaid
  planId               String   // starter | builder | team
  currentPeriodEnd     DateTime
  trialEnd             DateTime?
  cancelAtPeriodEnd    Boolean  @default(false)

  user       User      @relation(fields: [userId], references: [id], onDelete: Cascade)
  createdAt  DateTime  @default(now())
  updatedAt  DateTime  @updatedAt
}
```

---

## 3. 认证流程

- **Provider**: 邮箱+密码（Credentials Provider），无邮箱验证（降低注册摩擦）
- **Adapter**: `@auth/prisma-adapter`
- **Session 策略**: JWT 模式
- **中间件**: `middleware.ts` 保护 `/dashboard/*` 路由
- **页面**: `/login`、`/register`、`/dashboard/billing`

```
用户访问 /pricing
  → 选择计划 → 点击 "Start Free Trial"
  → 检查登录状态
      ├─ 未登录 → 跳转 /login?callback=/pricing → 注册/登录后跳回
      └─ 已登录 → 直接进入支付
  → POST /api/stripe/checkout → 302 跳转到 Stripe 托管页
```

---

## 4. 支付流程

### 订阅创建

```
POST /api/stripe/checkout
  body: { planId: 'starter' | 'builder' | 'team' }

服务端：
  1. 查用户是否已有活跃订阅 → 有则返回错误
  2. 查/建 Stripe Customer
  3. 创建 Checkout Session（mode: 'subscription', trial_period_days: 14）
  4. success_url → /dashboard/billing?success=true
  5. cancel_url → /pricing?canceled=true
```

### Webhook 事件

| 事件 | 处理 |
|------|------|
| `checkout.session.completed` | 创建 Subscription 记录，status: 'active' |
| `invoice.paid` | 更新 currentPeriodEnd |
| `invoice.payment_failed` | status → 'past_due'（Stripe 自带的催款邮件处理通知） |
| `customer.subscription.updated` | 同步 planId、priceId、周期变更 |
| `customer.subscription.deleted` | status → 'canceled' |

### 取消订阅

`POST /api/stripe/cancel` → `stripe.subscriptions.update(id, { cancel_at_period_end: true })` → 更新 DB

### 订阅管理页面 `/dashboard/billing`

| 状态 | 显示 |
|------|------|
| 无订阅 | 「无活跃订阅」+ 链接回 /pricing |
| 试用中 | 「14 天试用，{date} 到期」+ 取消按钮 |
| 活跃 | 「{Plan} — 下次扣款 {date}」+ 取消 + 升级/降级 |
| 已取消（未到期） | 「{date} 后失效」+ 重新激活按钮 |

---

## 5. 权限控制

- `/trends` 列表保持公开（免费流量入口）
- 深度报告 `/reports/[date]` 和决策卡片内容需要活跃订阅
- 中间件根据 `subscription.status === 'active'` 或 `trialEnd > now()` 判断访问权限

---

## 6. Stripe Dashboard 准备清单

1. 注册 [dashboard.stripe.com](https://dashboard.stripe.com)
2. Products → 创建 3 个产品：Starter / Builder / Team，各绑定月付 recurring price
3. 记录月付 Price ID，写入 `.env`
4. Webhooks → 添加 endpoint：`https://www.aimfast.dev/api/stripe/webhook`，监听事件：
   - `checkout.session.completed`
   - `invoice.paid`
   - `invoice.payment_failed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
5. 获取 `STRIPE_SECRET_KEY` + `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`
6. Branding → 上传 logo、品牌色 `#2563eb`

---

## 7. 环境变量

```env
DATABASE_URL=postgresql://...  (Neon)
AUTH_SECRET=<openssl rand -base64 32>
STRIPE_SECRET_KEY=sk_test_...
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_STARTER_PRICE_ID=price_...
STRIPE_BUILDER_PRICE_ID=price_...
STRIPE_TEAM_PRICE_ID=price_...
```

---

## 8. 实施步骤

```
Phase 1 — 基础设施
  [ ] 移除 output: 'export'
  [ ] prisma init → schema.prisma → prisma db push
  [ ] 安装依赖

Phase 2 — 认证
  [ ] NextAuth.js 配置 + Route Handler
  [ ] middleware.ts
  [ ] /login + /register 页面
  [ ] UserMenu 组件

Phase 3 — 支付
  [ ] Stripe Checkout API Route
  [ ] Stripe Webhook API Route
  [ ] Stripe Cancel API Route
  [ ] Pricing 页面 CTA 改造

Phase 4 — 订阅管理
  [ ] /dashboard/billing 页面
  [ ] /dashboard 布局

Phase 5 — 权限控制
  [ ] 中间件扩展：premium 内容访问控制
```
