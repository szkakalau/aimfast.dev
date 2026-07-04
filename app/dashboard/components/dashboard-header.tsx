'use client';

type Props = {
  lang: 'zh' | 'en';
  onToggleLang: () => void;
  title: string;
  date: string;
};

export function DashboardHeader({ lang, onToggleLang, title, date }: Props) {
  return (
    <header className="dash-header">
      <h1 id="header-title">
        <svg className="icon icon-accent" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="4" />
          <path d="M4.93 4.93a10 10 0 0 1 14.14 0M4.93 19.07a10 10 0 0 0 14.14 0" />
        </svg>
        {title}
      </h1>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <button className="lang-toggle" onClick={onToggleLang} title="Switch Language / 切换语言">
          {lang === 'zh' ? 'EN' : '中文'}
        </button>
        <span className="date">{date}</span>
      </div>
    </header>
  );
}
