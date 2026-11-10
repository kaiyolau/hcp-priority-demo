export interface Doctor {
  id: string;
  rank: number;
  name: string;
  specialty: string;
  city: string;
  score: number;
  rxHistory: number[];
  rxLastMonth: number;
  rxWindowStart: number;
  growthPct3m: number;
  daysSinceLastVisit: number;
  breakdown: { growthPoints: number; recencyPoints: number };
}

export interface DoctorList {
  scoringVersion: string;
  count: number;
  doctors: Doctor[];
}

export interface Explanation {
  doctorId: string;
  text: string;
  source: 'llm' | 'rules';
  model: string | null;
  cached: boolean;
  latencyMs: number;
  attempts: number;
  fallbackReason: string | null;
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(path, { headers: { Accept: 'application/json' } });
  if (!res.ok) throw new Error(`${path} failed with ${res.status}`);
  return (await res.json()) as T;
}

export const fetchDoctors = () => getJson<DoctorList>('/api/doctors');

export const fetchExplanation = (id: string) =>
  getJson<Explanation>(`/api/doctors/${encodeURIComponent(id)}/explain`);
