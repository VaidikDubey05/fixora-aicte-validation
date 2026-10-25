import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import { queryKeys } from './queryKeys';
import { components } from '../types/api';

export type ApplicationSummary = components['schemas']['ApplicationSummary'];

export interface ApplicationListParams {
  status?: string;
  state?: string;
  category?: string;
  severity?: string;
  assignee?: string;
  q?: string;
  page?: number;
  page_size?: number;
}

export interface ApplicationListResponse {
  items: ApplicationSummary[];
  total: number;
  page: number;
  page_size: number;
}

export function useApplications(params?: ApplicationListParams) {
  return useQuery({
    queryKey: queryKeys.applications.list(params),
    queryFn: async (): Promise<ApplicationListResponse> => {
      const res = await api.get<ApplicationListResponse>('/applications', { params });
      return res.data;
    },
    staleTime: 30 * 1000,
  });
}
