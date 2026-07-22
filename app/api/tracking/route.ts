import { NextResponse } from 'next/server';
import { auth } from '@/lib/auth';
import { prisma } from '@/lib/prisma';
import { getUserId } from '@/lib/session';

/** 每个用户的追踪目标上限 */
const MAX_TARGETS = 10;

/** 追踪目标类型 */
const VALID_TYPES = ['competitor', 'person', 'topic', 'tech', 'platform'];

// ═════ GET — 获取当前用户的所有追踪目标 ═════

export async function GET() {
  const session = await auth();
  const userId = getUserId(session);
  if (!userId) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const targets = await prisma.trackingTarget.findMany({
    where: { userId },
    orderBy: { createdAt: 'asc' },
  });

  return NextResponse.json({ targets });
}

// ═════ POST — 创建新追踪目标 ═════

export async function POST(request: Request) {
  const session = await auth();
  const userId = getUserId(session);
  if (!userId) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  let body: { name?: string; type?: string; aliases?: string[]; keywords?: string[]; notes?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  const name = body.name?.trim();
  if (!name || name.length > 200) {
    return NextResponse.json({ error: 'Name is required (max 200 chars).' }, { status: 400 });
  }

  const type = body.type || 'topic';
  if (!VALID_TYPES.includes(type)) {
    return NextResponse.json({ error: `Invalid type. Must be one of: ${VALID_TYPES.join(', ')}` }, { status: 400 });
  }

  // ── 上限检查 ──
  const count = await prisma.trackingTarget.count({
    where: { userId, status: 'active' },
  });
  if (count >= MAX_TARGETS) {
    return NextResponse.json({ error: `Max ${MAX_TARGETS} active tracking targets allowed.` }, { status: 409 });
  }

  // ── 去重检查 ──
  const existing = await prisma.trackingTarget.findUnique({
    where: { userId_name: { userId, name } },
  });
  if (existing) {
    return NextResponse.json({ error: 'A target with this name already exists.' }, { status: 409 });
  }

  const target = await prisma.trackingTarget.create({
    data: {
      userId,
      name,
      type,
      aliases: JSON.stringify(body.aliases ?? []),
      keywords: JSON.stringify(body.keywords ?? []),
      notes: body.notes ?? '',
      status: 'active',
    },
  });

  return NextResponse.json({ target }, { status: 201 });
}

// ═════ DELETE — 删除追踪目标 ═════

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

  const target = await prisma.trackingTarget.findUnique({ where: { id } });
  if (!target || target.userId !== userId) {
    return NextResponse.json({ error: 'Target not found.' }, { status: 404 });
  }

  await prisma.trackingTarget.delete({ where: { id } });
  return NextResponse.json({ ok: true });
}

// ═════ PATCH — 更新追踪目标 (暂停/恢复/修改) ═════

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

  let body: { status?: string; notes?: string; aliases?: string[]; keywords?: string[] };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  const target = await prisma.trackingTarget.findUnique({ where: { id } });
  if (!target || target.userId !== userId) {
    return NextResponse.json({ error: 'Target not found.' }, { status: 404 });
  }

  const data: Record<string, unknown> = {};
  if (body.status && ['active', 'paused'].includes(body.status)) {
    data.status = body.status;
  }
  if (body.notes !== undefined) {
    data.notes = body.notes;
  }
  if (body.aliases !== undefined) {
    data.aliases = JSON.stringify(body.aliases);
  }
  if (body.keywords !== undefined) {
    data.keywords = JSON.stringify(body.keywords);
  }

  if (Object.keys(data).length === 0) {
    return NextResponse.json({ error: 'No valid fields to update.' }, { status: 400 });
  }

  const updated = await prisma.trackingTarget.update({
    where: { id },
    data,
  });

  return NextResponse.json({ target: updated });
}
