import { useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';
import { queryKeys } from './queryKeys';
import { components } from '../types/api';

export type FindingItem = components['schemas']['FindingItem'];

export interface FindingActionPayload {
  findingId: string;
  applicationId?: string;
  action: string;
  reason: string;
}

export function useFindingAction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      findingId,
      action,
      reason,
    }: FindingActionPayload): Promise<FindingItem> => {
      const res = await api.post<FindingItem>(`/findings/${findingId}/actions`, {
        action,
        reason,
      });
      return res.data;
    },
    onSuccess: (data, variables) => {
      queryClient.setQueryData(queryKeys.findings.detail(data.finding_id), data);
      queryClient.invalidateQueries({ queryKey: queryKeys.findings.all });
      if (variables.applicationId) {
        queryClient.invalidateQueries({
          queryKey: queryKeys.applications.findings(variables.applicationId),
        });
        queryClient.invalidateQueries({
          queryKey: queryKeys.applications.detail(variables.applicationId),
        });
      }
    },
  });
}
