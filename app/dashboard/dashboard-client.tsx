'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { Flame } from 'lucide-react';
import type { TrendTerm } from '@/app/trends/types';
import { getTrackedItems, computeDecisionScore } from '@/app/trends/utils';
import { DashboardHeader } from './components/dashboard-header';
import { DecisionCard } from './components/decision-card';
import { CompetitorCard } from './components/competitor-card';
import { FullReport } from './components/full-report';
import { DashboardFooter } from './components/dashboard-footer';
import Watchlist, { type SignalSnapshot } from './components/watchlist';
import ErrorBanner from '@/components/ErrorBanner';

/* ── I18N dictionary ── */
const I18N_DICT: Record<string, Record<string, string>> = {
  zh: {
    headerTitle: 'AimFast.Dev',
    watchlistTitle: 'My Watchlist',
    serendipityTitle: 'Also Trending Today',
    serendipityHint: 'Track terms from Trends to monitor their growth here.',
    decisionCardTitle: '今日决策',
    decisionNoSignal: '今日暂无高确定性机会。以下是过去 7 天热度最高的信号。',
    decisionEvidence: '证据',
    decisionBuyer: '谁会付费',
    decisionBuyerInferred: '正在遭受此问题的独立开发者和小团队。',
    decisionPricing: '定价',
    decisionOneTime: '一次性',
    decisionValidation: '验证路径',
    decisionValidationDefault: '2 小时 MVP → 发到信号源社区 → 测量反馈',
    decisionWhyNot: '为什么不选另外两个',
    decisionAskAI: '问 AI',
    decisionEngagement: '互动',
    cEndTitle: 'C 端消费机会',
    cEndBuyer: '谁会付钱',
    ciTitle: '竞品动态',
    ciAddTarget: '添加追踪',
    ciEmpty: '暂无竞品追踪目标。',
    ciNoIntel: '今天没有值得关注的新动作。',
    ciMentions: '提及',
    competitorCardTitle: '竞品动态',
    competitorNoIntel: '今天你的追踪目标没有值得关注的新动作。',
    competitorEmpty: '还没有追踪目标。添加你的第一个竞品或话题。',
    competitorAddTarget: '+ 添加追踪目标',
    competitorAddPlaceholder: '竞品名、话题或技术栈…',
    competitorAddConfirm: '添加',
    competitorAction: '→ 你的行动',
    aiChatTitle: '问 AI',
    aiChatWelcome: '关于今天的数据有什么想问的？深入追问证据、探索替代方案、验证假设。',
    aiChatPlaceholder: 'AI 助手即将上线…',
    aiChatSend: '→',
    footerRefresh: '数据刷新：每日 08:30 CST',
    footerNextUpdate: '下次更新',
    fullReportToggle: '完整日报',
    fullReportExpand: '展开阅读',
    fullReportCollapse: '收起',
    loading: '加载中…',
    noData: '无数据',
    historyUnavailable: '历史数据暂不可用，变化趋势将在数据积累后显示。',
  },
  en: {
    headerTitle: 'AimFast.Dev',
    watchlistTitle: 'My Watchlist',
    serendipityTitle: 'Also Trending Today',
    serendipityHint: 'Track terms from Trends to monitor their growth here.',
    decisionCardTitle: "Today's Decision",
    decisionNoSignal: 'No high-confidence opportunity today. Here are the hottest signals from the past 7 days.',
    decisionEvidence: 'Evidence',
    decisionBuyer: 'Who Will Pay',
    decisionBuyerInferred: 'Independent developers and small teams facing this problem daily.',
    decisionPricing: 'Pricing',
    decisionOneTime: 'one-time',
    decisionValidation: 'Validation',
    decisionValidationDefault: '2h MVP → post to signal source → measure response',
    decisionWhyNot: 'Why Not the Others',
    decisionAskAI: 'Ask AI',
    decisionEngagement: 'interactions',
    cEndTitle: 'Consumer Opportunities',
    cEndBuyer: 'Who Pays',
    ciTitle: 'Competitor Intel',
    ciAddTarget: 'Add Target',
    ciEmpty: 'No tracking targets set up yet.',
    ciNoIntel: 'No notable competitor activity today.',
    ciMentions: 'mentions',
    competitorCardTitle: 'Competitor Intel',
    competitorNoIntel: 'No notable activity from your tracked targets today.',
    competitorEmpty: 'No tracking targets yet. Add your first competitor or topic.',
    competitorAddTarget: '+ Add Target',
    competitorAddPlaceholder: 'Competitor name, topic, or tech…',
    competitorAddConfirm: 'Add',
    competitorAction: '→ Your move',
    aiChatTitle: 'Ask AI',
    aiChatWelcome: 'Ask me anything about this data — dig deeper into the evidence, explore alternatives, or validate assumptions.',
    aiChatPlaceholder: 'AI assistant coming soon…',
    aiChatSend: '→',
    footerRefresh: 'Data refresh: daily 08:30 CST',
    footerNextUpdate: 'Next update',
    fullReportToggle: 'Full Report',
    fullReportExpand: 'Expand',
    fullReportCollapse: 'Collapse',
    loading: 'Loading…',
    noData: 'No data',
    historyUnavailable: 'Historical data temporarily unavailable. Trend data will appear as it accumulates.',
  },
};

