/**
 * Post-build fix: 将中文页面的 <html lang="en"> 替换为 <html lang="zh-CN">
 * 根布局默认 lang="en"；构建后此脚本将 /zh/ 路径下的页面修正为 zh-CN。
 *
 * Usage: node scripts/fix-en-lang.mjs
 */
import { readFileSync, writeFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';

const OUT_DIR = join(process.cwd(), 'out');
const SEP = join('a', 'b').includes('\\') ? '\\' : '/';

function findZhPages(dir) {
  const results = [];
  try {
    const entries = readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = join(dir, entry.name);
      if (entry.isDirectory()) {
        results.push(...findZhPages(fullPath));
      } else if (entry.name === 'index.html') {
        // 中文页面：路径中包含 /zh/ 目录段
        if (fullPath.includes(`${SEP}zh${SEP}`)) {
          results.push(fullPath);
        }
      }
    }
  } catch {
    // out/ doesn't exist yet — skip
  }
  return results;
}

const pages = findZhPages(OUT_DIR);

if (pages.length === 0) {
  console.log('[fix-zh-lang] No ZH pages found in out/ — skipping');
  process.exit(0);
}

let fixed = 0;
for (const filePath of pages) {
  try {
    const html = readFileSync(filePath, 'utf-8');
    if (html.includes('lang="en"')) {
      const fixedHtml = html.replace(/lang="en"/g, 'lang="zh-CN"');
      writeFileSync(filePath, fixedHtml, 'utf-8');
      fixed++;
      console.log(`[fix-zh-lang] Fixed: ${filePath}`);
    }
  } catch (err) {
    console.error(`[fix-zh-lang] Error: ${filePath} — ${err.message}`);
  }
}

console.log(`[fix-zh-lang] Done: ${fixed} ZH page(s) fixed`);
