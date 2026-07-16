/** Shared UI labels for trend terms — single source of truth for stage names. */

export type Locale = 'en' | 'zh';

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

export function getStageLabel(stage: string, locale: Locale): string {
  return locale === 'zh' ? stageLabelZh(stage) : stageLabel(stage);
}

export const STAGES = ['all', 'nascent', 'emergent', 'validating', 'rising'] as const;
export type StageFilter = (typeof STAGES)[number];

export type SortKey = 'builder' | 'score' | 'opportunity' | 'revenue' | 'newest' | 'mentions';

export const SORT_OPTIONS: { key: SortKey; label: string; labelZh: string }[] = [
  { key: 'builder', label: 'Builder Score', labelZh: 'Builder 评分' },
  { key: 'score', label: 'Score ↓', labelZh: '综合评分 ↓' },
  { key: 'opportunity', label: 'Opportunity ↓', labelZh: '机会评分 ↓' },
  { key: 'revenue', label: 'Revenue ↓', labelZh: '收入潜力 ↓' },
  { key: 'newest', label: 'Newest', labelZh: '最新' },
  { key: 'mentions', label: 'Most Mentioned', labelZh: '最多提及' },
];

export interface TrendLabels {
  all: string;
  allCategories: string;
  aiFocus: string;
  allTypes: string;
  results: string;
  forBuilders: string;
  general: string;
  noMatches: string;
  stageFilterLabel: Record<string, string>;
  sortLabels: Record<string, string>;
  emptyMessages: {
    aiFocus: string;
    category: (cat: string) => string;
    productType: (pt: string) => string;
    default: string;
  };
}

export function getLabels(locale: Locale): TrendLabels {
  if (locale === 'zh') {
    return {
      all: '全部',
      allCategories: '全部分类',
      aiFocus: '🤖 AI 聚焦',
      allTypes: '全部类型',
      results: '条结果',
      forBuilders: '面向开发者',
      general: '通用排序',
      noMatches: '没有匹配项',
      stageFilterLabel: { all: '全部', nascent: '萌芽期 (0-7天)', emergent: '涌现期 (8-30天)', validating: '验证期 (31-90天)', rising: '上升期 (90天+)' },
      sortLabels: Object.fromEntries(SORT_OPTIONS.map(o => [o.key, o.labelZh])),
      emptyMessages: {
        aiFocus: '当前阶段没有 AI 相关术语。请尝试其他阶段或关闭 AI 聚焦。',
        category: (cat: string) => `当前阶段没有"${cat}"相关术语。请尝试其他分类或阶段。`,
        productType: (pt: string) => `当前阶段没有"${pt}"类型的机会。请尝试其他产品类型。`,
        default: '当前阶段没有术语。请尝试其他筛选条件。',
      },
    };
  }
  return {
    all: 'All',
    allCategories: 'All Categories',
    aiFocus: '🤖 AI Focus',
    allTypes: 'All Types',
    results: 'results',
    forBuilders: 'For Builders',
    general: 'General',
    noMatches: 'No matches',
    stageFilterLabel: { all: 'All', nascent: 'Nascent (0-7d)', emergent: 'Emergent (8-30d)', validating: 'Validating (31-90d)', rising: 'Rising (90d+)' },
    sortLabels: Object.fromEntries(SORT_OPTIONS.map(o => [o.key, o.label])),
    emptyMessages: {
      aiFocus: 'No AI terms in this stage. Try a different stage or turn off AI Focus.',
      category: (cat: string) => `No "${cat}" terms in this stage. Try another category or stage.`,
      productType: (pt: string) => `No "${pt}" opportunities in this stage. Try another product type.`,
      default: 'No terms in this stage. Try another filter.',
    },
  };
}
