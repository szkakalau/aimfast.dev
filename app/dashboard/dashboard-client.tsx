'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { DashboardHeader } from './components/dashboard-header';
import { DashboardHero } from './components/dashboard-hero';
import { CompetitorIntel } from './components/competitor-intel';
import { TopSignals } from './components/top-signals';
import { TrendCharts } from './components/trend-charts';
import { DailyReport } from './components/daily-report';
import { OpportunityBoard } from './components/opportunity-board';
import { BetDrawer } from './components/bet-drawer';
import { DashboardFooter } from './components/dashboard-footer';

/* ── I18N dictionary (mirrors existing zh/en) ── */
const I18N_DICT: Record<string, Record<string, string>> = {
  zh: {
    headerTitle: 'AimFast.Dev',
    heroOpportunity: '今日最佳机会',
    heroBets: '当前下注',
    heroSignals: '今日信号',
    heroSubBets: '个决策追踪中',
    heroSubSignals: '来自 11 个信源',
    ciTitle: '🎯 竞品动态',
    ciAddTarget: '添加追踪',
    ciEmpty: '暂无竞品追踪目标。',
    ciNoIntel: '今日暂无竞品情报。',
    ciMentions: '提及',
    ciTrendUp: '↑',
    ciTrendDown: '↓',
    ciTrendStable: '→',
    ciNoise: '已过滤',
    ciTypeCompetitor: '竞品',
    ciTypeTopic: '话题',
    ciTypePerson: '人物',
    ciTypeTech: '技术',
    ciTypePlatform: '平台',
    signalsTitle: 'Top 10 信号',
    thRank: '#',
    thSignal: '信号',
    thSource: '来源',
    thScore: '评分',
    thCross: '跨平台',
    thEngagement: '互动',
    chartScoreTitle: '14天评分趋势',
    chartVolumeTitle: '14天信号量',
    reportTitle: '📰 日报',
    tocTitle: '目录',
    tocJumpTo: '-- 跳转到 --',
    oppBoardTitle: '机会看板',
    oppActiveBets: '🎯 活跃下注',
    oppActiveBetsEmpty: '暂无活跃下注。',
    oppPipeline: '📡 机会管线',
    oppPipelineEmpty: '暂无机会数据。',
    oppLessons: '📖 近期复盘',
    oppLessonsEmpty: '暂无复盘记录。',
    betDrawerTitle: '新下注',
    betActionObserve: '观察',
    betActionValidate: '验证',
    betActionBuild: '构建',
    betCancel: '取消',
    betConfirm: '确认下注',
    loadingSignals: '正在加载信号数据…',
    loadingReport: '正在加载报告…',
    footerRefresh: '数据刷新：每日 08:30 CST',
    oppObserve: '观察',
    oppValidate: '验证',
    oppBuild: '构建',
    oppWhy: '为什么',
    reportAria: '日报',
    loading: '加载中…',
    noData: '无数据',
    backToTop: '回到顶部',
  },
  en: {
    headerTitle: 'AimFast.Dev',
    heroOpportunity: "Today's Best Opportunity",
    heroBets: 'Active Bets',
    heroSignals: 'Signals Today',
    heroSubBets: 'decisions tracked',
    heroSubSignals: 'from 11 sources',
    ciTitle: '🎯 Competitor Intel',
    ciAddTarget: 'Add Target',
    ciEmpty: 'No tracking targets.',
    ciNoIntel: 'No intel today.',
    ciMentions: 'mentions',
    ciTrendUp: '↑',
    ciTrendDown: '↓',
    ciTrendStable: '→',
    ciNoise: 'filtered',
    ciTypeCompetitor: 'Competitor',
    ciTypeTopic: 'Topic',
    ciTypePerson: 'Person',
    ciTypeTech: 'Tech',
    ciTypePlatform: 'Platform',
    signalsTitle: 'Top 10 Signals',
    thRank: '#',
    thSignal: 'Signal',
    thSource: 'Source',
    thScore: 'Score',
    thCross: 'Cross-Platform',
    thEngagement: 'Engagement',
    chartScoreTitle: '14-Day Score Trend',
    chartVolumeTitle: '14-Day Signal Volume',
    reportTitle: '📰 Daily Report',
    tocTitle: 'Contents',
    tocJumpTo: '-- Jump to --',
    oppBoardTitle: 'Opportunity Board',
    oppActiveBets: '🎯 Active Bets',
    oppActiveBetsEmpty: 'No active bets.',
    oppPipeline: '📡 Opportunity Pipeline',
    oppPipelineEmpty: 'No opportunity data yet.',
    oppLessons: '📖 Recent Lessons',
    oppLessonsEmpty: 'No lessons recorded yet.',
    betDrawerTitle: 'New Bet',
    betActionObserve: 'Observe',
    betActionValidate: 'Validate',
    betActionBuild: 'Build',
    betCancel: 'Cancel',
    betConfirm: 'Place Bet',
    loadingSignals: 'Loading signal data…',
    loadingReport: 'Loading report…',
    footerRefresh: 'Data refresh: daily 08:30 CST',
    oppObserve: 'Observe',
    oppValidate: 'Validate',
    oppBuild: 'Build',
    oppWhy: 'Why',
    reportAria: 'Daily Report',
    loading: 'Loading…',
    noData: 'No data',
    backToTop: 'Back to top',
  },
};

