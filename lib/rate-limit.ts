/**
 * 内存限流器 — 无外部依赖，适合单实例部署。
 * 限制：冷启动/多实例部署时计数器不共享。生产环境高流量时建议迁移到 Redis。
 */

interface RateLimitEntry {
  count: number;
  resetAt: number;
}

const store = new Map<string, RateLimitEntry>();

// 定期清理过期条目，防止内存泄漏
const CLEANUP_INTERVAL = 60_000; // 每分钟
let lastCleanup = Date.now();

function cleanup() {
  const now = Date.now();
  if (now - lastCleanup < CLEANUP_INTERVAL) return;
  lastCleanup = now;
  for (const [key, entry] of store) {
    if (now >= entry.resetAt) {
      store.delete(key);
    }
  }
}

/**
 * 检查是否触发限流。
 * @returns { allowed: boolean; remaining: number; resetAt: number }
 */
export function checkRateLimit(
  key: string,
  maxRequests: number,
  windowMs: number,
): { allowed: boolean; remaining: number; resetAt: number } {
  cleanup();

  const now = Date.now();
  const entry = store.get(key);

  if (!entry || now >= entry.resetAt) {
    // 首次请求或窗口已过期
    const resetAt = now + windowMs;
    store.set(key, { count: 1, resetAt });
    return { allowed: true, remaining: maxRequests - 1, resetAt };
  }

  entry.count++;

  if (entry.count > maxRequests) {
    return { allowed: false, remaining: 0, resetAt: entry.resetAt };
  }

  return { allowed: true, remaining: maxRequests - entry.count, resetAt: entry.resetAt };
}

/**
 * 重置某个 key 的限流计数（如登录成功后清除失败记录）。
 */
export function resetRateLimit(key: string): void {
  store.delete(key);
}

/**
 * 获取客户端 IP（兼容 Vercel / 反向代理）。
 */
export function getClientIP(request: Request): string {
  const forwarded = request.headers.get('x-forwarded-for');
  if (forwarded) {
    return forwarded.split(',')[0].trim();
  }
  return '127.0.0.1';
}