/* ── Shared types ── */
export type Signal = {
  id: string;
  title: string;
  url: string;
  source: string;
  source_key: string;
  signal_type: string;
  score: number;
  engagement: { likes?: number; replies?: number; points?: number; comments?: number; total: number };
  cross_platform_count: number;
  summary: string;
  tags: string[];
  author: string;
};

export type HistoryEntry = {
  date: string;
  total_signals: number;
  top_score: number;
  avg_score: number;
  action_qualified: number;
  cross_platform: number;
};

export type CompetitorIntelTarget = {
  target_id: string;
  target_name: string;
  target_type: string;
  stats: {
    weekly_mentions: number;
    trend: string;
    sentiment: string;
    noise_count: number;
    signal_count: number;
    core_narrative: string;
  };
  highlights: Array<{
    source: string;
    source_url: string;
    original_text: string;
    translation: string;
    competitor_impact: string;
    your_action: string;
    relevance: string;
  }>;
  suggested_actions: Array<{ action: string; label: string }>;
  noise_summary: string;
};

export type CompetitorIntel = {
  date: string;
  target_count: number;
  targets: CompetitorIntelTarget[];
};

export type CompetitorTarget = {
  id: string;
  name: string;
  type: string;
  aliases: string[];
  keywords: string[];
  status: string;
};

export type DashboardDecision = {
  product_name?: string;
  one_liner?: string;
  pricing?: string;
  validation_path?: string;
  buyer?: string;
  why_not_others?: string;
};

export type DashboardData = {
  date: string;
  signals: Signal[];
  summary: Record<string, unknown>;
  history: HistoryEntry[];
  opportunities: unknown[];
  decision?: DashboardDecision;
  demand_radar: Record<string, unknown>;
  workbench: Record<string, unknown>;
  bets: unknown[];
  lessons: unknown[];
  watchlist: unknown[];
  competitor_targets: CompetitorTarget[];
  competitor_intel: CompetitorIntel;
  report_md: string;
  report_md_en: string;
  pipeline: Record<string, unknown>;
  archive: Array<{ date: string; report_md: string; report_md_en: string; has_report: boolean }>;
  generated_at: string;
};

function toSnapshot(t: TrendTerm): SignalSnapshot {
  return { id: t.id, canonical: t.canonical, category: t.category, stage: t.stage, score: t.score, total_mentions: t.total_mentions };
}

/* ── Helpers ── */

function daysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

/* ═════ Main Component ═════ */

type Props = { trendTerms: TrendTerm[] };

