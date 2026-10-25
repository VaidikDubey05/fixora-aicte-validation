import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import { queryKeys } from './queryKeys';
import { components } from '../types/api';

export type VerificationQueueItem = components['schemas']['VerificationQueueItem'];

export interface VerificationQueueResponse {
  items: VerificationQueueItem[];
  total: number;
}

export function useVerificationQueue() {
  return useQuery({
    queryKey: queryKeys.verification.queue,
    queryFn: async (): Promise<VerificationQueueResponse> => {
      const res = await api.get<VerificationQueueResponse>('/verification/queue');
      return res.data;
    },
    staleTime: 30 * 1000,
  });
}
