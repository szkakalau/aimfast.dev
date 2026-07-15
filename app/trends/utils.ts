import type { TrendTerm } from './types';

/** Normalize category string to title case (defense in depth — data should already be normalized). */
export function normalizeCategory(cat: string): string {
  const c = cat?.trim();
  if (!c) return '';
  return c.charAt(0).toUpperCase() + c.slice(1);
}

/**
 * Builder Score — composite metric for indie developers.
 * Weights: opportunity × blue_ocean(100 − competition) × revenue / dev_days.
 * Terms without opportunity data return 0 (sorted to bottom).
 */
export function builderScore(t: TrendTerm): number {
  const opp = t.opportunity_score ?? 0;
  const blue = 100 - (t.competition_score ?? 50);
  const rev = t.revenue_potential ?? 1;
  const days = Math.max(t.estimated_dev_days ?? 14, 1);
  return Math.round((opp * blue * rev) / days);
}
