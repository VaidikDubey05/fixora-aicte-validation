import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import { queryKeys } from './queryKeys';
import { components } from '../types/api';

export type ChecklistItem = components['schemas']['ChecklistItem'];

export interface ChecklistResponse {
  application_id: string;
  checklist: ChecklistItem[];
  overall_status?: string;
}

export function useChecklist(applicationId: string) {
  return useQuery({
    queryKey: queryKeys.applications.checklist(applicationId),
    queryFn: async (): Promise<ChecklistResponse> => {
      const res = await api.get<ChecklistResponse>(`/applications/${applicationId}/checklist`);
      return res.data;
    },
    enabled: !!applicationId,
    staleTime: 30 * 1000,
  });
}
