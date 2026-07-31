'use client';

import { useState, useMemo } from 'react';
import Link from 'next/link';
import {
  Lightbulb,
  Target,
  DollarSign,
  AlertTriangle,
  Play,
  ChevronDown,
  ChevronUp,
  TrendingUp,
  BarChart3,
} from 'lucide-react';

/* ── Types ── */

export type DeepAnalysisItem = {
  id: string;
  slug: string;
  canonical: string;
  category: string;
  stage: string;
  score: number;
  opportunity_score: number;
  market_score: number;
  competition_score: number;
  demand_score: number;
  source_count: number;
  total_mentions: number;
  growth_pct: number;
  summary_en: string;
  why_summary: string;
  tam: string;
  mvp_blueprint: string;
  business_model: string;
  risk_assessment: string;
  action_plan: string;
  suggested_products: string[];
  tags: string[];
};

export type DeepAnalysisData = {
  updated_at: string;
  total: number;
  items: DeepAnalysisItem[];
};

/* ── Sub-components ── */

function ScoreBadge({ score, label }: { score: number; label: string }) {
  const color = score >= 70 ? 'var(--opp-score-high)' : score >= 40 ? 'var(--opp-score-mid)' : 'var(--opp-score-low)';
  return (
    <div className="da-score-badge" style={{ borderColor: color }}>
      <span className="da-score-value" style={{ color }}>{score}</span>
      <span className="da-score-label">{label}</span>
    </div>
  );
}

