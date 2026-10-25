import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import { queryKeys } from './queryKeys';
import { components } from '../types/api';

export type InspectionQueueItem = components['schemas']['InspectionQueueItem'];

export interface InspectionQueueResponse {
  items: InspectionQueueItem[];
  total: number;
}

export function useInspectionQueue() {
  return useQuery({
    queryKey: queryKeys.inspection.queue,
    queryFn: async (): Promise<InspectionQueueResponse> => {
      const res = await api.get<InspectionQueueResponse>('/inspection/queue');
      return res.data;
    },
    staleTime: 30 * 1000,
  });
}
