import { useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';
import { queryKeys } from './queryKeys';
import { components } from '../types/api';

export interface LoginParams {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in?: number;
  user: components['schemas']['UserResponse'];
}

export function useLogin() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (credentials: LoginParams): Promise<LoginResponse> => {
      const res = await api.post<LoginResponse>('/auth/login', credentials);
      return res.data;
    },
    onSuccess: (data) => {
      localStorage.setItem('fixora_token', data.access_token);
      localStorage.setItem('fixora_user', JSON.stringify(data.user));
      queryClient.setQueryData(queryKeys.auth.me, data.user);
      queryClient.invalidateQueries({ queryKey: queryKeys.auth.me });
    },
  });
}
