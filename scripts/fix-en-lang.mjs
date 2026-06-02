/**
 * Post-build fix: 将英文页面的 <html lang="zh-CN"> 替换为 <html lang="en">
 * Next.js 静态导出不支持按路由覆盖根布局的 html lang 属性，
 * 此脚本在构建后修正 out/ 目录中所有英文页面的 lang 属性。
 *
 * Usage: node scripts/fix-en-lang.mjs
 */
import { readFileSync, writeFileSync, readdirSync } from 'node:fs';
import { join, dirname } from 'node:path';

const OUT_DIR = join(process.cwd(), 'out');

function findEnglishPages(dir) {
  const results = [];
  try {
    const entries = readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = join(dir, entry.name);
      if (entry.isDirectory()) {
        // Follow directories — detect English pages by /en/ path segment
        results.push(...findEnglishPages(fullPath));
      } else if (entry.name === 'index.html') {
        // An HTML file is English if its directory path ends with /en
        if (dirname(fullPath).endsWith('/en') || dirname(fullPath).endsWith('\\en')) {
          results.push(fullPath);
        }
      }
    }
  } catch {
    // out/ doesn't exist yet — skip
  }
  return results;
}

const pages = findEnglishPages(OUT_DIR);

if (pages.length === 0) {
  console.log('[fix-en-lang] No English pages found in out/ — skipping');
  process.exit(0);
}

let fixed = 0;
for (const filePath of pages) {
  try {
    const html = readFileSync(filePath, 'utf-8');
    if (html.includes('lang="zh-CN"')) {
      const fixedHtml = html.replace(/lang="zh-CN"/g, 'lang="en"');
      writeFileSync(filePath, fixedHtml, 'utf-8');
      fixed++;
      console.log(`[fix-en-lang] Fixed: ${filePath}`);
    }
  } catch (err) {
    console.error(`[fix-en-lang] Error: ${filePath} — ${err.message}`);
  }
}

console.log(`[fix-en-lang] Done: ${fixed} English page(s) fixed`);
