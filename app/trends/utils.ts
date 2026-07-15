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

// ── Tracking (localStorage-backed watchlist) ──

const TRACKED_KEY = 'aimfast_tracked';
const MAX_TRACKED = 50;

export interface TrackedItem {
  /** Term ID, format "trend-{slug}" — matches TrendTerm.id */
  id: string;
  /** ISO date string when the item was added to tracking */
  addedAt: string;
}

/**
 * Read the user's tracked items from localStorage.
 * Returns empty array on any failure (corrupted JSON, localStorage unavailable).
 */
export function getTrackedItems(): TrackedItem[] {
  try {
    const raw = localStorage.getItem(TRACKED_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (item: unknown): item is TrackedItem =>
        typeof item === 'object' && item !== null && typeof (item as TrackedItem).id === 'string',
    );
  } catch {
    return [];
  }
}

/**
 * Add a term ID to the tracking list.
 * Returns the updated list, or null if the item was already tracked or the list is full.
 */
export function addTrackedItem(id: string): TrackedItem[] | null {
  const items = getTrackedItems();
  if (items.some((item) => item.id === id)) return null; // already tracked
  if (items.length >= MAX_TRACKED) return null; // at limit
  const updated = [...items, { id, addedAt: new Date().toISOString() }];
  try {
    localStorage.setItem(TRACKED_KEY, JSON.stringify(updated));
  } catch {
    return null; // localStorage full or unavailable
  }
  return updated;
}

/**
 * Remove a term ID from the tracking list.
 * Returns the updated list, or null if the item was not found.
 */
export function removeTrackedItem(id: string): TrackedItem[] | null {
  const items = getTrackedItems();
  const idx = items.findIndex((item) => item.id === id);
  if (idx === -1) return null; // not tracked
  const updated = [...items.slice(0, idx), ...items.slice(idx + 1)];
  try {
    localStorage.setItem(TRACKED_KEY, JSON.stringify(updated));
  } catch {
    return null;
  }
  return updated;
}

/**
 * Check if a term ID is currently tracked.
 */
export function isTracked(id: string): boolean {
  return getTrackedItems().some((item) => item.id === id);
}

// ── Decision Score (used by Dashboard Watchlist) ──

const SCORE_DELTA_WEIGHT = 0.6;
const MENTION_DELTA_WEIGHT = 0.4;
const SCORE_NORMALIZE_FACTOR = 100;

/**
 * Compute a composite decision score from 7-day trend deltas.
 * Weights: scoreDelta (60%) + mentionDelta (40%), both normalized.
 * Returns null when history data is unavailable.
 */
export function computeDecisionScore(today: TrendTerm, history: TrendTerm | undefined): number | null {
  if (!history) return null;
  const scoreDelta = (today.score - history.score) / SCORE_NORMALIZE_FACTOR;
  const prevMentions = Math.max(history.total_mentions, 1);
  const mentionDelta = Math.max(-1, Math.min(1, (today.total_mentions - history.total_mentions) / prevMentions));
  return scoreDelta * SCORE_DELTA_WEIGHT + mentionDelta * MENTION_DELTA_WEIGHT;
}
