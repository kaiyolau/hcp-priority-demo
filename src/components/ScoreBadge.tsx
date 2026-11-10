import { scoreTier } from '../lib/format';

export function ScoreBadge({ score }: { score: number }) {
  const tier = scoreTier(score);
  return (
    <span className="score" data-tier={tier} aria-label={`Score ${score} of 100, ${tier} priority`}>
      <span className="score__value">{score}</span>
      <span className="score__track" aria-hidden="true">
        <span className="score__fill" style={{ width: `${score}%` }} />
      </span>
    </span>
  );
}
