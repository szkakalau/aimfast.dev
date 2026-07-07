'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { DashboardHeader } from './components/dashboard-header';
import { DecisionCard } from './components/decision-card';
import { CompetitorCard } from './components/competitor-card';
import { SystemPulse } from './components/system-pulse';
import { AiChatPanel } from './components/ai-chat-panel';
import { FullReport } from './components/full-report';
import { DashboardFooter } from './components/dashboard-footer';

/* ── I18N dictionary ── */
const I18N_DICT: Record<string, Record<string, string>> = {
  zh: {
    headerTitle: 'AimFast.Dev',
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
    pulseTitle: '系统脉搏',
    pulseSignals: '今日信号',
    pulseTopScore: '最高分',
    pulseCrossPlatform: '跨平台',
    pulseSourcesOnline: '信源在线',
    pulseViewArchive: '查看完整日报归档 →',
    pulseHealthy: '正常',
    pulseDegraded: '部分异常',
    pulseNoData: '暂无数据',
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
    backToTop: '回到顶部',
  },
  en: {
    headerTitle: 'AimFast.Dev',
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
    pulseTitle: 'System Pulse',
    pulseSignals: 'Signals Today',
    pulseTopScore: 'Top Score',
    pulseCrossPlatform: 'Cross-Platform',
    pulseSourcesOnline: 'Sources Online',
    pulseViewArchive: 'View Full Report Archive →',
    pulseHealthy: 'Healthy',
    pulseDegraded: 'Degraded',
    pulseNoData: 'No data yet',
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
    backToTop: 'Back to top',
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

export function DashboardClient() {
  // ── State ──
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [lang, setLang] = useState<'zh' | 'en'>('en');
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [chatCard, setChatCard] = useState<'decision' | 'competitor' | 'system' | null>(null);

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
      try {
        const res = await fetch('/dashboard/data/dashboard.json');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json: DashboardData = await res.json();
        if (!cancelled) {
          setData(json);
          setSelectedDate(json.date);
          // Cache for offline fallback
          try { localStorage.setItem('kakaopc_dashboard_cache', JSON.stringify(json)); } catch { /* noop */ }
        }
      } catch (err) {
        console.error('[Dashboard] Failed to load data:', err);
        // Fallback to cache
        if (!cancelled) {
          try {
            const cached = localStorage.getItem('kakaopc_dashboard_cache');
            if (cached) {
              const parsed = JSON.parse(cached) as DashboardData;
              setData(parsed);
              setSelectedDate(parsed.date);
            }
          } catch { /* noop */ }
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  // ── AI Chat ──
  const openChat = useCallback((card: 'decision' | 'competitor' | 'system') => {
    setChatCard((prev) => (prev === card ? null : card));
  }, []);

  const closeChat = useCallback(() => setChatCard(null), []);

  // ── Derived data ──
  const topSignal = data?.signals?.[0] || null;
  const decision = data?.decision || {};
  const history = data?.history || [];
  const signalCount = data?.signals?.length || 0;
  const topScore = topSignal?.score || (history.length > 0 ? history[history.length - 1].top_score : 0);
  const crossPlatformCount = data?.signals?.filter((s) => s.cross_platform_count > 0).length || 0;
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
          <DecisionCard t={t} signal={null} decision={{}} reportMd="" date="--" loading />
          <CompetitorCard t={t} intel={null} targets={[]} loading />
          <SystemPulse t={t} history={[]} signalCount={0} topScore={0} crossPlatformCount={0} sourcesOnline={0} sourcesTotal={0} loading />
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
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '40vh' }}>
            <p style={{ color: 'var(--color-text-muted)' }}>{t.noData}</p>
          </div>
        </main>
      </>
    );
  }

  return (
    <>
      <DashboardHeader
        lang={lang}
        onToggleLang={toggleLang}
        title={t.headerTitle}
        date={selectedDate || data.date}
        dates={allDates}
        onSelectDate={setSelectedDate}
      />

      <main className="dash-main">
        {/* ── Card 1: Today's Decision ── */}
        <DecisionCard
          t={t}
          signal={topSignal}
          decision={decision}
          reportMd={reportMd}
          date={selectedDate || data.date}
          onAskAI={() => openChat('decision')}
        />

        {/* AI Chat for decision card */}
        {chatCard === 'decision' && (
          <AiChatPanel
            t={t}
            cardType="decision"
            isOpen
            onClose={closeChat}
          />
        )}

        {/* ── Card 2: Competitor Intel ── */}
        <CompetitorCard
          t={t}
          intel={data.competitor_intel}
          targets={data.competitor_targets || []}
          onAskAI={() => openChat('competitor')}
        />

        {/* AI Chat for competitor card */}
        {chatCard === 'competitor' && (
          <AiChatPanel
            t={t}
            cardType="competitor"
            isOpen
            onClose={closeChat}
          />
        )}

        {/* ── Card 3: System Pulse ── */}
        <SystemPulse
          t={t}
          history={history}
          signalCount={signalCount}
          topScore={topScore}
          crossPlatformCount={crossPlatformCount}
          sourcesOnline={11}
          sourcesTotal={11}
        />

        {/* AI Chat for system pulse */}
        {chatCard === 'system' && (
          <AiChatPanel
            t={t}
            cardType="system"
            isOpen
            onClose={closeChat}
          />
        )}

        {/* ── Full Report (collapsible daily report) ── */}
        <FullReport t={t} reportMd={reportMd} />
      </main>

      <DashboardFooter t={t} generatedAt={data.generated_at} />
    </>
  );
}
