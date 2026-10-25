import { useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';
import { queryKeys } from './queryKeys';
import { components } from '../types/api';

export type ApplicationDetail = components['schemas']['ApplicationDetail'];

export function useSubmitApplication(applicationId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (): Promise<ApplicationDetail> => {
      const res = await api.post<ApplicationDetail>(`/applications/${applicationId}/submit`);
      return res.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.applications.all });
      queryClient.setQueryData(queryKeys.applications.detail(applicationId), data);
    },
  });
}