export function DashboardClient({ trendTerms }: Props) {
  // ── State ──
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [lang, setLang] = useState<'zh' | 'en'>('en');
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [trackedItems, setTrackedItems] = useState(getTrackedItems);
  const [historyTerms, setHistoryTerms] = useState<TrendTerm[]>([]);
  const [historyUnavailable, setHistoryUnavailable] = useState(false);
  const [dashError, setDashError] = useState(false);
  const [historyError, setHistoryError] = useState(false);

  // ── i18n ──
  const t = useMemo(() => I18N_DICT[lang] || I18N_DICT.en, [lang]);

  // Detect browser language on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem('kakaopc_lang');
      if (saved === 'zh' || saved === 'en') setLang(saved);
      else if (navigator.language.startsWith('zh')) setLang('zh');
    } catch { /* localStorage unavailable */ }
  }, []);

  // Poll for tracking changes (e.g. from Trends page in another tab)
  useEffect(() => {
    const onStorage = () => setTrackedItems(getTrackedItems());
    window.addEventListener('storage', onStorage);
    // Also refresh on mount in case Trends page was used
    setTrackedItems(getTrackedItems());
    return () => window.removeEventListener('storage', onStorage);
  }, []);

  const toggleLang = useCallback(() => {
    setLang((prev) => {
      const next = prev === 'zh' ? 'en' : 'zh';
      try { localStorage.setItem('kakaopc_lang', next); } catch { /* noop */ }
      return next;
    });
  }, []);

  // ── Fetch data ──
  useEffect(() => {
    let cancelled = false;
    async function load() {
      // Fetch today's dashboard.json + 7d-ago history in parallel
      const historyDate = daysAgo(7);
      const [dashRes, histRes] = await Promise.all([
        fetch('/dashboard/data/dashboard.json'),
        fetch(`/dashboard/data/history/trends_${historyDate}.json`),
      ]);

      if (!cancelled) {
        if (dashRes.ok) {
          try {
            const json: DashboardData = await dashRes.json();
            setData(json);
            setSelectedDate(json.date);
            try { localStorage.setItem('kakaopc_dashboard_cache', JSON.stringify(json)); } catch { /* noop */ }
          } catch (err) {
            console.error('[Dashboard] Failed to parse dashboard data:', err);
            setDashError(true);
          }
        } else {
          // Fallback to cache
          try {
            const cached = localStorage.getItem('kakaopc_dashboard_cache');
            if (cached) {
              const parsed = JSON.parse(cached) as DashboardData;
              setData(parsed);
              setSelectedDate(parsed.date);
            } else {
              setDashError(true);
            }
          } catch { setDashError(true); }
        }

        if (histRes.ok) {
          try {
            const hist: TrendTerm[] = await histRes.json();
            setHistoryTerms(hist);
          } catch { setHistoryUnavailable(true); setHistoryError(true); }
        } else {
          setHistoryUnavailable(true);
          setHistoryError(true);
        }

        setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  // ── Derived data ──

  // Build today's trend map
  const todayMap = useMemo(() => {
    const m = new Map<string, TrendTerm>();
    for (const t of trendTerms) m.set(t.id, t);
    return m;
  }, [trendTerms]);

  const historyMap = useMemo(() => {
    const m = new Map<string, TrendTerm>();
    for (const t of historyTerms) m.set(t.id, t);
    return m;
  }, [historyTerms]);

  // Determine the decision signal: prefer tracked term with highest decisionScore
  const decisionSignal = useMemo(() => {
    if (!data) return null;

    // Try tracked items first
    let bestScore = -Infinity;
    let bestSignal: Signal | null = null;

    for (const item of trackedItems) {
      const today = todayMap.get(item.id);
      const hist = historyMap.get(item.id);
      if (!today) continue;
      const ds = computeDecisionScore(today, hist ?? undefined);
      if (ds !== null && ds > bestScore) {
        bestScore = ds;
        // Match trend term to dashboard signal.
        // NOTE: assumes signal.id === trend term id (format: "trend-{slug}").
        // If generate_dashboard.py uses a different ID scheme, this will never match.
        const sig = data.signals.find((s) => s.id === item.id);
        if (sig) bestSignal = sig;
      }
    }

    // Fallback: global top signal
    if (!bestSignal && data.signals.length > 0) {
      bestSignal = data.signals[0];
    }

    return bestSignal;
  }, [data, trackedItems, todayMap, historyMap]);

  // Serendipity: top 3 untracked signals (by score) with trend data
  const serendipitySignals = useMemo(() => {
    if (!data) return [];
    const trackedIds = new Set(trackedItems.map((t) => t.id));
    return data.signals
      .filter((s) => !trackedIds.has(s.id))
      .slice(0, 3);
  }, [data, trackedItems]);

  // Watchlist data: signal snapshots for today + history
  const watchlistToday = useMemo(
    () => trendTerms.map(toSnapshot),
    [trendTerms],
  );
  const watchlistHistory = useMemo(
    () => historyTerms.map(toSnapshot),
    [historyTerms],
  );

  // Top recommendations for cold start
  const topRecommendations = useMemo(
    () => trendTerms.slice(0, 10).map(toSnapshot),
    [trendTerms],
  );

  // ── Derived from dashboard data ──
  const topSignal = data?.signals?.[0] || null;
  const decision = data?.decision || {};
  const signalCount = data?.signals?.length || 0;
  const reportMd = lang === 'en' && data?.report_md_en ? data.report_md_en : (data?.report_md || '');

  // Archive dates for date picker
  const allDates = useMemo(() => {
    if (!data?.archive) return data?.date ? [data.date] : [];
    return data.archive.map((a) => a.date).sort().reverse();
  }, [data]);

  // ── Render ──
  if (loading) {
    return (
      <>
        <DashboardHeader
          lang={lang}
          onToggleLang={toggleLang}
          title={t.headerTitle}
          date="--"
          dates={[]}
          onSelectDate={() => {}}
        />
        <main className="dash-main">
          <Watchlist
            trackedItems={[]}
            todaySignals={[]}
            historySignals={[]}
            topRecommendations={[]}
            loading
          />
          <DecisionCard t={t} lang={lang} signal={null} decision={{}} reportMd="" date="--" loading />
          <CompetitorCard t={t} intel={null} targets={[]} loading />
        </main>
      </>
    );
  }

  if (!data) {
    return (
      <>
        <DashboardHeader
          lang={lang}
          onToggleLang={toggleLang}
          title={t.headerTitle}
          date="--"
          dates={[]}
          onSelectDate={() => {}}
        />
        <main className="dash-main">
          {dashError ? (
            <div className="container" style={{ marginTop: 'var(--space-4)' }}>
              <ErrorBanner section="Dashboard" onRetry={() => window.location.reload()} />
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '40vh' }}>
              <p style={{ color: 'var(--color-text-muted)' }}>{t.noData}</p>
            </div>
          )}
        </main>
      </>
    );
  }

  const headerStatus = `${signalCount} signals · Updated ${data.generated_at ? new Date(data.generated_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false }) : 'daily'}`;

  return (
    <>
      <DashboardHeader
        lang={lang}
        onToggleLang={toggleLang}
        title={t.headerTitle}
        date={selectedDate || data.date}
        dates={allDates}
        onSelectDate={setSelectedDate}
        status={headerStatus}
      />

      <main className="dash-main">
        {/* ── Global error (dashboard data fetch failed, no cache) ── */}
        {dashError && (
          <div className="container" style={{ marginBottom: 'var(--space-3)' }}>
            <ErrorBanner section="Dashboard" onRetry={() => window.location.reload()} />
          </div>
        )}

        {/* ── Watchlist ── */}
        <Watchlist
          trackedItems={trackedItems}
          todaySignals={watchlistToday}
          historySignals={watchlistHistory}
          topRecommendations={topRecommendations}
          historyUnavailable={historyUnavailable}
          historyError={historyError}
        />

        {/* ── Today's Decision (tracked-prioritized) ── */}
        <DecisionCard
          t={t}
          lang={lang}
          signal={decisionSignal || topSignal}
          decision={decision}
          reportMd={reportMd}
          date={selectedDate || data.date}
        />

        {/* ── Serendipity: Also Trending Today ── */}
        {serendipitySignals.length > 0 && (
          <section className="dash-section">
            <h2 className="dash-section-title"><Flame size={18} className="icon-inline" aria-hidden="true" /> {t.serendipityTitle}</h2>
            <div className="serendipity-row">
              {serendipitySignals.map((sig) => {
                const trend = todayMap.get(sig.id);
                return (
                  <a
                    key={sig.id}
                    href={trend ? `/trends/${trend.id.replace('trend-', '')}/` : '#'}
                    className="serendipity-card"
                  >
                    <span className="serendipity-card-source">{sig.source}</span>
                    <span className="serendipity-card-title">{sig.title}</span>
                    <span className="serendipity-card-score">Score: {sig.score}</span>
                  </a>
                );
              })}
            </div>
          </section>
        )}

        {/* ── Competitor Intel ── */}
        <CompetitorCard
          t={t}
          intel={data.competitor_intel}
          targets={data.competitor_targets || []}
        />

        {/* ── Full Report ── */}
        <FullReport t={t} reportMd={reportMd} />
      </main>

      <DashboardFooter t={t} generatedAt={data.generated_at} />
    </>
  );
}
