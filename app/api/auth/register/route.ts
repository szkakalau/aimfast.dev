import { NextResponse } from 'next/server';
import bcrypt from 'bcryptjs';
import { prisma } from '@/lib/prisma';
import { checkRateLimit, getClientIP } from '@/lib/rate-limit';

const REGISTER_LIMIT = 5;       // 每个 IP 最多 5 次
const REGISTER_WINDOW = 15 * 60 * 1000; // 15 分钟窗口

export async function POST(request: Request) {
  try {
    // 限流检查
    const ip = getClientIP(request);
    const rateLimit = checkRateLimit(`register:${ip}`, REGISTER_LIMIT, REGISTER_WINDOW);
    if (!rateLimit.allowed) {
      return NextResponse.json(
        { error: 'Too many registration attempts. Please try again later.' },
        { status: 429 },
      );
    }

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
    console.error('Register failed');
    return NextResponse.json({ error: 'Registration failed. Please try again.' }, { status: 500 });
  }
}
