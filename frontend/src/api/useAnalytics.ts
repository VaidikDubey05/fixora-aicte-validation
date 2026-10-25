import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import { queryKeys } from './queryKeys';
import { components } from '../types/api';

export type AnalyticsOverview = components['schemas']['AnalyticsOverview'];

export function useAnalytics() {
  return useQuery({
    queryKey: queryKeys.analytics.overview,
    queryFn: async (): Promise<AnalyticsOverview> => {
      const res = await api.get<AnalyticsOverview>('/analytics/overview');
      return res.data;
    },
    staleTime: 60 * 1000,
  });
}
