import type { TrendTerm } from './types';

/** Normalize category string to title case (defense in depth — data should already be normalized). */
export function normalizeCategory(cat: string): string {
  const c = cat?.trim();
  if (!c) return '';
  return c.charAt(0).toUpperCase() + c.slice(1);
}

const BLUE_OCEAN_MAX = 100;
const DEFAULT_COMPETITION = 50;
const DEFAULT_REVENUE = 1;
const DEFAULT_DEV_DAYS = 14;

/**
 * Builder Score — composite metric for indie developers.
 * Weights: opportunity × blue_ocean(BLUE_OCEAN_MAX − competition) × revenue / dev_days.
 * Terms without opportunity data return 0 (sorted to bottom).
 */
export function builderScore(t: TrendTerm): number {
  const opp = t.opportunity_score ?? 0;
  const blue = BLUE_OCEAN_MAX - (t.competition_score ?? DEFAULT_COMPETITION);
  const rev = t.revenue_potential ?? DEFAULT_REVENUE;
  const days = Math.max(t.estimated_dev_days ?? DEFAULT_DEV_DAYS, 1);
  return Math.round((opp * blue * rev) / days);
}
