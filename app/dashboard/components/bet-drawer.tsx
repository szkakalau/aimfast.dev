'use client';

type Props = {
  t: Record<string, string>;
  demandName: string;
  action: string;
  timeline: number;
  thesis: string;
  criteria: string;
  onActionChange: (action: string) => void;
  onTimelineChange: (days: number) => void;
  onThesisChange: (thesis: string) => void;
  onCriteriaChange: (criteria: string) => void;
  onConfirm: () => void;
  onClose: () => void;
};

export function BetDrawer({
  t,
  demandName,
  action,
  timeline,
  thesis,
  criteria,
  onActionChange,
  onTimelineChange,
  onThesisChange,
  onCriteriaChange,
  onConfirm,
  onClose,
}: Props) {
  return (
    <div className="bet-drawer-overlay" onClick={onClose}>
      <div className="bet-drawer" onClick={(e) => e.stopPropagation()}>
        <div className="bet-drawer-header">
          <h3>{t.betDrawerTitle}</h3>
          <button className="bet-drawer-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>
        <div className="bet-drawer-body">
          <div className="bet-drawer-demand">{demandName}</div>

          {/* Action selection */}
          <div className="bet-drawer-actions">
            {(['observe', 'validate', 'build'] as const).map((act) => (
              <button
                key={act}
                className={`btn-bet-action ${action === act ? 'active' : ''}`}
                onClick={() => onActionChange(act)}
              >
                {act === 'observe' && `🔍 ${t.betActionObserve}`}
                {act === 'validate' && `🧪 ${t.betActionValidate}`}
                {act === 'build' && `🔨 ${t.betActionBuild}`}
              </button>
            ))}
          </div>

          <label className="bet-drawer-label">Thesis</label>
          <textarea
            className="bet-drawer-input"
            rows={3}
            placeholder="Why is this worth betting on?"
            value={thesis}
            onChange={(e) => onThesisChange(e.target.value)}
          />

          <label className="bet-drawer-label">Success Criteria (optional)</label>
          <textarea
            className="bet-drawer-input"
            rows={2}
            placeholder="How will you know if this bet is successful?"
            value={criteria}
            onChange={(e) => onCriteriaChange(e.target.value)}
          />

          <label className="bet-drawer-label">Timeline</label>
          <div className="bet-drawer-timeline">
            {[7, 14, 30].map((days) => (
              <button
                key={days}
                className={`btn-timeline ${timeline === days ? 'active' : ''}`}
                onClick={() => onTimelineChange(days)}
              >
                {days} days
              </button>
            ))}
          </div>
        </div>
        <div className="bet-drawer-footer">
          <button className="btn btn-outline" onClick={onClose}>
            {t.betCancel}
          </button>
          <button className="btn btn-primary" onClick={onConfirm}>
            {t.betConfirm}
          </button>
        </div>
      </div>
    </div>
  );
}
