import { describe, it, expect, beforeEach, vi } from 'vitest';
import { checkRateLimit, resetRateLimit, getClientIP } from '@/lib/rate-limit';

// rate-limit 使用模块级 Map，测试间需清理
// 通过调用 resetRateLimit 清理测试中使用的 key

describe('checkRateLimit', () => {
  beforeEach(() => {
    // 清理测试 key
    resetRateLimit('test:user');
    resetRateLimit('test:burst');
  });

  it('首次请求应该允许', () => {
    const result = checkRateLimit('test:user', 5, 60_000);
    expect(result.allowed).toBe(true);
    expect(result.remaining).toBe(4);
  });

  it('在限制范围内连续请求应该允许', () => {
    for (let i = 0; i < 5; i++) {
      const result = checkRateLimit('test:user', 5, 60_000);
      expect(result.allowed).toBe(true);
      expect(result.remaining).toBe(4 - i);
    }
  });

  it('超过限制后应该拒绝', () => {
    // 消耗 5 次配额
    for (let i = 0; i < 5; i++) {
      checkRateLimit('test:user', 5, 60_000);
    }
    // 第 6 次应被拒绝
    const result = checkRateLimit('test:user', 5, 60_000);
    expect(result.allowed).toBe(false);
    expect(result.remaining).toBe(0);
  });

  it('resetAt 应该在未来时间', () => {
    const result = checkRateLimit('test:user', 5, 60_000);
    expect(result.resetAt).toBeGreaterThan(Date.now());
    expect(result.resetAt).toBeLessThanOrEqual(Date.now() + 60_000);
  });

  it('不同 key 独立计数', () => {
    // 消耗 key-A 全部配额
    for (let i = 0; i < 5; i++) {
      checkRateLimit('test:burst', 5, 60_000);
    }
    // key-B 不应受影响
    const result = checkRateLimit('test:user', 5, 60_000);
    expect(result.allowed).toBe(true);
    expect(result.remaining).toBe(4);
  });

  it('窗口过期后重置计数', () => {
    const windowMs = 100; // 100ms 窗口，方便测试

    // 消耗所有配额
    for (let i = 0; i < 3; i++) {
      checkRateLimit('test:user', 3, windowMs);
    }
    expect(checkRateLimit('test:user', 3, windowMs).allowed).toBe(false);

    // 等待窗口过期
    vi.useFakeTimers();
    // 重新设置（因为上面的调用使用了真实时间）
    resetRateLimit('test:user');
    for (let i = 0; i < 3; i++) {
      checkRateLimit('test:user', 3, windowMs);
    }
    expect(checkRateLimit('test:user', 3, windowMs).allowed).toBe(false);

    // 快进到窗口过期后
    vi.advanceTimersByTime(windowMs + 1);

    // 应该被允许
    const result = checkRateLimit('test:user', 3, windowMs);
    expect(result.allowed).toBe(true);
    expect(result.remaining).toBe(2); // 3 - 1

    vi.useRealTimers();
  });
});

describe('resetRateLimit', () => {
  it('重置后重新允许请求', () => {
    // 消耗所有配额
    for (let i = 0; i < 5; i++) {
      checkRateLimit('test:user', 5, 60_000);
    }
    expect(checkRateLimit('test:user', 5, 60_000).allowed).toBe(false);

    // 重置
    resetRateLimit('test:user');

    // 应重新允许
    const result = checkRateLimit('test:user', 5, 60_000);
    expect(result.allowed).toBe(true);
    expect(result.remaining).toBe(4);
  });

  it('重置不存在的 key 不报错', () => {
    expect(() => resetRateLimit('nonexistent')).not.toThrow();
  });
});

describe('getClientIP', () => {
  it('从 x-forwarded-for 提取第一个 IP', () => {
    const req = new Request('https://example.com/api/test', {
      headers: { 'x-forwarded-for': '203.0.113.1, 10.0.0.1, 10.0.0.2' },
    });
    expect(getClientIP(req)).toBe('203.0.113.1');
  });

  it('无 x-forwarded-for 返回 fallback', () => {
    const req = new Request('https://example.com/api/test');
    expect(getClientIP(req)).toBe('127.0.0.1');
  });

  it('单个 IP 直接返回', () => {
    const req = new Request('https://example.com/api/test', {
      headers: { 'x-forwarded-for': '203.0.113.42' },
    });
    expect(getClientIP(req)).toBe('203.0.113.42');
  });
});
