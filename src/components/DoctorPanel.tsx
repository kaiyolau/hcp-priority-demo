import { useQuery } from '@tanstack/react-query';
import { lazy, Suspense } from 'react';
import { fetchExplanation, type Doctor, type Explanation } from '../api';
import { formatGrowth, scoreTier } from '../lib/format';

// Recharts is the largest dependency; load it after the table renders.
const RxTrendChart = lazy(() => import('./RxTrendChart').then((m) => ({ default: m.RxTrendChart })));

interface Props {
  doctor: Doctor;
  total: number;
  onClose: () => void;
}

export function DoctorPanel({ doctor, total, onClose }: Props) {
  const tier = scoreTier(doctor.score);

  return (
    <aside id="detail-panel" className="panel" aria-labelledby="panel-title">
      <header className="panel__head">
        <div>
          <p className="eyebrow">
            Rank {doctor.rank} of {total} · {doctor.specialty} · {doctor.city}
          </p>
          <h2 id="panel-title" className="panel__title">
            {doctor.name}
          </h2>
        </div>
        <button type="button" className="icon-btn panel__close" onClick={onClose} aria-label="Close details">
          ×
        </button>
      </header>

      <AiExplanation doctorId={doctor.id} />

      <div className="panel__stats">
        <div className="stat" data-tier={tier}>
          <span className="stat__label">Priority score</span>
          <span className="stat__value">{doctor.score}</span>
        </div>
        <div className="stat">
          <span className="stat__label">Rx last month</span>
          <span className="stat__value">{doctor.rxLastMonth}</span>
        </div>
        <div className="stat">
          <span className="stat__label">3-mo trend</span>
          <span className="stat__value">{formatGrowth(doctor.growthPct3m)}</span>
        </div>
        <div className="stat">
          <span className="stat__label">Since last visit</span>
          <span className="stat__value">
            {doctor.daysSinceLastVisit}
            <small>d</small>
          </span>
        </div>
      </div>

      <Suspense fallback={<div className="chart-placeholder" aria-hidden="true" />}>
        <RxTrendChart history={doctor.rxHistory} />
      </Suspense>

      <ScoreBreakdown doctor={doctor} />
    </aside>
  );
}

function AiExplanation({ doctorId }: { doctorId: string }) {
  const { data, isPending, isError, refetch } = useQuery({
    queryKey: ['explain', doctorId],
    queryFn: () => fetchExplanation(doctorId),
    staleTime: Infinity,
  });

  return (
    <section className="ai" aria-labelledby="ai-title" aria-busy={isPending}>
      <div className="ai__head">
        <h3 id="ai-title" className="ai__title">
          <span className="ai__spark" aria-hidden="true">
            ✦
          </span>
          Why visit now
        </h3>
        {data && <SourceBadge explanation={data} />}
      </div>
      <div aria-live="polite">
        {isPending && (
          <div className="ai__skeleton" role="status">
            <span className="visually-hidden">Generating explanation…</span>
            <span />
            <span />
          </div>
        )}
        {isError && (
          <p className="ai__error">
            Could not load the explanation.{' '}
            <button type="button" className="link-btn" onClick={() => refetch()}>
              Try again
            </button>
          </p>
        )}
        {data && <p className="ai__text">{data.text}</p>}
      </div>
      {data && (
        <p className="ai__meta">
          {data.source === 'llm'
            ? 'Every number above was checked against this HCP’s data before display.'
            : 'Written from this HCP’s data by a rules template (LLM unavailable or answer failed checks).'}{' '}
          {data.cached ? 'Served from cache.' : `${data.latencyMs} ms${data.attempts > 1 ? `, ${data.attempts} attempts` : ''}.`}
        </p>
      )}
    </section>
  );
}

function SourceBadge({ explanation }: { explanation: Explanation }) {
  if (explanation.source === 'llm') {
    return (
      <span className="badge badge--ai" title={explanation.model ?? undefined}>
        AI · {explanation.model}
      </span>
    );
  }
  return (
    <span className="badge" title={explanation.fallbackReason ?? undefined}>
      Rules fallback
    </span>
  );
}

function ScoreBreakdown({ doctor }: { doctor: Doctor }) {
  const { growthPoints, recencyPoints } = doctor.breakdown;
  return (
    <section className="breakdown" aria-labelledby="breakdown-title">
      <h3 id="breakdown-title" className="section-title">
        How the score is built
      </h3>
      <div className="breakdown__bar" role="img" aria-label={`Rx growth ${growthPoints} of 60 points, visit gap ${recencyPoints} of 40 points`}>
        <span className="breakdown__growth" style={{ width: `${growthPoints}%` }} />
        <span className="breakdown__recency" style={{ width: `${recencyPoints}%` }} />
      </div>
      <dl className="breakdown__legend">
        <div>
          <dt>
            <i className="dot dot--growth" /> Rx growth
          </dt>
          <dd>
            {growthPoints} / 60 pts
          </dd>
        </div>
        <div>
          <dt>
            <i className="dot dot--recency" /> Visit gap
          </dt>
          <dd>
            {recencyPoints} / 40 pts
          </dd>
        </div>
      </dl>
      <p className="note">
        Simplified, transparent rules for the demo: 60% weight on 3-month Rx growth (−20% → 0, +40% → max), 40% on days
        since the last visit (capped at 90). A production system would use a trained ML model.
      </p>
    </section>
  );
}
