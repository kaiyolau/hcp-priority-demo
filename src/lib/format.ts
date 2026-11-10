export type ScoreTier = 'high' | 'medium' | 'low';

export function scoreTier(score: number): ScoreTier {
  if (score >= 60) return 'high';
  if (score >= 35) return 'medium';
  return 'low';
}

export function formatGrowth(pct: number): string {
  return `${pct > 0 ? '+' : ''}${pct}%`;
}

/** Month labels for an Rx history whose last entry is "last month". */
export function monthLabels(length: number, now: Date = new Date()): string[] {
  const fmt = new Intl.DateTimeFormat('en-CA', { month: 'short' });
  return Array.from({ length }, (_, i) => {
    const monthsAgo = length - i;
    return fmt.format(new Date(now.getFullYear(), now.getMonth() - monthsAgo, 1));
  });
}
