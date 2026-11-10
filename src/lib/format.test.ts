import { describe, expect, it } from 'vitest';
import { formatGrowth, monthLabels, scoreTier } from './format';

describe('scoreTier', () => {
  it('buckets scores into high / medium / low', () => {
    expect(scoreTier(80)).toBe('high');
    expect(scoreTier(60)).toBe('high');
    expect(scoreTier(59)).toBe('medium');
    expect(scoreTier(35)).toBe('medium');
    expect(scoreTier(34)).toBe('low');
  });
});

describe('formatGrowth', () => {
  it('adds a plus sign only to positive numbers', () => {
    expect(formatGrowth(12)).toBe('+12%');
    expect(formatGrowth(-3)).toBe('-3%');
    expect(formatGrowth(0)).toBe('0%');
  });
});

describe('monthLabels', () => {
  it('ends with the month before "now"', () => {
    expect(monthLabels(3, new Date(2026, 10, 9))).toEqual(['Aug', 'Sep', 'Oct']);
  });
});
