import { useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';
import { queryKeys } from './queryKeys';
import { components } from '../types/api';

export interface CreateApplicationPayload {
  institution_id?: string;
  academic_year: string;
  application_type: string;
  category: string;
  metadata?: Record<string, any>;
}

export type ApplicationDetail = components['schemas']['ApplicationDetail'];

export function useCreateApplication() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: CreateApplicationPayload): Promise<ApplicationDetail> => {
      const res = await api.post<ApplicationDetail>('/applications', payload);
      return res.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.applications.all });
      queryClient.setQueryData(queryKeys.applications.detail(data.id), data);
    },
  });
}
