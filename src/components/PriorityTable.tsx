import { useMemo, useState } from 'react';
import type { Doctor } from '../api';
import { formatGrowth } from '../lib/format';
import { ScoreBadge } from './ScoreBadge';

type SortKey = 'rank' | 'name' | 'specialty' | 'growthPct3m' | 'daysSinceLastVisit' | 'score';
type SortDir = 'asc' | 'desc';

interface Props {
  doctors: Doctor[];
  selectedId: string | null;
  onSelect: (id: string, opts?: { reveal?: boolean }) => void;
}

const COLUMNS: { key: SortKey; label: string; className?: string }[] = [
  { key: 'rank', label: 'Rank' },
  { key: 'name', label: 'HCP' },
  { key: 'specialty', label: 'Specialty', className: 'col-optional' },
  { key: 'growthPct3m', label: '3-mo Rx trend', className: 'col-optional' },
  { key: 'daysSinceLastVisit', label: 'Last visit', className: 'col-optional' },
  { key: 'score', label: 'Score' },
];

export function PriorityTable({ doctors, selectedId, onSelect }: Props) {
  const [query, setQuery] = useState('');
  const [specialty, setSpecialty] = useState('all');
  const [sort, setSort] = useState<{ key: SortKey; dir: SortDir }>({ key: 'rank', dir: 'asc' });

  const specialties = useMemo(() => [...new Set(doctors.map((d) => d.specialty))].sort(), [doctors]);

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    const filtered = doctors.filter(
      (d) =>
        (specialty === 'all' || d.specialty === specialty) &&
        (!q || d.name.toLowerCase().includes(q) || d.city.toLowerCase().includes(q)),
    );
    const factor = sort.dir === 'asc' ? 1 : -1;
    return [...filtered].sort((a, b) => {
      const av = a[sort.key];
      const bv = b[sort.key];
      const cmp = typeof av === 'string' ? av.localeCompare(bv as string) : (av as number) - (bv as number);
      return cmp * factor || a.rank - b.rank;
    });
  }, [doctors, query, specialty, sort]);

  const toggleSort = (key: SortKey) =>
    setSort((s) => {
      if (s.key === key) return { key, dir: s.dir === 'asc' ? 'desc' : 'asc' };
      // Text and rank read naturally ascending; numeric signals read best highest-first.
      const ascFirst: SortKey[] = ['rank', 'name', 'specialty'];
      return { key, dir: ascFirst.includes(key) ? 'asc' : 'desc' };
    });

  const onRowKeyDown = (e: React.KeyboardEvent<HTMLTableRowElement>, index: number) => {
    const move = (next: number) => {
      const target = rows[next];
      if (!target) return;
      e.preventDefault();
      onSelect(target.id);
      (e.currentTarget.parentElement?.children[next] as HTMLElement | undefined)?.focus();
    };
    if (e.key === 'ArrowDown') move(index + 1);
    if (e.key === 'ArrowUp') move(index - 1);
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onSelect(rows[index].id, { reveal: true });
    }
  };

  return (
    <section className="board" aria-labelledby="board-title">
      <div className="board__toolbar">
        <h2 id="board-title" className="board__title">
          Visit priority <span className="board__count">{rows.length} HCPs</span>
        </h2>
        <div className="board__filters">
          <label className="field">
            <span className="visually-hidden">Search by name or city</span>
            <input
              type="search"
              placeholder="Search name or city"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
          <label className="field">
            <span className="visually-hidden">Filter by specialty</span>
            <select value={specialty} onChange={(e) => setSpecialty(e.target.value)}>
              <option value="all">All specialties</option>
              {specialties.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      <div className="table-wrap">
        <table className="table" aria-describedby="table-help">
          <caption id="table-help" className="visually-hidden">
            HCPs ranked by visit priority. Use arrow keys to move between rows; the details panel updates.
          </caption>
          <thead>
            <tr>
              {COLUMNS.map((col) => {
                const active = sort.key === col.key;
                return (
                  <th
                    key={col.key}
                    scope="col"
                    className={col.className}
                    aria-sort={active ? (sort.dir === 'asc' ? 'ascending' : 'descending') : undefined}
                  >
                    <button type="button" className="th-sort" onClick={() => toggleSort(col.key)}>
                      {col.label}
                      <span aria-hidden="true" className="th-sort__icon">
                        {active ? (sort.dir === 'asc' ? '▲' : '▼') : '↕'}
                      </span>
                    </button>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {rows.map((d, i) => {
              const selected = d.id === selectedId;
              return (
                <tr
                  key={d.id}
                  tabIndex={0}
                  aria-selected={selected}
                  className={selected ? 'is-selected' : undefined}
                  onClick={() => onSelect(d.id, { reveal: true })}
                  onKeyDown={(e) => onRowKeyDown(e, i)}
                  data-testid={`row-${d.id}`}
                >
                  <td className="cell-rank">{String(d.rank).padStart(2, '0')}</td>
                  <td>
                    <div className="cell-name">{d.name}</div>
                    <div className="cell-sub">{d.city}</div>
                  </td>
                  <td className="col-optional">{d.specialty}</td>
                  <td className="col-optional">
                    <span className="trend" data-dir={d.growthPct3m > 0 ? 'up' : d.growthPct3m < 0 ? 'down' : 'flat'}>
                      {formatGrowth(d.growthPct3m)}
                    </span>
                  </td>
                  <td className="col-optional">{d.daysSinceLastVisit}d ago</td>
                  <td>
                    <ScoreBadge score={d.score} />
                  </td>
                </tr>
              );
            })}
            {rows.length === 0 && (
              <tr>
                <td colSpan={COLUMNS.length} className="empty">
                  No HCPs match these filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
