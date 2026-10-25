import { useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';
import { queryKeys } from './queryKeys';

export interface VerifyDocumentResponse {
  document_id: string;
  status: string;
  simulated: boolean;
  source?: string;
}

export function useVerifyDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (documentId: string): Promise<VerifyDocumentResponse> => {
      const res = await api.post<VerifyDocumentResponse>(`/documents/${documentId}/verify`);
      return res.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.documents.detail(data.document_id),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.verification.queue,
      });
    },
  });
}
