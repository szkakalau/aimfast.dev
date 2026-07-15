import { describe, it, expect, beforeEach } from 'vitest';
import { stageLabel, STAGES } from '@/app/trends/labels';
import { normalizeCategory, builderScore, getTrackedItems, addTrackedItem, removeTrackedItem, isTracked, computeDecisionScore } from '@/app/trends/utils';
import type { TrendTerm } from '@/app/trends/types';

// ── labels.ts ──

describe('stageLabel', () => {
  it('returns full label for known stages', () => {
    expect(stageLabel('nascent')).toBe('Nascent (0-7d)');
    expect(stageLabel('emergent')).toBe('Emergent (8-30d)');
    expect(stageLabel('validating')).toBe('Validating (31-90d)');
    expect(stageLabel('rising')).toBe('Rising (90d+)');
  });

  it('returns raw value for unknown stages', () => {
    expect(stageLabel('unknown')).toBe('unknown');
    expect(stageLabel('')).toBe('');
  });
});

describe('STAGES', () => {
  it('has all 5 expected values', () => {
    expect(STAGES).toEqual(['all', 'nascent', 'emergent', 'validating', 'rising']);
  });
});

// ── utils.ts ──

describe('normalizeCategory', () => {
  it('title-cases lowercased category', () => {
    expect(normalizeCategory('product')).toBe('Product');
    expect(normalizeCategory('hottopic')).toBe('Hottopic');
  });

  it('preserves already title-cased category', () => {
    expect(normalizeCategory('AI/LLM')).toBe('AI/LLM');
    expect(normalizeCategory('DevTools')).toBe('DevTools');
  });

  it('handles empty/whitespace', () => {
    expect(normalizeCategory('')).toBe('');
    expect(normalizeCategory('   ')).toBe('');
  });
});

describe('builderScore', () => {
  const full: TrendTerm = {
    id: 'trend-test',
    canonical: 'Test Term',
    aliases: [],
    first_seen: '2026-07-01',
    last_seen: '2026-07-15',
    stage: 'emergent',
    score: 80,
    source_count: 5,
    total_mentions: 100,
    sources: ['Reddit', 'GitHub'],
    growth_pct: 50,
    category: 'DevTools',
    tags: ['test'],
    summary_zh: 'test',
    summary_en: 'test',
    research_md_path: 'content/trends/test.md',
    opportunity_score: 75,
    market_score: 80,
    competition_score: 30,
    demand_score: 70,
    seo_difficulty: 40,
    suggested_products: ['SaaS'],
    estimated_dev_days: 7,
    revenue_potential: 4,
  };

  it('computes correct score with full data', () => {
    // opp=75, blue=70, rev=4, days=7 → (75*70*4)/7 = 3000
    expect(builderScore(full)).toBe(3000);
  });

  it('returns 0 when no opportunity data', () => {
    const bare: TrendTerm = {
      ...full,
      opportunity_score: undefined,
      competition_score: undefined,
      revenue_potential: undefined,
      estimated_dev_days: undefined,
    };
    // opp=0 → result=0
    expect(builderScore(bare)).toBe(0);
  });

  it('uses defaults for missing competition/revenue/dev_days', () => {
    const partial: TrendTerm = {
      ...full,
      opportunity_score: 60,
      competition_score: undefined, // → 50, blue=50
      revenue_potential: undefined, // → 1
      estimated_dev_days: undefined, // → 14
    };
    // opp=60, blue=50, rev=1, days=14 → (60*50*1)/14 = 214.29 → 214
    expect(builderScore(partial)).toBe(214);
  });

  it('ensures dev_days never drops below 1', () => {
    const fast: TrendTerm = { ...full, estimated_dev_days: 0 };
    // days = max(0, 1) = 1
    expect(builderScore(fast)).toBe(21000); // 75*70*4/1
  });
});

// ── Tracking helpers ──

describe('getTrackedItems', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('returns empty array when no items stored', () => {
    expect(getTrackedItems()).toEqual([]);
  });

  it('returns parsed items from localStorage', () => {
    const items = [{ id: 'trend-test', addedAt: '2026-07-15T00:00:00.000Z' }];
    localStorage.setItem('aimfast_tracked', JSON.stringify(items));
    expect(getTrackedItems()).toEqual(items);
  });

  it('returns empty array on corrupted JSON', () => {
    localStorage.setItem('aimfast_tracked', '{broken');
    expect(getTrackedItems()).toEqual([]);
  });

  it('returns empty array when stored value is not an array', () => {
    localStorage.setItem('aimfast_tracked', '"not-an-array"');
    expect(getTrackedItems()).toEqual([]);
  });

  it('filters out malformed entries', () => {
    localStorage.setItem('aimfast_tracked', JSON.stringify([{ id: 'trend-ok', addedAt: 'x' }, { bad: true }, null, 'string']));
    const result = getTrackedItems();
    expect(result).toHaveLength(1);
    expect(result[0].id).toBe('trend-ok');
  });
});

