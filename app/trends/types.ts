export interface TrendTerm {
  id: string;
  canonical: string;
  canonical_zh?: string;                // Chinese display name (empty for English-only terms)
  aliases: string[];
  first_seen: string;
  last_seen: string;
  stage: 'nascent' | 'emergent' | 'validating' | 'rising';
  score: number;
  source_count: number;
  total_mentions: number;
  sources: string[];
  growth_pct: number;
  category: string;
  tags: string[];
  summary_zh: string;
  summary_en: string;
  research_md_path: string;

  // ── Opportunity Analysis (v2) ──
  opportunity_score?: number;         // 0-100 — 综合机会评分
  market_score?: number;              // 0-100 — 市场规模/潜力
  competition_score?: number;         // 0-100 — 竞争程度（越低=蓝海）
  demand_score?: number;              // 0-100 — 痛点强度
  seo_difficulty?: number;            // 0-100 — SEO 难度（越低越容易）
  suggested_products?: string[];      // ["Chrome Extension", "SaaS", "API", "MCP", "AI Agent"]
  estimated_dev_days?: number;        // MVP 预计开发天数
  revenue_potential?: number;         // 1-5 — 首月收入星级
  risk_factors_en?: string[];         // 风险因素（英文）
  risk_factors_zh?: string[];         // 风险因素（中文）
  opportunity_summary_en?: string;    // 机会分析总结（英文）
  opportunity_summary_zh?: string;    // 机会分析总结（中文）
}

export interface TrendTermsData {
  updated_at: string;
  terms: TrendTerm[];
}