export type IntelAction = { action: string; label: string };
export type IntelHighlight = { source: string; source_url: string; original_text: string; translation: string; competitor_impact: string; your_action: string; relevance: string };
export type CompetitorIntelTarget = {
  target_id: string; target_name: string; target_type: string;
  stats: { weekly_mentions: number; trend: string; sentiment: string; noise_count: number; signal_count: number; core_narrative: string };
  highlights: IntelHighlight[];
  suggested_actions: IntelAction[];
  noise_summary: string;
};
export type CompetitorIntel = { date: string; target_count: number; targets: CompetitorIntelTarget[] };
export type DashboardData = {
  date: string;
  signals: Signal[];
  summary: Record<string, unknown>;
  history: HistoryEntry[];
  opportunities: OppEntry[];
  demand_radar: Record<string, unknown>;
  workbench: Record<string, unknown>;
  bets: Bet[];
  lessons: Lesson[];
  watchlist: unknown[];
  competitor_targets: CompetitorTarget[];
  competitor_intel: CompetitorIntel;
  report_md: string;
  report_md_en: string;
  pipeline: Record<string, unknown>;
  archive: ArchiveEntry[];
  generated_at: string;
};

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

export type HistoryEntry = { date: string; total_signals: number; top_score: number; avg_score: number; action_qualified: number; cross_platform: number };
export type Bet = { id: string; date: string; demand: string; action: string; status: string; thesis?: string; criteria?: string; timeline_days?: number; created_at?: string };
export type Lesson = { id: string; type: string; opportunity: string; lesson: string; date: string };
export type CompetitorTarget = { id: string; name: string; type: string; aliases: string[]; keywords: string[]; status: string };
export type OppEntry = { id?: string; name?: string; demand?: string; score?: number; stage?: string; why?: string; type?: string; _suggested?: boolean };
export type ArchiveEntry = { date: string; report_md: string; report_md_en: string; has_report: boolean };

