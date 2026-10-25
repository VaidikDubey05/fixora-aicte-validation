import { useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';
import { queryKeys } from './queryKeys';

export function useAckAlert() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (alertId: string): Promise<any> => {
      const res = await api.post(`/alerts/${alertId}/ack`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.alerts.all });
    },
  });
}
