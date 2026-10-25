import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import { queryKeys } from './queryKeys';

export interface VerifyChainResponse {
  valid: boolean;
  checked?: number;
  total_events?: number;
  first_broken_seq?: number | null;
  tampered_index?: number | null;
  genesis_hash?: string;
  latest_hash?: string;
}

export function useVerifyChain(enabled = false) {
  return useQuery({
    queryKey: queryKeys.audit.verifyChain,
    queryFn: async (): Promise<VerifyChainResponse> => {
      const res = await api.get<VerifyChainResponse>('/audit/verify-chain');
      return res.data;
    },
    enabled,
    staleTime: 60 * 1000,
  });
}
