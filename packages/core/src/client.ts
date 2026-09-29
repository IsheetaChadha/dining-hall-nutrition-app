import { ApiError } from './errors';
import type {
  MealsResponse,
  MetaResponse,
  RecommendationRequest,
  RecommendationsResponse,
  Settings,
} from './types';

/** The slice of `fetch` the client needs, so web (window.fetch) and React Native can both supply one. */
export type FetchLike = (
  url: string,
  init?: { method?: string; headers?: Record<string, string>; body?: string },
) => Promise<{ ok: boolean; status: number; json(): Promise<unknown> }>;

export interface ApiClientOptions {
  /** Origin of the API server; '' for same-origin (web). */
  baseUrl: string;
  fetch: FetchLike;
}

export type ApiClient = ReturnType<typeof createApiClient>;

export function createApiClient({ baseUrl, fetch }: ApiClientOptions) {
  async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
    let response: Awaited<ReturnType<FetchLike>>;
    try {
      response = await fetch(`${baseUrl}/api/v1${path}`, {
        method,
        headers: body === undefined ? { Accept: 'application/json' } : { Accept: 'application/json', 'Content-Type': 'application/json' },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch {
      throw new ApiError(0, 'network_error', "Can't reach the planner server. Is it running?");
    }

    const payload = await response.json().catch(() => undefined);
    if (response.ok) return payload as T;

    const error = (payload as { error?: { code?: string; message?: string; fields?: Record<string, string> | null } })?.error;
    if (error?.code) {
      throw new ApiError(response.status, error.code, error.message ?? 'Something went wrong.', error.fields ?? {});
    }
    throw new ApiError(response.status, 'http_error', `The server responded with ${response.status}.`);
  }

  return {
    getSettings: () => request<Settings>('GET', '/settings'),
    updateSettings: (settings: Settings) => request<Settings>('PUT', '/settings', settings),
    getMeals: (date?: string) =>
      request<MealsResponse>('GET', date ? `/meals?date=${encodeURIComponent(date)}` : '/meals'),
    getMeta: () => request<MetaResponse>('GET', '/meta'),
    getRecommendations: (req: RecommendationRequest = {}) =>
      request<RecommendationsResponse>('POST', '/recommendations', req),
  };
}
