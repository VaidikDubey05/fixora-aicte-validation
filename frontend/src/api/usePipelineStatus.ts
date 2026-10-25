import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import { queryKeys } from './queryKeys';
import { components } from '../types/api';

export type PipelineStatus = components['schemas']['PipelineStatus'];

export function usePipelineStatus(applicationId: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.applications.status(applicationId),
    queryFn: async (): Promise<PipelineStatus> => {
      const res = await api.get<PipelineStatus>(`/applications/${applicationId}/status`);
      return res.data;
    },
    enabled: enabled && !!applicationId,
    // Refetch interval: 1500ms while running, otherwise stop polling
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.is_running) {
        return 1500;
      }
      return false;
    },
    staleTime: 1000,
  });
}
