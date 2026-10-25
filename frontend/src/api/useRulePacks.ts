import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import { queryKeys } from './queryKeys';
import { components } from '../types/api';

export type RulePackItem = components['schemas']['RulePackItem'];

export interface RulePacksResponse {
  items: RulePackItem[];
  total: number;
}

export function useRulePacks() {
  return useQuery({
    queryKey: queryKeys.rulePacks.all,
    queryFn: async (): Promise<RulePacksResponse> => {
      const res = await api.get<RulePacksResponse>('/rule-packs');
      return res.data;
    },
    staleTime: 60 * 1000,
  });
}
