import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import { queryKeys } from './queryKeys';
import { components } from '../types/api';

export type FindingItem = components['schemas']['FindingItem'];

export interface FindingsResponse {
  items: FindingItem[];
  total: number;
}

export function useFindings(applicationId: string) {
  return useQuery({
    queryKey: queryKeys.applications.findings(applicationId),
    queryFn: async (): Promise<FindingsResponse> => {
      const res = await api.get<FindingsResponse>(`/applications/${applicationId}/findings`);
      return res.data;
    },
    enabled: !!applicationId,
    staleTime: 30 * 1000,
  });
}
