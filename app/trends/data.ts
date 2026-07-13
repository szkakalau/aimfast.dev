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

export function getResearchContentEn(path: string): string {
  // Try English variant first (e.g., content/trends/homegames-en.md)
  const enPath = path.replace(/\.md$/, '-en.md');
  const enContent = getResearchContent(enPath);
  if (enContent) return enContent;
  // Fall back to original
  return getResearchContent(path);
}

export function getTrendStats(): { total: number; withResearch: number; totalSources: number } {
  try {
    const data = getAllTrendTerms();
    const terms = data.terms || [];
    const withResearch = terms.filter((t) => t.research_md_path && t.score >= 60).length;
    const totalSources = new Set(terms.flatMap((t) => t.sources || [])).size;
    return { total: terms.length, withResearch, totalSources };
  } catch {
    return { total: 0, withResearch: 0, totalSources: 0 };
  }
}

export function stageLabel(stage: string): string {
  const map: Record<string, string> = {
    nascent: 'Nascent (0-7d)',
    emergent: 'Emergent (8-30d)',
    validating: 'Validating (31-90d)',
    rising: 'Rising (90d+)',
  };
  return map[stage] || stage;
}

export function stageLabelZh(stage: string): string {
  const map: Record<string, string> = {
    nascent: '萌芽期 (0-7天)',
    emergent: '涌现期 (8-30天)',
    validating: '验证期 (31-90天)',
    rising: '上升期 (90天+)',
  };
  return map[stage] || stage;
}

export function stagePct(stage: string): string {
  const map: Record<string, string> = {
    nascent: '0–7',
    emergent: '8–30',
    validating: '31–90',
    rising: '90+',
  };
  return map[stage] || '';
}
