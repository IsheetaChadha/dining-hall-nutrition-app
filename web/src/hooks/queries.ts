import type { RecommendationRequest, Settings } from '@dining/core';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useApi } from '../api';

export function useSettings() {
  const api = useApi();
  return useQuery({ queryKey: ['settings'], queryFn: () => api.getSettings(), staleTime: Infinity });
}

export function useSaveSettings() {
  const api = useApi();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (settings: Settings) => api.updateSettings(settings),
    onSuccess: (saved) => {
      queryClient.setQueryData(['settings'], saved);
      void queryClient.invalidateQueries({ queryKey: ['recommendations'] });
    },
  });
}

export function useMeals(date?: string) {
  const api = useApi();
  return useQuery({ queryKey: ['meals', date ?? 'today'], queryFn: () => api.getMeals(date), staleTime: 60 * 60_000 });
}

export function useRecommendations(request: RecommendationRequest) {
  const api = useApi();
  return useQuery({
    queryKey: ['recommendations', request],
    queryFn: () => api.getRecommendations(request),
    staleTime: 5 * 60_000,
  });
}