function SectionPreview({ icon: Icon, title, text }: { icon: React.ComponentType<{ size?: number; className?: string }>; title: string; text: string }) {
  if (!text) return null;
  // Strip markdown formatting for preview
  const clean = text
    .replace(/^#{1,4}\s+/gm, '')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .slice(0, 250);

  return (
    <div className="da-section-preview">
      <div className="da-section-header">
        <Icon size={14} className="da-section-icon" />
        <span className="da-section-title">{title}</span>
      </div>
      <p className="da-section-text">{clean}{clean.length >= 250 ? '…' : ''}</p>
    </div>
  );
}

function DeepAnalysisCard({ item, lang }: { item: DeepAnalysisItem; lang: 'zh' | 'en' }) {
  const [expanded, setExpanded] = useState(false);
  const isEn = lang === 'en';

  const stageLabel = (s: string) => {
    const map: Record<string, string> = {
      nascent: isEn ? 'Nascent' : '萌芽期',
      emergent: isEn ? 'Emergent' : '涌现期',
      validating: isEn ? 'Validating' : '验证期',
      rising: isEn ? 'Rising' : '上升期',
    };
    return map[s] || s;
  };

  const trendUrl = `/trends/${item.slug}/`;

  return (
    <div className="da-card">
      {/* ── Header ── */}
      <div className="da-card-header">
        <div className="da-card-header-top">
          <span className={`stage-badge ${item.stage}`}>{stageLabel(item.stage)}</span>
          <Link href={trendUrl} className="da-card-title-link">
            <h3 className="da-card-title">{item.canonical}</h3>
          </Link>
        </div>

        <div className="da-card-scores">
          <ScoreBadge score={item.opportunity_score} label={isEn ? 'Opportunity' : '机会'} />
          <ScoreBadge score={item.market_score} label={isEn ? 'Market' : '市场'} />
          <ScoreBadge score={item.demand_score} label={isEn ? 'Demand' : '需求'} />
          {item.competition_score <= 30 && (
            <span className="da-low-comp" title={isEn ? 'Low competition — green field' : '低竞争 — 蓝海'}>
              {isEn ? 'Low competition' : '低竞争'}
            </span>
          )}
        </div>
      </div>

      {/* ── Why Summary ── */}
      {item.why_summary && (
        <p className="da-why-summary">{item.why_summary.slice(0, 200)}{item.why_summary.length > 200 ? '…' : ''}</p>
      )}

      {/* ── Tags + Products ── */}
      <div className="da-card-tags">
        {item.tags.slice(0, 4).map((tag) => (
          <span key={tag} className="da-tag">#{tag}</span>
        ))}
        {item.suggested_products.slice(0, 3).map((p) => (
          <span key={p} className="da-product-tag">{p}</span>
        ))}
      </div>

      {/* ── Stats row ── */}
      <div className="da-card-stats">
        <span className="da-stat"><TrendingUp size={12} /> +{item.growth_pct}%</span>
        <span className="da-stat"><BarChart3 size={12} /> {item.source_count} {isEn ? 'sources' : '信源'}</span>
        <span className="da-stat">{item.total_mentions} {isEn ? 'mentions' : '提及'}</span>
      </div>

      {/* ── Expand toggle ── */}
      <button
        className="da-expand-btn"
        onClick={() => setExpanded((prev) => !prev)}
        aria-expanded={expanded}
      >
        {expanded ? (
          <><ChevronUp size={14} /> {isEn ? 'Collapse' : '收起'}</>
        ) : (
          <><ChevronDown size={14} /> {isEn ? 'Show TAM, MVP & Action Plan' : '展开 TAM、MVP 与行动建议'}</>
        )}
      </button>

      {/* ── Expanded content ── */}
      {expanded && (
        <div className="da-expanded">
          <SectionPreview icon={Target} title={isEn ? 'TAM & Market Size' : '市场规模 (TAM)'} text={item.tam} />
          <SectionPreview icon={DollarSign} title={isEn ? 'Business Model' : '商业模式'} text={item.business_model} />
          <SectionPreview icon={Play} title={isEn ? 'MVP Blueprint' : 'MVP 蓝图'} text={item.mvp_blueprint} />
          <SectionPreview icon={AlertTriangle} title={isEn ? 'Risk Assessment' : '风险评估'} text={item.risk_assessment} />

          <Link href={trendUrl} className="da-read-full">
            {isEn ? 'Read full analysis →' : '阅读完整分析 →'}
          </Link>
        </div>
      )}
    </div>
  );
}

/* ── Main Component ── */

interface DeepAnalysisProps {
  data: DeepAnalysisData | null;
  lang: 'zh' | 'en';
  loading?: boolean;
}

export default function DeepAnalysis({ data, lang, loading }: DeepAnalysisProps) {
  const isEn = lang === 'en';

  if (loading) {
    return (
      <section className="dash-section">
        <h2 className="dash-section-title">
          <Lightbulb size={18} className="icon-inline" aria-hidden="true" />
          {isEn ? 'Deep Analysis' : '深度分析'}
        </h2>
        <div className="da-grid">
          {[1, 2, 3].map((i) => (
            <div key={i} className="da-card skeleton-card" aria-busy="true">
              <div className="skeleton skeleton-h2" />
              <div className="skeleton skeleton-text" />
              <div className="skeleton skeleton-text short" />
            </div>
          ))}
        </div>
      </section>
    );
  }

  if (!data || !data.items || data.items.length === 0) {
    return (
      <section className="dash-section">
        <h2 className="dash-section-title">
          <Lightbulb size={18} className="icon-inline" aria-hidden="true" />
          {isEn ? 'Deep Analysis' : '深度分析'}
        </h2>
        <div className="da-empty">
          <p>{isEn ? 'Deep analysis reports are being generated. Check back soon.' : '深度分析报告正在生成中，请稍后查看。'}</p>
        </div>
      </section>
    );
  }

  // Sort by opportunity_score descending
  const sorted = [...data.items].sort((a, b) => b.opportunity_score - a.opportunity_score);

  return (
    <section className="dash-section">
      <div className="dash-section-header">
        <h2 className="dash-section-title">
          <Lightbulb size={18} className="icon-inline" aria-hidden="true" />
          {isEn ? 'Deep Analysis' : '深度分析'}
          <span className="da-count">{data.total} {isEn ? 'reports' : '篇报告'}</span>
        </h2>
      </div>

      <p className="da-subtitle">
        {isEn
          ? 'In-depth business case analysis for the highest-scoring trends. Each includes TAM estimation, MVP blueprint, business model recommendations, risk assessment, and a concrete action plan.'
          : '最高分趋势的深度商业案分析。每篇包含市场规模估算、MVP 蓝图、商业模式建议、风险评估和具体行动方案。'}
      </p>

      <div className="da-grid">
        {sorted.map((item) => (
          <DeepAnalysisCard key={item.id} item={item} lang={lang} />
        ))}
      </div>
    </section>
  );
}
