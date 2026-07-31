import { NextResponse } from 'next/server';
import { auth } from '@/lib/auth';
import { prisma } from '@/lib/prisma';
import { getUserId } from '@/lib/session';
import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';

/** Verify user has an active Pro+ subscription */
async function checkProAccess(userId: string): Promise<boolean> {
  try {
    const sub = await prisma.subscription.findUnique({ where: { userId } });
    if (!sub) return false;
    return ['active', 'trialing'].includes(sub.status);
  } catch {
    return false;
  }
}

/** Load trend terms data */
function loadTrendTerms(): { updated_at: string; terms: unknown[] } {
  try {
    const path = join(process.cwd(), 'tracking', 'trend_terms.json');
    if (!existsSync(path)) return { updated_at: '', terms: [] };
    const raw = readFileSync(path, 'utf-8');
    return JSON.parse(raw);
  } catch {
    return { updated_at: '', terms: [] };
  }
}

/** Convert trend terms to flat CSV rows */
function termsToCsv(terms: Record<string, unknown>[]): string {
  const headers = [
    'id', 'canonical', 'category', 'stage', 'score',
    'opportunity_score', 'market_score', 'competition_score', 'demand_score',
    'source_count', 'total_mentions', 'growth_pct', 'seo_difficulty',
    'first_seen', 'last_seen', 'suggested_products', 'tags',
  ];

  const escape = (v: unknown): string => {
    const s = Array.isArray(v) ? v.join('; ') : String(v ?? '');
    if (s.includes(',') || s.includes('"') || s.includes('\n')) {
      return `"${s.replace(/"/g, '""')}"`;
    }
    return s;
  };

  const rows = [headers.join(',')];
  for (const t of terms) {
    rows.push(headers.map((h) => escape(t[h])).join(','));
  }
  return rows.join('\n');
}

// ═════ GET — Export trend terms as CSV or JSON ═════

export async function GET(request: Request) {
  const session = await auth();
  const userId = getUserId(session);
  if (!userId) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  // Admin bypass
  const role = (session?.user as Record<string, unknown> | undefined)?.role as string | undefined;
  if (role !== 'admin') {
    const hasAccess = await checkProAccess(userId);
    if (!hasAccess) {
      return NextResponse.json(
        { error: 'Export requires a Pro subscription. Upgrade at /pricing.' },
        { status: 402 },
      );
    }
  }

  const { searchParams } = new URL(request.url);
  const type = searchParams.get('type') || 'trends';
  const format = searchParams.get('format') || 'json';

  if (type === 'trends') {
    const data = loadTrendTerms();
    const terms = data.terms as Record<string, unknown>[];

    if (format === 'csv') {
      const csv = termsToCsv(terms);
      const filename = `aimfast-trends-${new Date().toISOString().slice(0, 10)}.csv`;
      return new NextResponse(csv, {
        headers: {
          'Content-Type': 'text/csv; charset=utf-8',
          'Content-Disposition': `attachment; filename="${filename}"`,
        },
      });
    }

    // Default: JSON
    const filename = `aimfast-trends-${new Date().toISOString().slice(0, 10)}.json`;
    return new NextResponse(JSON.stringify(data, null, 2), {
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
        'Content-Disposition': `attachment; filename="${filename}"`,
      },
    });
  }

  return NextResponse.json({ error: 'Invalid type. Use ?type=trends' }, { status: 400 });
}
