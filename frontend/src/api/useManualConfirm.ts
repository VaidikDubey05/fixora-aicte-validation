import { useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';
import { queryKeys } from './queryKeys';

export interface ManualConfirmParams {
  verificationId: string;
  outcome?: string;
  notes?: string;
  reason?: string;
}

export function useManualConfirm() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ verificationId, outcome = 'VERIFIED', notes, reason }: ManualConfirmParams): Promise<any> => {
      const res = await api.post(`/verification/${verificationId}/manual-confirm`, {
        outcome,
        notes: notes || reason || 'Officer manual verification confirmed with source documentation.',
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.verification.queue });
    },
  });
}
