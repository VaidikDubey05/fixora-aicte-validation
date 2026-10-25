import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import { queryKeys } from './queryKeys';
import { components } from '../types/api';

export type AuditEventItem = components['schemas']['AuditEventItem'];

export interface AuditListParams {
  event_type?: string;
  application_id?: string;
  actor_id?: string;
  page?: number;
  page_size?: number;
}

export interface AuditListResponse {
  items: AuditEventItem[];
  total: number;
}

export function useAudit(params?: AuditListParams) {
  return useQuery({
    queryKey: queryKeys.audit.list(params),
    queryFn: async (): Promise<AuditListResponse> => {
      const res = await api.get<AuditListResponse>('/audit', { params });
      return res.data;
    },
    staleTime: 30 * 1000,
  });
}
