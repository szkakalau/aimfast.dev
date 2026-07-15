/** Shared UI labels for trend terms — single source of truth for stage names. */

export function stageLabel(stage: string): string {
  const map: Record<string, string> = {
    nascent: 'Nascent (0-7d)',
    emergent: 'Emergent (8-30d)',
    validating: 'Validating (31-90d)',
    rising: 'Rising (90d+)',
  };
  return map[stage] || stage;
}

export const STAGES = ['all', 'nascent', 'emergent', 'validating', 'rising'] as const;
export type StageFilter = (typeof STAGES)[number];
