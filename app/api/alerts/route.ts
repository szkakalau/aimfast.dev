import { NextResponse } from 'next/server';
import { auth } from '@/lib/auth';
import { prisma } from '@/lib/prisma';
import { getUserId } from '@/lib/session';

const MAX_ALERTS = 10;
const VALID_CATEGORIES = [
  'DevTools', 'AIAgent', 'OpenSource', 'AIModel', 'TechConcept',
  'Industry', 'AIApp', 'DX', 'Infra', 'Productivity', 'Consumer', 'Design',
];

// ═════ GET — List user alerts ═════

export async function GET() {
  const session = await auth();
  const userId = getUserId(session);
  if (!userId) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const alerts = await prisma.alert.findMany({
    where: { userId },
    orderBy: { createdAt: 'desc' },
  });

  // Check for new matches since last visit
  const matches: Array<{ alert: typeof alerts[0]; matchedTerm: string }> = [];
  try {
    const { readFileSync, existsSync } = await import('node:fs');
    const { join } = await import('node:path');
    const path = join(process.cwd(), 'tracking', 'trend_terms.json');
    if (existsSync(path)) {
      const data = JSON.parse(readFileSync(path, 'utf-8'));
      const terms = data.terms || [];

      for (const alert of alerts) {
        if (!alert.enabled) continue;
        const kw = alert.keyword.toLowerCase();
        const matching = terms.filter((t: Record<string, unknown>) => {
          const name = String(t.canonical || '').toLowerCase();
          const tags = (t.tags as string[]) || [];
          const score = Number(t.score || 0);
          const category = String(t.category || '');
          const matchesKeyword = name.includes(kw) || tags.some((tag: string) => tag.toLowerCase().includes(kw));
          const meetsScore = score >= alert.minScore;
          const matchesCategory = !alert.category || category === alert.category;
          return matchesKeyword && meetsScore && matchesCategory;
        });

        if (matching.length > 0) {
          const newest = matching.sort((a: Record<string, unknown>, b: Record<string, unknown>) => {
            const dA = String(a.last_seen || '');
            const dB = String(b.last_seen || '');
            return dB.localeCompare(dA);
          })[0];
          const termName = String(newest.canonical || '');
          if (termName !== alert.lastMatchTerm) {
            matches.push({ alert, matchedTerm: termName });
            // Update last match
            await prisma.alert.update({
              where: { id: alert.id },
              data: { lastMatchedAt: new Date(), lastMatchTerm: termName },
            });
          }
        }
      }
    }
  } catch {
    // Alert matching is best-effort
  }

  return NextResponse.json({
    alerts: alerts.map((a) => ({
      id: a.id,
      keyword: a.keyword,
      category: a.category,
      minScore: a.minScore,
      enabled: a.enabled,
      lastMatchedAt: a.lastMatchedAt?.toISOString() || null,
      lastMatchTerm: a.lastMatchTerm,
      createdAt: a.createdAt.toISOString(),
    })),
    newMatches: matches.map((m) => ({
      alertId: m.alert.id,
      keyword: m.alert.keyword,
      matchedTerm: m.matchedTerm,
    })),
  });
}

// ═════ POST — Create alert ═════

export async function POST(request: Request) {
  const session = await auth();
  const userId = getUserId(session);
  if (!userId) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  let body: { keyword?: string; category?: string | null; minScore?: number };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  const keyword = body.keyword?.trim().toLowerCase();
  if (!keyword || keyword.length < 2 || keyword.length > 100) {
    return NextResponse.json({ error: 'Keyword is required (2-100 chars).' }, { status: 400 });
  }

  if (body.category && !VALID_CATEGORIES.includes(body.category)) {
    return NextResponse.json({ error: `Invalid category. Valid: ${VALID_CATEGORIES.join(', ')}` }, { status: 400 });
  }

  const minScore = body.minScore ?? 50;
  if (minScore < 0 || minScore > 100) {
    return NextResponse.json({ error: 'minScore must be 0-100.' }, { status: 400 });
  }

  // Limit check
  const count = await prisma.alert.count({ where: { userId } });
  if (count >= MAX_ALERTS) {
    return NextResponse.json({ error: `Max ${MAX_ALERTS} alerts allowed.` }, { status: 409 });
  }

  // Duplicate check (case-insensitive)
  const existing = await prisma.alert.findUnique({
    where: { userId_keyword: { userId, keyword } },
  });
  if (existing) {
    return NextResponse.json({ error: 'An alert with this keyword already exists.' }, { status: 409 });
  }

  const alert = await prisma.alert.create({
    data: {
      userId,
      keyword,
      category: body.category || null,
      minScore,
      enabled: true,
    },
  });

  return NextResponse.json(
    {
      alert: {
        id: alert.id,
        keyword: alert.keyword,
        category: alert.category,
        minScore: alert.minScore,
        enabled: alert.enabled,
        createdAt: alert.createdAt.toISOString(),
      },
    },
    { status: 201 },
  );
}

// ═════ DELETE — Remove alert ═════

export async function DELETE(request: Request) {
  const session = await auth();
  const userId = getUserId(session);
  if (!userId) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const { searchParams } = new URL(request.url);
  const id = searchParams.get('id');
  if (!id) {
    return NextResponse.json({ error: 'Missing id parameter.' }, { status: 400 });
  }

  const alert = await prisma.alert.findUnique({ where: { id } });
  if (!alert || alert.userId !== userId) {
    return NextResponse.json({ error: 'Alert not found.' }, { status: 404 });
  }

  await prisma.alert.delete({ where: { id } });
  return NextResponse.json({ ok: true });
}

// ═════ PATCH — Toggle enabled/disabled ═════

export async function PATCH(request: Request) {
  const session = await auth();
  const userId = getUserId(session);
  if (!userId) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const { searchParams } = new URL(request.url);
  const id = searchParams.get('id');
  if (!id) {
    return NextResponse.json({ error: 'Missing id parameter.' }, { status: 400 });
  }

  let body: { enabled?: boolean; minScore?: number };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  const alert = await prisma.alert.findUnique({ where: { id } });
  if (!alert || alert.userId !== userId) {
    return NextResponse.json({ error: 'Alert not found.' }, { status: 404 });
  }

  const data: Record<string, unknown> = {};
  if (typeof body.enabled === 'boolean') data.enabled = body.enabled;
  if (typeof body.minScore === 'number' && body.minScore >= 0 && body.minScore <= 100) {
    data.minScore = body.minScore;
  }

  if (Object.keys(data).length === 0) {
    return NextResponse.json({ error: 'No valid fields to update.' }, { status: 400 });
  }

  const updated = await prisma.alert.update({ where: { id }, data });
  return NextResponse.json({
    alert: {
      id: updated.id,
      keyword: updated.keyword,
      category: updated.category,
      minScore: updated.minScore,
      enabled: updated.enabled,
    },
  });
}
