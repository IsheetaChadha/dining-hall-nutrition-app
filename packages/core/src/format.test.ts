import { describe, expect, it } from 'vitest';
import { dayLabel, formatWindow, goalDelta, plateTotals, scoreLabel, scoreToPercent, toISODate } from './format';
import type { PlateItem } from './types';

function item(name: string, calories: number, protein_g: number, fat_g = 0, carbs_g = 0): PlateItem {
  return {
    id: name, name, station: 'Grill', is_vegetarian: false, allergens: [],
    nutrition: { calories, protein_g, fat_g, carbs_g, serving_size: '1 each' },
  };
}

describe('formatWindow', () => {
  it('shows a free window as a start–end clock range in the given time zone', () => {
    expect(formatWindow('2026-09-29T15:30:00Z', '2026-09-29T17:00:00Z', 'America/Indiana/Indianapolis')).toBe(
      '11:30 AM – 1:00 PM',
    );
  });
});

describe('scores', () => {
  it('rounds a 0–1 score to a whole percent', () => {
    expect(scoreToPercent(0.826)).toBe(83);
    expect(scoreToPercent(1)).toBe(100);
  });

  it('labels scores by how well they fit', () => {
    expect(scoreLabel(0.85)).toBe('Great fit');
    expect(scoreLabel(0.65)).toBe('Good fit');
    expect(scoreLabel(0.45)).toBe('Fair fit');
    expect(scoreLabel(0.2)).toBe('Poor fit');
  });
});

describe('plate math', () => {
  it('totals the macros of every item with nutrition', () => {
    const noInfo: PlateItem = { ...item('Water', 0, 0), nutrition: null };

    expect(plateTotals([item('Chicken', 300, 40, 6, 2), item('Rice', 200, 4, 1, 44), noInfo])).toEqual({
      calories: 500, protein_g: 44, fat_g: 7, carbs_g: 46,
    });
  });

  it('compares plate totals with the per-meal goal', () => {
    const totals = { calories: 520, protein_g: 38, fat_g: 7, carbs_g: 46 };

    expect(goalDelta(totals, { protein_g: 40, calories: 600 })).toEqual({ protein_g: -2, calories: -80 });
  });
});

describe('dates', () => {
  const today = new Date(2026, 8, 29, 13, 0);

  it('formats a local date as YYYY-MM-DD', () => {
    expect(toISODate(today)).toBe('2026-09-29');
    expect(toISODate(new Date(2026, 0, 5))).toBe('2026-01-05');
  });

  it('names today and tomorrow, and spells out other days', () => {
    expect(dayLabel('2026-09-29', today)).toBe('Today');
    expect(dayLabel('2026-09-30', today)).toBe('Tomorrow');
    expect(dayLabel('2026-10-02', today)).toBe('Fri, Oct 2');
  });
});
