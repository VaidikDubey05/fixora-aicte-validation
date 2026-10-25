import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import { queryKeys } from './queryKeys';
import { components } from '../types/api';

export type RulePackItem = components['schemas']['RulePackItem'];

export function useRulePack(id: string) {
  return useQuery({
    queryKey: queryKeys.rulePacks.detail(id),
    queryFn: async (): Promise<RulePackItem> => {
      const res = await api.get<RulePackItem>(`/rule-packs/${id}`);
      return res.data;
    },
    enabled: !!id,
    staleTime: 60 * 1000,
  });
}
