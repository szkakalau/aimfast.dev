export interface TrendTerm {
  id: string;
  canonical: string;
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
}

export interface TrendTermsData {
  updated_at: string;
  terms: TrendTerm[];
}
