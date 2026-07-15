'use client';

import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorBannerProps {
  /** Human-readable description of what failed, e.g. "Watchlist data" */
  section?: string;
  /** Called when user clicks retry. If omitted, the retry button is hidden. */
  onRetry?: () => void;
  /** Override the default message. Falls back to a section-prefixed generic message. */
  message?: string;
}

/**
 * Section-level error banner — compact, non-blocking.
 * Shows when a specific section's data fetch fails, while the rest of the page remains functional.
 */
export default function ErrorBanner({ section, onRetry, message }: ErrorBannerProps) {
  const text = message || (section
    ? `${section} data temporarily unavailable`
    : 'Data temporarily unavailable');

  return (
    <div
      className="error-banner"
      role="alert"
      aria-live="polite"
    >
      <AlertTriangle size={16} aria-hidden="true" />
      <span className="error-banner-text">{text}</span>
      {onRetry && (
        <button
          type="button"
          className="error-banner-retry"
          onClick={onRetry}
        >
          <RefreshCw size={14} aria-hidden="true" />
          Retry
        </button>
      )}
    </div>
  );
}
