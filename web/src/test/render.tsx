import { ApiError, type ApiClient, type RecommendationsResponse, type Settings } from '@dining/core';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import type { ReactElement } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { vi } from 'vitest';
import { ApiProvider } from '../api';

export const SETTINGS: Settings = {
  protein_target_g: 100,
  calorie_limit: 1800,
  meals_per_day: 3,
  day_start: '07:00',
  day_end: '21:00',
  restricted_keywords: ['beef', 'pork'],
  building_coords: { WALC: [40.4274, -86.9132] },
};

function rec(rank: number, hall: string, meal: string, total: number, dish: string) {
  return {
    rank,
    dining_hall: hall,
    meal,
    window: { start: '2026-09-29T15:30:00Z', end: '2026-09-29T17:00:00Z' },
    scores: { total, nutrition: 0.9, time: 1, proximity: null },
    plate: [
      {
        id: dish, name: dish, station: 'Grill', is_vegetarian: false, allergens: [],
        nutrition: { calories: 320, protein_g: 42, fat_g: 6, carbs_g: 12, serving_size: '1 each' },
      },
    ],
  };
}

export const PLAN: RecommendationsResponse = {
  date: '2026-09-29',
  meal: null,
  goal_per_meal: { protein_g: 33.3, calories: 600 },
  windows: [{ start: '2026-09-29T15:30:00Z', end: '2026-09-29T17:00:00Z' }],
  recommendations: [rec(1, 'Wiley', 'Lunch', 0.86, 'Grilled Chicken'), rec(2, 'Ford', 'Dinner', 0.71, 'Turkey Burger')],
  notice: null,
  warnings: [],
};

export function fakeApi(overrides: Partial<ApiClient> = {}) {
  return {
    getSettings: vi.fn(async () => structuredClone(SETTINGS)),
    updateSettings: vi.fn(async (s: Settings) => s),
    getMeals: vi.fn(async (date?: string) => ({ date: date ?? '2026-09-29', meals: ['Breakfast', 'Lunch', 'Dinner'] })),
    getMeta: vi.fn(async () => ({ calendar_source: 'ical' as const })),
    getRecommendations: vi.fn(async () => structuredClone(PLAN)),
    ...overrides,
  } satisfies ApiClient;
}

export function apiError(status: number, code: string, message: string, fields?: Record<string, string>) {
  return new ApiError(status, code, message, fields);
}

export function renderWithApp(ui: ReactElement, { api = fakeApi(), route = '/' } = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const result = render(
    <ApiProvider client={api}>
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[route]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>{ui}</MemoryRouter>
      </QueryClientProvider>
    </ApiProvider>,
  );
  return { ...result, api };
}
