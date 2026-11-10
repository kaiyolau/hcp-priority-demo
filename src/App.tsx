import { useQuery } from '@tanstack/react-query';
import { useCallback, useEffect, useState } from 'react';
import { fetchDoctors } from './api';
import { DoctorPanel } from './components/DoctorPanel';
import { PriorityTable } from './components/PriorityTable';

const REPO_URL = 'https://github.com/kaiyolau/hcp-priority-demo';

function readSelectedFromUrl(): string | null {
  return new URLSearchParams(window.location.search).get('hcp');
}

export default function App() {
  const { data, isPending, isError, refetch } = useQuery({ queryKey: ['doctors'], queryFn: fetchDoctors });
  const [selectedId, setSelectedId] = useState<string | null>(readSelectedFromUrl);
  const [panelOpen, setPanelOpen] = useState(true);

  // Open the top-ranked HCP by default so the AI explanation is visible on first load.
  const doctors = data?.doctors ?? [];
  const selected = doctors.find((d) => d.id === selectedId) ?? doctors[0];

  const select = useCallback((id: string, opts?: { reveal?: boolean }) => {
    setSelectedId(id);
    setPanelOpen(true);
    // On narrow screens the panel sits above the table, so bring it into view after a click.
    if (opts?.reveal && window.matchMedia('(max-width: 1079px)').matches) {
      requestAnimationFrame(() => document.getElementById('detail-panel')?.scrollIntoView({ behavior: 'smooth' }));
    }
    const url = new URL(window.location.href);
    url.searchParams.set('hcp', id);
    window.history.replaceState(null, '', url);
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setPanelOpen(false);
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <div className="topbar">
        <span className="topbar__tag">DEMO</span>
        <span>All HCPs and prescription numbers are synthetic.</span>
        <a href={REPO_URL} target="_blank" rel="noreferrer">
          View source
        </a>
      </div>
      <header className="nav">
        <span className="nav__brand">RX&nbsp;PRIORITY</span>
        <nav className="nav__links" aria-label="Project links">
          <a href="#how-it-works">How it works</a>
          <a href={REPO_URL} target="_blank" rel="noreferrer">
            GitHub
          </a>
        </nav>
      </header>

      <section className="hero">
        <h1 className="hero__title">Who should your reps visit this week?</h1>
        <p className="hero__lead">
          HCPs ranked by prescribing momentum and time since the last visit, each with a one-line AI explanation grounded
          only in that HCP’s data.
        </p>
      </section>

      <main id="main" className="layout" data-panel={panelOpen && selected ? 'open' : 'closed'}>
        {isPending && <p className="state">Loading HCPs…</p>}
        {isError && (
          <p className="state" role="alert">
            Could not load HCPs.{' '}
            <button type="button" className="link-btn" onClick={() => refetch()}>
              Retry
            </button>
          </p>
        )}
        {data && (
          <>
            <PriorityTable doctors={doctors} selectedId={selected?.id ?? null} onSelect={select} />
            {panelOpen && selected && (
              <DoctorPanel key={selected.id} doctor={selected} total={data.count} onClose={() => setPanelOpen(false)} />
            )}
          </>
        )}
      </main>

      <section id="how-it-works" className="how">
        <h2 className="how__title">How it works</h2>
        <ol className="how__steps">
          <li>
            <strong>Score.</strong> A FastAPI service loads the dataset into an embedded DuckDB database and ranks HCPs with
            one SQL query: faster 3-month Rx growth and a longer gap since the last visit mean a higher score.
          </li>
          <li>
            <strong>Explain.</strong> The selected HCP’s facts are sent to an LLM with instructions to use only those facts.
            Calls have timeouts, retries with backoff, and an in-memory cache.
          </li>
          <li>
            <strong>Verify.</strong> Every number in the answer is checked against the source data. If anything is
            invented, or the LLM is down, a deterministic rules-based sentence is shown instead.
          </li>
        </ol>
      </section>

      <footer className="footer">
        Portfolio demo built with React, TypeScript, FastAPI and DuckDB. Synthetic data only. Not affiliated with any
        company.
      </footer>
    </>
  );
}
