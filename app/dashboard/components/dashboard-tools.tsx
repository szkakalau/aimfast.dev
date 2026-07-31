'use client';

import { useState, useCallback, useEffect } from 'react';
import { Download, Bell, BellOff, Plus, X, Loader2, Check } from 'lucide-react';

/* ── Types ── */

type AlertItem = {
  id: string;
  keyword: string;
  category: string | null;
  minScore: number;
  enabled: boolean;
  lastMatchedAt: string | null;
  lastMatchTerm: string | null;
  createdAt: string;
};

type NewMatch = {
  alertId: string;
  keyword: string;
  matchedTerm: string;
};

type AlertsData = {
  alerts: AlertItem[];
  newMatches: NewMatch[];
};

const VALID_CATEGORIES = [
  'DevTools', 'AIAgent', 'OpenSource', 'AIModel', 'TechConcept',
  'Industry', 'AIApp', 'DX', 'Infra', 'Productivity', 'Consumer', 'Design',
];

/* ── Export Button ── */

function ExportButton({ lang }: { lang: 'zh' | 'en' }) {
  const [open, setOpen] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState('');

  const handleExport = useCallback(async (format: 'csv' | 'json') => {
    setDownloading(true);
    setError('');
    try {
      const res = await fetch(`/api/export?type=trends&format=${format}`);
      if (res.status === 402) {
        setError(lang === 'zh' ? '需要 Pro 订阅。' : 'Requires Pro subscription.');
        return;
      }
      if (!res.ok) throw new Error('Export failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `aimfast-trends.${format}`;
      a.click();
      URL.revokeObjectURL(url);
      setOpen(false);
    } catch {
      setError(lang === 'zh' ? '导出失败，请重试。' : 'Export failed. Try again.');
    } finally {
      setDownloading(false);
    }
  }, [lang]);

  return (
    <div className="dtools-action">
      <button
        className="dtools-btn"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        title={lang === 'zh' ? '导出数据' : 'Export Data'}
      >
        <Download size={14} />
        <span>{lang === 'zh' ? '导出' : 'Export'}</span>
      </button>

      {open && (
        <div className="dtools-dropdown">
          <button
            className="dtools-dropdown-item"
            onClick={() => handleExport('csv')}
            disabled={downloading}
          >
            {downloading ? <Loader2 size={14} className="icon-spin" /> : <Download size={14} />}
            <span>CSV</span>
            <span className="dtools-dropdown-hint">Excel / Google Sheets</span>
          </button>
          <button
            className="dtools-dropdown-item"
            onClick={() => handleExport('json')}
            disabled={downloading}
          >
            {downloading ? <Loader2 size={14} className="icon-spin" /> : <Download size={14} />}
            <span>JSON</span>
            <span className="dtools-dropdown-hint">{lang === 'zh' ? '程序化分析' : 'Programmatic use'}</span>
          </button>
          {error && <p className="dtools-error">{error}</p>}
        </div>
      )}
    </div>
  );
}

/* ── Alerts Panel ── */

function AlertsPanel({ lang }: { lang: 'zh' | 'en' }) {
  const [open, setOpen] = useState(false);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [matches, setMatches] = useState<NewMatch[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // New alert form state
  const [showForm, setShowForm] = useState(false);
  const [newKeyword, setNewKeyword] = useState('');
  const [newCategory, setNewCategory] = useState('');
  const [newMinScore, setNewMinScore] = useState(50);
  const [submitting, setSubmitting] = useState(false);

  const fetchAlerts = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/alerts');
      if (res.ok) {
        const data: AlertsData = await res.json();
        setAlerts(data.alerts);
        setMatches(data.newMatches);
      }
    } catch { /* best effort */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    if (open) fetchAlerts();
  }, [open, fetchAlerts]);

  const handleCreate = useCallback(async () => {
    if (!newKeyword.trim()) return;
    setSubmitting(true);
    setError('');
    try {
      const res = await fetch('/api/alerts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          keyword: newKeyword.trim(),
          category: newCategory || null,
          minScore: newMinScore,
        }),
      });
      if (res.ok) {
        setNewKeyword('');
        setNewCategory('');
        setNewMinScore(50);
        setShowForm(false);
        await fetchAlerts();
      } else {
        const data = await res.json();
        setError(data.error || (lang === 'zh' ? '创建失败' : 'Failed to create'));
      }
    } catch {
      setError(lang === 'zh' ? '网络错误' : 'Network error');
    } finally {
      setSubmitting(false);
    }
  }, [newKeyword, newCategory, newMinScore, lang, fetchAlerts]);

  const handleDelete = useCallback(async (id: string) => {
    try {
      const res = await fetch(`/api/alerts?id=${id}`, { method: 'DELETE' });
      if (res.ok) {
        setAlerts((prev) => prev.filter((a) => a.id !== id));
      }
    } catch { /* best effort */ }
  }, []);

  const handleToggle = useCallback(async (id: string, enabled: boolean) => {
    try {
      await fetch(`/api/alerts?id=${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      });
      setAlerts((prev) => prev.map((a) => (a.id === id ? { ...a, enabled } : a)));
    } catch { /* best effort */ }
  }, []);

  const matchCount = matches.length;
  const isEn = lang === 'en';

  return (
    <div className="dtools-action">
      <button
        className="dtools-btn"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        title={isEn ? 'Trend Alerts' : '趋势提醒'}
      >
        <Bell size={14} />
        <span>{isEn ? 'Alerts' : '提醒'}</span>
        {matchCount > 0 && <span className="dtools-badge">{matchCount}</span>}
      </button>

      {open && (
        <div className="dtools-panel">
          <div className="dtools-panel-header">
            <h3>{isEn ? 'Trend Alerts' : '趋势提醒'}</h3>
            <button className="dtools-close" onClick={() => setOpen(false)} aria-label={isEn ? 'Close' : '关闭'}>
              <X size={16} />
            </button>
          </div>

          {/* ── New Matches ── */}
          {matches.length > 0 && (
            <div className="dtools-matches">
              <p className="dtools-matches-title">
                {isEn ? 'New matches since your last visit:' : '上次访问以来的新匹配：'}
              </p>
              {matches.map((m) => (
                <div key={m.alertId} className="dtools-match">
                  <Check size={12} />
                  <span className="dtools-match-kw">"{m.keyword}"</span>
                  <span className="dtools-match-arrow">→</span>
                  <a href={`/trends/${m.matchedTerm.toLowerCase().replace(/\s+/g, '-')}/`} className="dtools-match-term">
                    {m.matchedTerm}
                  </a>
                </div>
              ))}
            </div>
          )}

          {/* ── Alert List ── */}
          {loading ? (
            <div className="dtools-loading">
              <Loader2 size={16} className="icon-spin" />
            </div>
          ) : alerts.length === 0 ? (
            <p className="dtools-empty">
              {isEn
                ? 'No alerts set. Get notified when a trend matching your keywords crosses the score threshold.'
                : '还没有提醒。当匹配关键词的趋势超过分数阈值时通知你。'}
            </p>
          ) : (
            <div className="dtools-alert-list">
              {alerts.map((a) => (
                <div key={a.id} className={`dtools-alert-item ${a.enabled ? '' : 'disabled'}`}>
                  <div className="dtools-alert-info">
                    <span className="dtools-alert-kw">"{a.keyword}"</span>
                    {a.category && <span className="dtools-alert-cat">{a.category}</span>}
                    <span className="dtools-alert-score">≥{a.minScore}</span>
                  </div>
                  <div className="dtools-alert-actions">
                    <button
                      className="dtools-alert-toggle"
                      onClick={() => handleToggle(a.id, !a.enabled)}
                      title={a.enabled ? (isEn ? 'Pause' : '暂停') : (isEn ? 'Enable' : '启用')}
                    >
                      {a.enabled ? <Bell size={12} /> : <BellOff size={12} />}
                    </button>
                    <button
                      className="dtools-alert-delete"
                      onClick={() => handleDelete(a.id)}
                      title={isEn ? 'Delete' : '删除'}
                    >
                      <X size={12} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* ── Add Form ── */}
          {showForm ? (
            <div className="dtools-form">
              <input
                className="dtools-input"
                type="text"
                value={newKeyword}
                onChange={(e) => setNewKeyword(e.target.value)}
                placeholder={isEn ? 'Keyword (e.g. "agent", "mcp")' : '关键词（如 "agent", "mcp"）'}
                onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
                autoFocus
              />
              <div className="dtools-form-row">
                <select
                  className="dtools-select"
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value)}
                >
                  <option value="">{isEn ? 'Any category' : '不限品类'}</option>
                  {VALID_CATEGORIES.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
                <input
                  className="dtools-input dtools-input-sm"
                  type="number"
                  min={0}
                  max={100}
                  value={newMinScore}
                  onChange={(e) => setNewMinScore(Number(e.target.value))}
                  title={isEn ? 'Minimum score' : '最低分数'}
                />
              </div>
              {error && <p className="dtools-error">{error}</p>}
              <div className="dtools-form-actions">
                <button className="dtools-submit" onClick={handleCreate} disabled={submitting || !newKeyword.trim()}>
                  {submitting ? <Loader2 size={14} className="icon-spin" /> : null}
                  {isEn ? 'Create Alert' : '创建提醒'}
                </button>
                <button className="dtools-cancel" onClick={() => { setShowForm(false); setError(''); }}>
                  {isEn ? 'Cancel' : '取消'}
                </button>
              </div>
            </div>
          ) : (
            <button className="dtools-add-btn" onClick={() => setShowForm(true)} disabled={alerts.length >= 10}>
              <Plus size={14} />
              {isEn ? 'Add Alert' : '添加提醒'}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Main Component ── */

interface DashboardToolsProps {
  lang: 'zh' | 'en';
}

export default function DashboardTools({ lang }: DashboardToolsProps) {
  return (
    <div className="dtools-bar">
      <ExportButton lang={lang} />
      <AlertsPanel lang={lang} />
    </div>
  );
}
