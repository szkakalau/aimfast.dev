'use client';

import { useState, useEffect, useCallback } from 'react';
import { Target, Plus, ChevronDown, ChevronUp, ExternalLink, X, Loader2 } from 'lucide-react';
import type { CompetitorIntelData, CompetitorIntelTarget } from '../dashboard-client';

const TYPE_LABELS: Record<string, string> = {
  competitor: '竞品',
  person: '人物',
  topic: '话题',
  tech: '技术',
  platform: '平台',
};

const TYPE_OPTIONS = [
  { value: 'competitor', label: '竞品公司' },
  { value: 'person', label: '行业人物' },
  { value: 'topic', label: '话题/赛道' },
  { value: 'tech', label: '技术栈' },
  { value: 'platform', label: '平台/渠道' },
];

const TREND_ICON: Record<string, string> = {
  up: '↑',
  down: '↓',
  stable: '→',
};

const TREND_COLOR: Record<string, string> = {
  up: 'var(--color-green)',
  down: 'var(--color-red)',
  stable: 'var(--color-text-muted)',
};

const SENTIMENT_LABELS: Record<string, string> = {
  positive: '😊 积极',
  negative: '😟 消极',
  neutral: '😐 中性',
};

interface TargetCardProps {
  target: CompetitorIntelTarget;
  lang: 'zh' | 'en';
  onDelete: (id: string) => void;
}

