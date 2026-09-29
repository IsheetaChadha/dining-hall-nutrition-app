import type { RecommendationRequest } from '@dining/core';
import { useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';

export interface GoalOverrides {
  protein?: number;
  calories?: number;
  meals?: number;
}

function numberParam(params: URLSearchParams, key: string): number | undefined {
  const value = Number(params.get(key));
  return params.has(key) && Number.isFinite(value) && value > 0 ? value : undefined;
}

/** The plan being viewed lives in the URL, so it's linkable and survives a reload. */
export function usePlanParams() {
  const [params, setParams] = useSearchParams();

  const request = useMemo<RecommendationRequest>(() => {
    const req: RecommendationRequest = {};
    const date = params.get('date');
    const meal = params.get('meal');
    if (date) req.date = date;
    if (meal) req.meal = meal;
    for (const key of ['protein', 'calories', 'meals'] as const) {
      const value = numberParam(params, key);
      if (value !== undefined) req[key] = value;
    }
    return req;
  }, [params]);

  function update(changes: Record<string, string | number | undefined>) {
    setParams((current) => {
      const next = new URLSearchParams(current);
      for (const [key, value] of Object.entries(changes)) {
        if (value === undefined || value === '') next.delete(key);
        else next.set(key, String(value));
      }
      return next;
    });
  }

  return {
    request,
    setDate: (date: string | undefined) => update({ date, meal: undefined }),
    setMeal: (meal: string | undefined) => update({ meal }),
    setGoals: (goals: GoalOverrides) => update({ ...goals }),
    resetToNow: () => update({ date: undefined, meal: undefined }),
  };
}