export function DashboardClient() {
  // ── State ──
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [lang, setLang] = useState<'zh' | 'en'>('zh');
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerDemand, setDrawerDemand] = useState<{ name: string; id: string } | null>(null);
  const [drawerAction, setDrawerAction] = useState('observe');
  const [drawerTimeline, setDrawerTimeline] = useState(7);
  const [drawerThesis, setDrawerThesis] = useState('');
  const [drawerCriteria, setDrawerCriteria] = useState('');

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
        const json = await res.json();
        if (!cancelled) {
          setData(json);
          setSelectedDate(json.date);
        }
      } catch (err) {
        console.error('[Dashboard] Failed to load data:', err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  // ── Bet actions ──
  const openBetDrawer = useCallback((demandName: string, demandId: string) => {
    setDrawerDemand({ name: demandName, id: demandId });
    setDrawerAction('observe');
    setDrawerTimeline(7);
    setDrawerThesis('');
    setDrawerCriteria('');
    setDrawerOpen(true);
  }, []);

  const closeBetDrawer = useCallback(() => setDrawerOpen(false), []);

  const confirmBet = useCallback(() => {
    if (!drawerDemand) return;
    const bets: Bet[] = data?.bets ? [...data.bets] : [];
    const newBet: Bet = {
      id: `bet-${Date.now()}`,
      date: data?.date || '',
      demand: drawerDemand.name,
      action: drawerAction,
      status: 'active',
      thesis: drawerThesis,
      criteria: drawerCriteria,
      timeline_days: drawerTimeline,
      created_at: new Date().toISOString(),
    };
    bets.push(newBet);
    setData((prev) => prev ? { ...prev, bets } : prev);
    // Persist to localStorage
    try {
      const stored = JSON.parse(localStorage.getItem('kakaopc_bets') || '[]');
      stored.push(newBet);
      localStorage.setItem('kakaopc_bets', JSON.stringify(stored));
    } catch { /* noop */ }
    closeBetDrawer();
  }, [drawerDemand, drawerAction, drawerTimeline, drawerThesis, drawerCriteria, data, closeBetDrawer]);

  // ── Render ──
  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
        <p style={{ color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>{t.loading}</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
        <p style={{ color: 'var(--color-text-muted)' }}>{t.noData}</p>
      </div>
    );
  }

  return (
    <>
      <DashboardHeader
        lang={lang}
        onToggleLang={toggleLang}
        title={t.headerTitle}
        date={selectedDate || data.date}
      />

      <main className="dash-main">
        {/* ── Hero Strip ── */}
        <DashboardHero
          t={t}
          topSignal={data.signals[0] || null}
          betCount={data.bets?.filter((b: Bet) => b.status === 'active').length || 0}
          signalCount={data.signals.length}
        />

        {/* ── Competitor Intel ── */}
        <CompetitorIntel
          t={t}
          intel={data.competitor_intel}
          targets={data.competitor_targets || []}
        />

        {/* ── Top 10 Signals ── */}
        <TopSignals t={t} signals={data.signals.slice(0, 10)} />

        {/* ── Charts ── */}
        <TrendCharts t={t} history={data.history || []} />

        {/* ── Daily Report ── */}
        <DailyReport
          t={t}
          lang={lang}
          reportMd={lang === 'en' && data.report_md_en ? data.report_md_en : data.report_md}
          date={selectedDate || data.date}
          archive={data.archive || []}
          selectedDate={selectedDate}
          onSelectDate={setSelectedDate}
        />

        {/* ── Opportunity Board ── */}
        <OpportunityBoard
          t={t}
          bets={data.bets || []}
          opportunities={data.opportunities || []}
          demandRadar={data.demand_radar}
          lessons={data.lessons || []}
          onPlaceBet={openBetDrawer}
        />
      </main>

      <DashboardFooter t={t} generatedAt={data.generated_at} />

      {/* ── Bet Drawer ── */}
      {drawerOpen && (
        <BetDrawer
          t={t}
          demandName={drawerDemand?.name || ''}
          action={drawerAction}
          timeline={drawerTimeline}
          thesis={drawerThesis}
          criteria={drawerCriteria}
          onActionChange={setDrawerAction}
          onTimelineChange={setDrawerTimeline}
          onThesisChange={setDrawerThesis}
          onCriteriaChange={setDrawerCriteria}
          onConfirm={confirmBet}
          onClose={closeBetDrawer}
        />
      )}
    </>
  );
}
