import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import { queryKeys } from './queryKeys';
import { components } from '../types/api';

export type UserResponse = components['schemas']['UserResponse'];

export function useMe() {
  const token = typeof window !== 'undefined' ? localStorage.getItem('fixora_token') : null;

  return useQuery({
    queryKey: queryKeys.auth.me,
    queryFn: async (): Promise<UserResponse> => {
      const res = await api.get<UserResponse>('/auth/me');
      localStorage.setItem('fixora_user', JSON.stringify(res.data));
      return res.data;
    },
    enabled: !!token,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}