describe('addTrackedItem', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('adds a new item and returns updated list', () => {
    const result = addTrackedItem('trend-new');
    expect(result).not.toBeNull();
    expect(result!.length).toBe(1);
    expect(result![0].id).toBe('trend-new');
    expect(result![0].addedAt).toBeTruthy();
  });

  it('persists to localStorage', () => {
    addTrackedItem('trend-new');
    const stored = JSON.parse(localStorage.getItem('aimfast_tracked')!);
    expect(stored).toHaveLength(1);
    expect(stored[0].id).toBe('trend-new');
  });

  it('returns null for duplicate id', () => {
    addTrackedItem('trend-dup');
    expect(addTrackedItem('trend-dup')).toBeNull();
    expect(getTrackedItems()).toHaveLength(1);
  });

  it('returns null when at limit (50 items)', () => {
    for (let i = 0; i < 50; i++) {
      addTrackedItem(`trend-${i}`);
    }
    expect(addTrackedItem('trend-overflow')).toBeNull();
    expect(getTrackedItems()).toHaveLength(50);
  });
});

describe('removeTrackedItem', () => {
  beforeEach(() => {
    localStorage.clear();
    addTrackedItem('trend-a');
    addTrackedItem('trend-b');
  });

  it('removes an existing item and returns updated list', () => {
    const result = removeTrackedItem('trend-a');
    expect(result).not.toBeNull();
    expect(result!.length).toBe(1);
    expect(result![0].id).toBe('trend-b');
  });

  it('persists removal to localStorage', () => {
    removeTrackedItem('trend-a');
    expect(getTrackedItems()).toHaveLength(1);
  });

  it('returns null for non-existent id', () => {
    expect(removeTrackedItem('trend-ghost')).toBeNull();
    expect(getTrackedItems()).toHaveLength(2);
  });
});

describe('isTracked', () => {
  beforeEach(() => {
    localStorage.clear();
    addTrackedItem('trend-tracked');
  });

  it('returns true for tracked id', () => {
    expect(isTracked('trend-tracked')).toBe(true);
  });

  it('returns false for untracked id', () => {
    expect(isTracked('trend-other')).toBe(false);
  });
});

// ── computeDecisionScore ──

describe('computeDecisionScore', () => {
  const base: TrendTerm = {
    id: 'trend-test',
    canonical: 'Test Term',
    aliases: [],
    first_seen: '2026-07-01',
    last_seen: '2026-07-15',
    stage: 'emergent',
    score: 80,
    source_count: 5,
    total_mentions: 100,
    sources: ['Reddit'],
    growth_pct: 50,
    category: 'DevTools',
    tags: [],
    summary_zh: '',
    summary_en: '',
    research_md_path: '',
    opportunity_score: 75,
    market_score: 80,
    competition_score: 30,
    demand_score: 70,
    seo_difficulty: 40,
    suggested_products: ['SaaS'],
    estimated_dev_days: 7,
    revenue_potential: 4,
  };

  it('returns null when no history data', () => {
    expect(computeDecisionScore(base, undefined)).toBeNull();
  });

  it('returns 0 when no changes', () => {
    const hist = { ...base };
    expect(computeDecisionScore(base, hist)).toBe(0);
  });

  it('positive when score and mentions both grow', () => {
    const hist = { ...base, score: 60, total_mentions: 40 };
    // scoreDelta = 20/100 = 0.2
    // mentionDelta = (100-40)/max(40,1) = 60/40 = 1.0 (clamped to 1.0)
    // result = 0.2*0.6 + 1.0*0.4 = 0.12 + 0.4 = 0.52
    const result = computeDecisionScore(base, hist);
    expect(result).toBeCloseTo(0.52, 5);
  });

  it('negative when score drops', () => {
    const hist = { ...base, score: 120 };
    // scoreDelta = -40/100 = -0.4
    // mentionDelta = 0
    // result = -0.4*0.6 + 0*0.4 = -0.24
    const result = computeDecisionScore(base, hist);
    expect(result).toBeCloseTo(-0.24, 5);
  });

  it('handles zero history mentions gracefully', () => {
    const hist = { ...base, total_mentions: 0, score: 80 };
    // scoreDelta = 0
    // prevMentions = max(0, 1) = 1
    // mentionDelta = (100-0)/1 = 100 → clamped to 1.0
    // result = 0 + 1.0*0.4 = 0.4
    const result = computeDecisionScore(base, hist);
    expect(result).toBeCloseTo(0.4, 5);
  });

  it('clamps mentionDelta to [-1, 1]', () => {
    // Mentions 10× growth → should clamp at 1.0
    const hist = { ...base, score: 80, total_mentions: 5 };
    // mentionDelta = (100-5)/5 = 19 → clamped to 1.0
    // result = 0 + 1.0*0.4 = 0.4
    expect(computeDecisionScore(base, hist)).toBeCloseTo(0.4, 5);
  });
});
