import { useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';
import { queryKeys } from './queryKeys';
import { components } from '../types/api';

export type RulePackItem = components['schemas']['RulePackItem'];

export interface RulePackSubmitParams {
  id: string;
  version?: string;
}

export function useRulePackSubmit() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: string | RulePackSubmitParams): Promise<any> => {
      const id = typeof params === 'string' ? params : params.id;
      const version = typeof params === 'string' ? 'v1.0' : params.version || 'v1.0';
      const res = await api.post(`/rule-packs/${id}/submit`, { version });
      return res.data;
    },
    onSuccess: (_, vars) => {
      const id = typeof vars === 'string' ? vars : vars.id;
      queryClient.invalidateQueries({ queryKey: queryKeys.rulePacks.detail(id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.rulePacks.all });
    },
  });
}
