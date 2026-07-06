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

export function stageLabel(stage: string): string {
  const map: Record<string, string> = {
    nascent: 'Nascent (0-7d)',
    emergent: 'Emergent (8-30d)',
    validating: 'Validating (31-90d)',
    rising: 'Rising (90d+)',
  };
  return map[stage] || stage;
}
