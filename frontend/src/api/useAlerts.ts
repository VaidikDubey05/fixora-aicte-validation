import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import { queryKeys } from './queryKeys';
import { components } from '../types/api';

export type AlertItem = components['schemas']['AlertItem'];

export interface AlertsResponse {
  items: AlertItem[];
  total: number;
  unread_count?: number;
}

export function useAlerts() {
  return useQuery({
    queryKey: queryKeys.alerts.all,
    queryFn: async (): Promise<AlertsResponse> => {
      const res = await api.get<AlertsResponse>('/alerts');
      return res.data;
    },
    refetchInterval: 15000,
    staleTime: 10000,
  });
}
