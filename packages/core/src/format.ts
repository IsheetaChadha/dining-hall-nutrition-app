import type { Goal, PlateItem } from './types';

export interface MacroTotals {
  calories: number;
  protein_g: number;
  fat_g: number;
  carbs_g: number;
}

/** "11:30 AM – 1:00 PM" in `timeZone` (default: the device's). */
export function formatWindow(startISO: string, endISO: string, timeZone?: string): string {
  const clock = new Intl.DateTimeFormat('en-US', { hour: 'numeric', minute: '2-digit', timeZone });
  // Newer ICU puts a narrow no-break space before AM/PM; normalize for predictable output.
  const fmt = (iso: string) => clock.format(new Date(iso)).replace(/ /g, ' ');
  return `${fmt(startISO)} – ${fmt(endISO)}`;
}

export function scoreToPercent(score: number): number {
  return Math.round(score * 100);
}

export function scoreLabel(score: number): string {
  if (score >= 0.8) return 'Great fit';
  if (score >= 0.6) return 'Good fit';
  if (score >= 0.4) return 'Fair fit';
  return 'Poor fit';
}

export function plateTotals(plate: PlateItem[]): MacroTotals {
  const totals: MacroTotals = { calories: 0, protein_g: 0, fat_g: 0, carbs_g: 0 };
  for (const { nutrition } of plate) {
    if (!nutrition) continue;
    totals.calories += nutrition.calories;
    totals.protein_g += nutrition.protein_g;
    totals.fat_g += nutrition.fat_g;
    totals.carbs_g += nutrition.carbs_g;
  }
  return totals;
}

/** Plate minus goal: negative protein is a shortfall, negative calories is room to spare. */
export function goalDelta(totals: MacroTotals, goal: Goal): { protein_g: number; calories: number } {
  return { protein_g: totals.protein_g - goal.protein_g, calories: totals.calories - goal.calories };
}

/** A local calendar date as YYYY-MM-DD (not UTC, unlike toISOString). */
export function toISODate(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

/** "Today", "Tomorrow", or e.g. "Fri, Oct 2". */
export function dayLabel(isoDate: string, today: Date = new Date()): string {
  const [year, month, day] = isoDate.split('-').map(Number) as [number, number, number];
  const date = new Date(year, month - 1, day);
  const tomorrow = new Date(today.getFullYear(), today.getMonth(), today.getDate() + 1);
  if (isoDate === toISODate(today)) return 'Today';
  if (isoDate === toISODate(tomorrow)) return 'Tomorrow';
  return new Intl.DateTimeFormat('en-US', { weekday: 'short', month: 'short', day: 'numeric' }).format(date);
}
