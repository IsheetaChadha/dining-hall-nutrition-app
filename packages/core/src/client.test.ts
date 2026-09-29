import { describe, expect, it } from 'vitest';
import { createApiClient, type FetchLike } from './client';
import { ApiError } from './errors';

type Call = { url: string; method: string; body?: unknown };

function fakeFetch(status: number, body: unknown, calls: Call[] = []): FetchLike {
  return async (url, init) => {
    calls.push({ url, method: init?.method ?? 'GET', body: init?.body ? JSON.parse(init.body) : undefined });
    return { ok: status >= 200 && status < 300, status, json: async () => body };
  };
}

describe('createApiClient', () => {
  it('posts a recommendations request as JSON under /api/v1', async () => {
    const calls: Call[] = [];
    const api = createApiClient({ baseUrl: 'http://host', fetch: fakeFetch(200, { recommendations: [] }, calls) });

    await api.getRecommendations({ date: '2026-09-30', meal: 'Lunch' });

    expect(calls).toEqual([
      { url: 'http://host/api/v1/recommendations', method: 'POST', body: { date: '2026-09-30', meal: 'Lunch' } },
    ]);
  });

  it('asks for a day of meals with an encoded date query', async () => {
    const calls: Call[] = [];
    const api = createApiClient({ baseUrl: '', fetch: fakeFetch(200, { date: '2026-09-30', meals: [] }, calls) });

    await api.getMeals('2026-09-30');
    await api.getMeals();

    expect(calls.map((c) => c.url)).toEqual(['/api/v1/meals?date=2026-09-30', '/api/v1/meals']);
  });

  it('puts settings and returns what the server saved', async () => {
    const saved = { protein_target_g: 120 };
    const calls: Call[] = [];
    const api = createApiClient({ baseUrl: '', fetch: fakeFetch(200, saved, calls) });

    const result = await api.updateSettings(saved as never);

    expect(calls[0]).toMatchObject({ url: '/api/v1/settings', method: 'PUT', body: saved });
    expect(result).toEqual(saved);
  });

  it('turns an API error body into a typed ApiError', async () => {
    const api = createApiClient({
      baseUrl: '',
      fetch: fakeFetch(422, {
        error: { code: 'invalid_settings', message: "Some values aren't valid.", fields: { meals_per_day: 'Too many' } },
      }),
    });

    const error = await api.getSettings().catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 422,
      code: 'invalid_settings',
      message: "Some values aren't valid.",
      fields: { meals_per_day: 'Too many' },
    });
  });

  it('reports a non-JSON failure as an http_error with its status', async () => {
    const fetch: FetchLike = async () => ({ ok: false, status: 500, json: async () => { throw new SyntaxError('not json'); } });
    const api = createApiClient({ baseUrl: '', fetch });

    await expect(api.getMeta()).rejects.toMatchObject({ status: 500, code: 'http_error' });
  });

  it('reports an unreachable server as a network_error', async () => {
    const fetch: FetchLike = async () => { throw new TypeError('Failed to fetch'); };
    const api = createApiClient({ baseUrl: '', fetch });

    await expect(api.getMeta()).rejects.toMatchObject({ status: 0, code: 'network_error' });
  });
});