function TargetCard({ target, lang, onDelete }: TargetCardProps) {
  const [expanded, setExpanded] = useState(false);
  const { stats, highlights, suggested_actions } = target;
  const hasHighlights = highlights.length > 0;
  const typeLabel = TYPE_LABELS[target.type] ?? target.type;

  return (
    <div className="ci-card">
      {/* ── Header ── */}
      <div className="ci-card-header">
        <div className="ci-card-header-left">
          <span className="ci-card-type">{typeLabel}</span>
          <h3 className="ci-card-name">{target.name}</h3>
        </div>
        <div className="ci-card-header-right">
          <span className="ci-card-stats" style={{ color: TREND_COLOR[stats.trend] ?? 'var(--color-text-muted)' }}>
            {TREND_ICON[stats.trend] ?? '→'} {stats.weekly_mentions} 提及
          </span>
          {stats.sentiment && (
            <span className="ci-card-sentiment" title="情感倾向">
              {SENTIMENT_LABELS[stats.sentiment] ?? ''}
            </span>
          )}
          <button
            className="ci-card-delete"
            onClick={() => onDelete(target.id)}
            aria-label={`删除追踪: ${target.name}`}
            title="删除追踪"
          >
            <X size={14} />
          </button>
        </div>
      </div>

      {/* ── No highlights ── */}
      {!hasHighlights && (
        <p className="ci-card-empty">
          {lang === 'zh' ? '今天没有值得关注的新动作。' : 'No notable activity today.'}
          {stats.noise_count > 0 && (
            <span className="ci-card-noise">
              {' '}({stats.noise_count} {lang === 'zh' ? '条噪音已过滤' : 'noise filtered'})
            </span>
          )}
        </p>
      )}

      {/* ── Notable change ── */}
      {stats.notable_change && (
        <div className="ci-card-change">
          <span className="ci-card-change-label">{lang === 'zh' ? '⚠️ 变化' : '⚠️ Change'}:</span>
          <span>{stats.notable_change}</span>
        </div>
      )}

      {/* ── Highlights ── */}
      {hasHighlights && (
        <div className="ci-highlights">
          {/* Always show first highlight */}
          <HighlightItem highlight={highlights[0]} lang={lang} />

          {/* Expandable: show rest */}
          {expanded && highlights.slice(1).map((h, i) => (
            <HighlightItem key={i} highlight={h} lang={lang} />
          ))}

          {highlights.length > 1 && (
            <button
              className="ci-expand-btn"
              onClick={() => setExpanded(!expanded)}
            >
              {expanded ? (
                <><ChevronUp size={14} /> {lang === 'zh' ? '收起' : 'Collapse'}</>
              ) : (
                <><ChevronDown size={14} /> {lang === 'zh' ? `展开全部 ${highlights.length} 条` : `Show all ${highlights.length}`}</>
              )}
            </button>
          )}
        </div>
      )}

      {/* ── Suggested actions ── */}
      {suggested_actions.length > 0 && (
        <div className="ci-actions">
          {suggested_actions.map((act, i) => (
            <span key={i} className={`ci-action-chip ci-action-${act.action}`}>
              {act.label}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function HighlightItem({ highlight, lang }: { highlight: CompetitorIntelData['targets'][0]['highlights'][0]; lang: 'zh' | 'en' }) {
  return (
    <div className={`ci-highlight ci-highlight-${highlight.relevance}`}>
      <div className="ci-highlight-header">
        <a
          href={highlight.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="ci-highlight-source"
        >
          {highlight.source} <ExternalLink size={10} />
        </a>
        {highlight.relevance === 'high' && (
          <span className="ci-relevance-badge">🔥 高价值</span>
        )}
      </div>

      <blockquote className="ci-highlight-quote">
        {highlight.original_text}
      </blockquote>

      <div className="ci-highlight-details">
        <div className="ci-detail-row">
          <span className="ci-detail-label">{lang === 'zh' ? '什么意思' : 'Meaning'}</span>
          <span className="ci-detail-value">{highlight.translation}</span>
        </div>
        <div className="ci-detail-row">
          <span className="ci-detail-label">{lang === 'zh' ? '竞品影响' : 'Impact'}</span>
          <span className="ci-detail-value">{highlight.competitor_impact}</span>
        </div>
        <div className="ci-detail-row ci-detail-action">
          <span className="ci-detail-label">→ {lang === 'zh' ? '你的行动' : 'Your move'}</span>
          <span className="ci-detail-value">{highlight.your_action}</span>
        </div>
      </div>
    </div>
  );
}

/* ═══════ Add Target Form ═══════ */

const MAX_TARGETS = 10;

interface AddTargetFormProps {
  onAdded: () => void;
  currentCount: number;
  lang: 'zh' | 'en';
}

function AddTargetForm({ onAdded, currentCount, lang }: AddTargetFormProps) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('');
  const [type, setType] = useState('topic');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = useCallback(async () => {
    const trimmed = name.trim();
    if (!trimmed) {
      setError(lang === 'zh' ? '请输入追踪目标名称' : 'Please enter a target name');
      return;
    }
    if (currentCount >= MAX_TARGETS) {
      setError(lang === 'zh' ? `最多 ${MAX_TARGETS} 个追踪目标` : `Max ${MAX_TARGETS} targets`);
      return;
    }

    setSubmitting(true);
    setError('');
    try {
      const res = await fetch('/api/tracking', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: trimmed, type }),
      });
      if (res.ok) {
        setName('');
        setOpen(false);
        onAdded();
      } else {
        const data = await res.json();
        setError(data.error || (lang === 'zh' ? '添加失败' : 'Failed to add'));
      }
    } catch {
      setError(lang === 'zh' ? '网络错误，请重试' : 'Network error, try again');
    } finally {
      setSubmitting(false);
    }
  }, [name, type, currentCount, lang, onAdded]);

  if (!open) {
    return (
      <button className="ci-add-btn" onClick={() => setOpen(true)}>
        <Plus size={16} />
        <span>{lang === 'zh' ? '添加追踪目标' : 'Add Target'}</span>
      </button>
    );
  }

  return (
    <div className="ci-add-form">
      <div className="ci-add-form-row">
        <input
          className="ci-add-input"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={lang === 'zh' ? '竞品名、话题或技术栈…' : 'Competitor name, topic, or tech…'}
          onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
          autoFocus
        />
        <select
          className="ci-add-select"
          value={type}
          onChange={(e) => setType(e.target.value)}
        >
          {TYPE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>
      {error && <p className="ci-add-error">{error}</p>}
      <div className="ci-add-actions">
        <button
          className="ci-add-submit"
          onClick={handleSubmit}
          disabled={submitting || !name.trim()}
        >
          {submitting ? (
            <><Loader2 size={14} className="icon-spin" /> {lang === 'zh' ? '添加中…' : 'Adding…'}</>
          ) : (
            lang === 'zh' ? '添加' : 'Add'
          )}
        </button>
        <button className="ci-add-cancel" onClick={() => { setOpen(false); setError(''); setName(''); }}>
          {lang === 'zh' ? '取消' : 'Cancel'}
        </button>
      </div>
    </div>
  );
}

/* ═══════ Main Component ═══════ */

interface CompetitorIntelProps {
  data: CompetitorIntelData | undefined;
  lang: 'zh' | 'en';
}

export default function CompetitorIntel({ data, lang }: CompetitorIntelProps) {
  const [targets, setTargets] = useState<CompetitorIntelTarget[]>([]);
  const [allTargets, setAllTargets] = useState<Array<{ id: string; name: string }>>([]);
  const [refreshKey, setRefreshKey] = useState(0);

  // 从 data prop 同步竞品情报（每天从服务器生成）
  useEffect(() => {
    if (data?.targets) {
      setTargets(data.targets);
    }
  }, [data]);

  // 加载所有追踪目标（用于表单验证）
  useEffect(() => {
    fetch('/api/tracking')
      .then((r) => r.json())
      .then((d) => setAllTargets(d.targets || []))
      .catch(() => {});
  }, [refreshKey]);

  const handleDelete = useCallback(async (id: string) => {
    try {
      await fetch(`/api/tracking?id=${id}`, { method: 'DELETE' });
      setTargets((prev) => prev.filter((t) => t.id !== id));
      setRefreshKey((k) => k + 1);
    } catch {
      // 静默失败 — 下次刷新时恢复
    }
  }, []);

  const handleAdded = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  const targetsWithIntel = targets.filter((t) =>
    data?.targets?.some((dt) => dt.id === t.id || dt.name === t.name)
  );

  return (
    <section className="dash-section">
      <div className="dash-section-header">
        <h2 className="dash-section-title">
          <Target size={18} className="icon-inline" aria-hidden="true" />{' '}
          {lang === 'zh' ? '竞品动态' : 'Competitor Intel'}
        </h2>
      </div>

      {/* ── 由 data 驱动的竞品情报卡片 ── */}
      {targets.length > 0 ? (
        <div className="ci-grid">
          {targets.map((target) => (
            <TargetCard
              key={target.id}
              target={target}
              lang={lang}
              onDelete={handleDelete}
            />
          ))}
        </div>
      ) : (
        <div className="ci-empty">
          <Target size={40} className="ci-empty-icon" aria-hidden="true" />
          <p className="ci-empty-text">
            {lang === 'zh'
              ? '还没有追踪目标。添加你的第一个竞品或话题。'
              : 'No tracking targets yet. Add your first competitor or topic.'}
          </p>
          <p className="ci-empty-hint">
            {lang === 'zh'
              ? '每天自动追踪竞品动态、行业趋势和技术变化 — 告诉你该关注什么、该做什么。'
              : 'Daily tracking of competitor moves, industry trends, and tech changes — telling you what to watch and what to do.'}
          </p>
        </div>
      )}

      {/* ── 添加表单 ── */}
      <AddTargetForm
        onAdded={handleAdded}
        currentCount={allTargets.length}
        lang={lang}
      />
    </section>
  );
}
