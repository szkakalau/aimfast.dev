/**
 * 共享 Frontmatter 解析器。
 * 从 MDX/MD 文件中提取 YAML frontmatter 元数据。
 *
 * 修复了原实现中的冒号截断 bug：
 *   旧: title: "DeepSeek: 中国AI" → title 被截断为 "DeepSeek"
 *   新: 只在第一个冒号处分割，完整保留值中的冒号
 */
import { readFileSync } from 'node:fs';

export interface Frontmatter {
  title?: string;
  date?: string;
  summary?: string;
  [key: string]: string | undefined;
}

/**
 * 解析 YAML frontmatter 块（`---\n...\n---`）。
 * 使用 `slice(colonIdx + 1)` 而非 `split(':')`，保留值中的冒号。
 */
export function parseFrontmatter(source: string): Frontmatter {
  const fm: Frontmatter = {};
  const fmMatch = source.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!fmMatch) return fm;

  const lines = fmMatch[1].split('\n');
  for (const line of lines) {
    const colonIdx = line.indexOf(':');
    if (colonIdx <= 0) continue; // 跳过无冒号或冒号在开头的行
    const key = line.slice(0, colonIdx).trim();
    let val = line.slice(colonIdx + 1).trim();
    // 剥离首尾引号（单引号或双引号）
    if (
      (val.startsWith('"') && val.endsWith('"')) ||
      (val.startsWith("'") && val.endsWith("'"))
    ) {
      val = val.slice(1, -1);
    }
    fm[key] = val;
  }
  return fm;
}

/**
 * 解析 YAML frontmatter 并返回剥离元数据后的正文。
 */
export function parseFrontmatterWithBody(source: string): { fm: Frontmatter; body: string } {
  const fm = parseFrontmatter(source);
  const fmMatch = source.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?/);
  const body = fmMatch ? source.slice(fmMatch[0].length) : source;
  return { fm, body };
}

/**
 * 从 MDX 源中提取纯文本正文（去除 frontmatter）。
 */
export function extractBody(source: string): string {
  return source.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n?/, '');
}

/**
 * 安全读取文件并解析 frontmatter。
 * 文件不存在时返回 undefined。
 */
export function readFrontmatter(filePath: string): Frontmatter | undefined {
  try {
    const source = readFileSync(filePath, 'utf-8');
    return parseFrontmatter(source);
  } catch {
    return undefined;
  }
}
