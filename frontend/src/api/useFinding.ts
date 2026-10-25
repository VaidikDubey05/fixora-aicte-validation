import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import { queryKeys } from './queryKeys';
import { components } from '../types/api';

export type FindingItem = components['schemas']['FindingItem'];

export function useFinding(findingId: string) {
  return useQuery({
    queryKey: queryKeys.findings.detail(findingId),
    queryFn: async (): Promise<FindingItem> => {
      const res = await api.get<FindingItem>(`/findings/${findingId}`);
      return res.data;
    },
    enabled: !!findingId,
    staleTime: 30 * 1000,
  });
}
