'use client';

type Props = {
  t: Record<string, string>;
  generatedAt: string;
};

export function DashboardFooter({ t, generatedAt }: Props) {
  return (
    <div className="dash-footer">
      <span>AimFast.Dev</span>
      {' · '}
      <span>{generatedAt ? new Date(generatedAt).toLocaleString() : '--'}</span>
      {' · '}
      <span>{t.footerRefresh}</span>
    </div>
  );
}
