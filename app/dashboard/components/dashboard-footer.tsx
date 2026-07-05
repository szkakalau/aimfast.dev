'use client';

import { useState, useEffect } from 'react';

type Props = {
  t: Record<string, string>;
  generatedAt: string;
};

export function DashboardFooter({ t, generatedAt }: Props) {
  const [countdown, setCountdown] = useState('');

  useEffect(() => {
    function updateCountdown() {
      const now = new Date();
      // Next refresh: today or tomorrow at 08:30 CST (00:30 UTC)
      const next = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), 0, 30, 0));
      if (next <= now) {
        next.setUTCDate(next.getUTCDate() + 1);
      }
      const diff = next.getTime() - now.getTime();
      const h = Math.floor(diff / (1000 * 60 * 60));
      const m = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      setCountdown(`${h}h ${m}m`);
    }

    updateCountdown();
    const interval = setInterval(updateCountdown, 60_000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="dash-footer">
      <span>AimFast.Dev</span>
      <span className="footer-sep">·</span>
      <span>{generatedAt ? new Date(generatedAt).toLocaleString() : '--'}</span>
      <span className="footer-sep">·</span>
      <span>{t.footerRefresh}</span>
      {countdown && (
        <>
          <span className="footer-sep">·</span>
          <span className="footer-countdown">
            {t.footerNextUpdate || 'Next update'}: {countdown}
          </span>
        </>
      )}
    </div>
  );
}
