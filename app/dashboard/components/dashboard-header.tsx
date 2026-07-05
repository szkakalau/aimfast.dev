'use client';

type Props = {
  lang: 'zh' | 'en';
  onToggleLang: () => void;
  title: string;
  date: string;
  dates: string[];
  onSelectDate: (date: string) => void;
};

export function DashboardHeader({ lang, onToggleLang, title, date, dates, onSelectDate }: Props) {
  return (
    <header className="dash-header">
      <div className="dash-header-left">
        <h1>
          <svg className="icon icon-accent" viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="12" cy="12" r="4" />
            <path d="M4.93 4.93a10 10 0 0 1 14.14 0M4.93 19.07a10 10 0 0 0 14.14 0" />
          </svg>
          {title}
        </h1>
      </div>

      <div className="dash-header-right">
        {/* Date picker */}
        {dates.length > 1 ? (
          <select
            className="date-select"
            value={date}
            onChange={(e) => onSelectDate(e.target.value)}
            aria-label="Select date"
          >
            {dates.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        ) : (
          <span className="date">{date}</span>
        )}

        {/* Language toggle */}
        <button
          className="lang-toggle"
          onClick={onToggleLang}
          title="Switch Language / 切换语言"
        >
          {lang === 'zh' ? 'EN' : '中文'}
        </button>
      </div>
    </header>
  );
}
