/**
 * 路径安全验证 —— 防止路径遍历攻击（directory traversal）。
 * 所有从 URL 参数读取并拼接文件路径的地方必须通过此验证。
 */
import { join, resolve } from 'node:path';

/**
 * 验证 slug/date 等 URL 参数不包含路径遍历字符。
 * 返回 true 表示安全，false 表示存在攻击风险。
 */
export function isValidPathSegment(segment: string): boolean {
  if (!segment || segment.length === 0 || segment.length > 255) return false;
  // 禁止路径遍历字符和空字节
  if (segment.includes('..')) return false;
  if (segment.includes('/')) return false;
  if (segment.includes('\\')) return false;
  if (segment.includes('\0')) return false;
  return true;
}

/**
 * 安全解析文件路径，确保最终路径在指定的基础目录内。
 * 如果路径不安全或超出基础目录，返回 null。
 */
export function safeResolve(baseDir: string, ...segments: string[]): string | null {
  for (const seg of segments) {
    if (!isValidPathSegment(seg)) return null;
  }
  const resolved = resolve(join(baseDir, ...segments));
  const base = resolve(baseDir);
  if (!resolved.startsWith(base + '\\') && !resolved.startsWith(base + '/') && resolved !== base) {
    return null;
  }
  return resolved;
}
