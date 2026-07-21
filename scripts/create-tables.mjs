import 'dotenv/config';
import { Pool, neonConfig } from '@neondatabase/serverless';
import ws from 'ws';

neonConfig.webSocketConstructor = ws;

const pool = new Pool({ connectionString: process.env.DATABASE_URL, max: 1 });

async function main() {
  const client = await pool.connect();
  try {
    // Drop test tables
    await client.query('DROP TABLE IF EXISTS t1');
    console.log('1-drop t1');
    await client.query('DROP TABLE IF EXISTS acc');
    console.log('2-drop acc');

    // Account
    await client.query(`CREATE TABLE IF NOT EXISTS "Account" (
      id TEXT PRIMARY KEY DEFAULT gen_random_uuid(),
      "userId" TEXT NOT NULL REFERENCES "User"(id) ON DELETE CASCADE,
      type TEXT NOT NULL,
      provider TEXT NOT NULL,
      "providerAccountId" TEXT NOT NULL,
      refresh_token TEXT,
      access_token TEXT,
      expires_at INT,
      token_type TEXT,
      scope TEXT,
      id_token TEXT,
      session_state TEXT,
      UNIQUE(provider, "providerAccountId")
    )`);
    console.log('3-Account');

    // Session
    await client.query(`CREATE TABLE IF NOT EXISTS "Session" (
      id TEXT PRIMARY KEY DEFAULT gen_random_uuid(),
      "sessionToken" TEXT UNIQUE NOT NULL,
      "userId" TEXT NOT NULL REFERENCES "User"(id) ON DELETE CASCADE,
      expires TIMESTAMPTZ NOT NULL
    )`);
    console.log('4-Session');

    // VerificationToken
    await client.query(`CREATE TABLE IF NOT EXISTS "VerificationToken" (
      identifier TEXT NOT NULL,
      token TEXT UNIQUE NOT NULL,
      expires TIMESTAMPTZ NOT NULL,
      UNIQUE(identifier, token)
    )`);
    console.log('5-VerificationToken');

    // Subscription
    await client.query(`CREATE TABLE IF NOT EXISTS "Subscription" (
      id TEXT PRIMARY KEY DEFAULT gen_random_uuid(),
      "userId" TEXT UNIQUE NOT NULL REFERENCES "User"(id) ON DELETE CASCADE,
      "stripeCustomerId" TEXT UNIQUE,
      "stripeSubscriptionId" TEXT UNIQUE,
      "stripePriceId" TEXT NOT NULL,
      status TEXT NOT NULL,
      "planId" TEXT NOT NULL,
      "currentPeriodEnd" TIMESTAMPTZ NOT NULL,
      "trialEnd" TIMESTAMPTZ,
      "cancelAtPeriodEnd" BOOLEAN NOT NULL DEFAULT false,
      "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
      "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT now()
    )`);
    console.log('6-Subscription');

    // Verify
    const r = await client.query(`SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name`);
    console.log('ALL OK. Tables:', r.rows.map(t => t.table_name).join(', '));
  } finally {
    client.release();
    await pool.end();
  }
}

main().catch(e => {
  console.error('FATAL:', e.message);
  process.exit(1);
});
