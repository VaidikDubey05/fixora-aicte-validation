import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import { queryKeys } from './queryKeys';
import { components } from '../types/api';

export type ApplicationDetail = components['schemas']['ApplicationDetail'];

export function useApplication(id: string) {
  return useQuery({
    queryKey: queryKeys.applications.detail(id),
    queryFn: async (): Promise<ApplicationDetail> => {
      const res = await api.get<ApplicationDetail>(`/applications/${id}`);
      return res.data;
    },
    enabled: !!id,
    staleTime: 30 * 1000,
  });
}
