import type { Doctor, Explanation } from '../api';

export function makeDoctor(overrides: Partial<Doctor> = {}): Doctor {
  return {
    id: 'hcp-001',
    rank: 1,
    name: 'Dr. Test One',
    specialty: 'Cardiology',
    city: 'Vancouver',
    score: 78,
    rxHistory: [60, 62, 65, 70, 80, 90],
    rxLastMonth: 90,
    rxWindowStart: 65,
    growthPct3m: 38,
    daysSinceLastVisit: 45,
    breakdown: { growthPoints: 58, recencyPoints: 20 },
    ...overrides,
  };
}

export const DOCTORS: Doctor[] = [
  makeDoctor(),
  makeDoctor({ id: 'hcp-002', rank: 2, name: 'Dr. Test Two', specialty: 'Oncology', city: 'Toronto', score: 40, growthPct3m: -5 }),
  makeDoctor({ id: 'hcp-003', rank: 3, name: 'Dr. Test Three', specialty: 'Neurology', city: 'Calgary', score: 12, growthPct3m: -20 }),
];

export function explanationFor(id: string): Explanation {
  return {
    doctorId: id,
    text: `Explanation for ${id}`,
    source: 'llm',
    model: 'test-model',
    cached: false,
    latencyMs: 120,
    attempts: 1,
    fallbackReason: null,
  };
}
