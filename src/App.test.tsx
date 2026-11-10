import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { DOCTORS, explanationFor } from './test/fixtures';
import { renderWithQuery } from './test/render';

// Recharts' ResponsiveContainer needs ResizeObserver, which jsdom lacks.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}

beforeEach(() => {
  vi.stubGlobal('ResizeObserver', ResizeObserverStub);
  vi.stubGlobal('matchMedia', () => ({ matches: false }));
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const explain = url.match(/\/api\/doctors\/(.+)\/explain$/);
      const body = explain ? explanationFor(decodeURIComponent(explain[1])) : { scoringVersion: 'rules-v1', count: 3, doctors: DOCTORS };
      return new Response(JSON.stringify(body), { status: 200 });
    }),
  );
  window.history.replaceState(null, '', '/');
});

afterEach(() => vi.unstubAllGlobals());

describe('App', () => {
  it('opens the top-ranked HCP with its AI explanation on first load', async () => {
    renderWithQuery(<App />);
    expect(await screen.findByRole('heading', { level: 2, name: 'Dr. Test One' })).toBeInTheDocument();
    expect(await screen.findByText('Explanation for hcp-001')).toBeInTheDocument();
    expect(screen.getByText('AI · test-model')).toBeInTheDocument();
  });

  it('shows details for a clicked row and records it in the URL', async () => {
    const user = userEvent.setup();
    renderWithQuery(<App />);
    await user.click(await screen.findByText('Dr. Test Two'));
    expect(await screen.findByText('Explanation for hcp-002')).toBeInTheDocument();
    await waitFor(() => expect(window.location.search).toBe('?hcp=hcp-002'));
  });
});
