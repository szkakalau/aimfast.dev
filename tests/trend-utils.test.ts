import { describe, it, expect } from 'vitest';
import { stageLabel, STAGES } from '@/app/trends/labels';
import { normalizeCategory, builderScore } from '@/app/trends/utils';
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
