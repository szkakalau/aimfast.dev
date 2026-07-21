import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import type { TrendTerm, TrendTermsData } from './types';

export function getAllTrendTerms(): TrendTermsData {
  try {
    const raw = readFileSync(
      join(process.cwd(), 'tracking', 'trend_terms.json'),
      'utf-8',
    );
    return JSON.parse(raw) as TrendTermsData;
  } catch {
    return { updated_at: '', terms: [] };
  }
}

export function getTrendTerm(slug: string): TrendTerm | null {
  const termId = `trend-${slug}`;
  const data = getAllTrendTerms();
  return data.terms.find((t) => t.id === termId) || null;
}

export function getResearchContent(path: string): string {
  try {
    const fullPath = join(process.cwd(), path);
    if (!existsSync(fullPath)) return '';
    return readFileSync(fullPath, 'utf-8');
  } catch {
    return '';
  }
}

/** Returns true if the body text is predominantly Chinese (CJK > 30% of alphanum+CJK chars). */
function isChineseText(text: string): boolean {
  const cjk = (text.match(/[一-鿿㐀-䶿]/g) || []).length;
  const alpha = (text.match(/[a-zA-Z0-9]/g) || []).length;
  const total = cjk + alpha;
  if (total === 0) return false;
  return cjk / total > 0.3;
}

export function getResearchContentEn(path: string): string {
  // Try English variant first (e.g., content/trends/homegames-en.md)
  const enPath = path.replace(/\.md$/, '-en.md');
  const enContent = getResearchContent(enPath);
  if (enContent) {
    const bodyOnly = enContent.replace(/^---[\s\S]*?---\n*/, '').trim();
    if (!isChineseText(bodyOnly)) return enContent;
    // EN file exists but LLM-generated content is Chinese — show it anyway
    // with a language note prepended (better than empty "not yet generated")
    const frontmatterEnd = enContent.indexOf('---\n', 4);
    if (frontmatterEnd !== -1) {
      const before = enContent.slice(0, frontmatterEnd + 4);
      const after = enContent.slice(frontmatterEnd + 4);
      return before + '\n> ⚠️ The English version of this report is being regenerated. Showing the available version below.\n\n' + after;
    }
    return enContent;
  }
  // Fall back to original, but reject if it's also Chinese
  const origContent = getResearchContent(path);
  if (origContent) {
    const bodyOnly = origContent.replace(/^---[\s\S]*?---\n*/, '').trim();
    if (!isChineseText(bodyOnly)) return origContent;
    // Original is also Chinese — show it with a note rather than nothing
    const frontmatterEnd = origContent.indexOf('---\n', 4);
    if (frontmatterEnd !== -1) {
      const before = origContent.slice(0, frontmatterEnd + 4);
      const after = origContent.slice(frontmatterEnd + 4);
      return before + '\n> ⚠️ The English version of this report is being regenerated. Showing the available version below.\n\n' + after;
    }
    return origContent;
  }
  return '';
}

export function getTrendStats(): { total: number; withResearch: number; totalSources: number } {
  try {
    const data = getAllTrendTerms();
    const terms = data.terms || [];
    const withResearch = terms.filter((t) => {
      if (!t.research_md_path) return false;
      const fullPath = join(process.cwd(), t.research_md_path);
      return existsSync(fullPath);
    }).length;
    const totalSources = new Set(terms.flatMap((t) => t.sources || [])).size;
    return { total: terms.length, withResearch, totalSources };
  } catch {
    return { total: 0, withResearch: 0, totalSources: 0 };
  }
}

export function stageLabel(stage: string): string {
  const map: Record<string, string> = {
    nascent: 'Nascent',
    emergent: 'Emergent',
    validating: 'Validating',
    rising: 'Rising',
  };
  return map[stage] || stage;
}

export function stageLabelZh(stage: string): string {
  const map: Record<string, string> = {
    nascent: '萌芽期',
    emergent: '涌现期',
    validating: '验证期',
    rising: '上升期',
  };
  return map[stage] || stage;
}

export function stagePct(stage: string): string {
  const map: Record<string, string> = {
    nascent: 'brand new',
    emergent: 'recent',
    validating: 'established',
    rising: 'mature',
  };
  return map[stage] || '';
}

/**
 * Lightweight HTML sanitizer for LLM-generated markdown content.
 * Strips dangerous tags and event handlers while preserving markdown-formatted output
 * (headings, lists, links, code blocks, etc. are rendered by `marked` as safe HTML).
 */
export function sanitizeTrendHtml(html: string): string {
  return html
    // Strip <script>...</script>
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
    // Strip <iframe>...</iframe>
    .replace(/<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>/gi, '')
    // Strip <style>...</style>
    .replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, '')
    // Strip <object>...</object>
    .replace(/<object\b[^<]*(?:(?!<\/object>)<[^<]*)*<\/object>/gi, '')
    // Strip <embed ...>
    .replace(/<embed\b[^>]*\/?>/gi, '')
    // Strip <form>...</form>
    .replace(/<form\b[^<]*(?:(?!<\/form>)<[^<]*)*<\/form>/gi, '')
    // Strip <meta ...> (self-closing)
    .replace(/<meta\b[^>]*\/?>/gi, '')
    // Strip <base ...> (self-closing)
    .replace(/<base\b[^>]*\/?>/gi, '')
    // Strip inline style attributes (potential defacement)
    .replace(/\s+style\s*=\s*"[^"]*"/gi, '')
    .replace(/\s+style\s*=\s*'[^']*'/gi, '')
    // Strip inline JS event handlers
    .replace(/\s+on\w+\s*=\s*"[^"]*"/gi, '')
    .replace(/\s+on\w+\s*=\s*'[^']*'/gi, '')
    .replace(/\s+on\w+\s*=\s*[^\s>]+/gi, '');
}
