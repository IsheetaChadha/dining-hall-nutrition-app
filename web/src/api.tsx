import { createApiClient, type ApiClient } from '@dining/core';
import { createContext, useContext, type ReactNode } from 'react';

const ApiContext = createContext<ApiClient | null>(null);

/** The web app's API client: same-origin, using the browser's fetch. */
export const browserApi = createApiClient({ baseUrl: '', fetch: (url, init) => window.fetch(url, init) });

export function ApiProvider({ client, children }: { client: ApiClient; children: ReactNode }) {
  return <ApiContext.Provider value={client}>{children}</ApiContext.Provider>;
}

export function useApi(): ApiClient {
  const client = useContext(ApiContext);
  if (!client) throw new Error('useApi must be used inside <ApiProvider>');
  return client;
}
