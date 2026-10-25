import { useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';
import { queryKeys } from './queryKeys';

export interface ValidateResponse {
  task_id?: string;
  status: string;
}

export function useValidate(applicationId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (): Promise<ValidateResponse> => {
      const res = await api.post<ValidateResponse>(`/applications/${applicationId}/validate`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.applications.status(applicationId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.applications.detail(applicationId),
      });
    },
  });
}
