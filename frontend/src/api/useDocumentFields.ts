import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import { queryKeys } from './queryKeys';

export interface DocumentFieldsResponse {
  document_id: string;
  fields: Record<string, any>[];
}

export function useDocumentFields(documentId: string) {
  return useQuery({
    queryKey: queryKeys.documents.fields(documentId),
    queryFn: async (): Promise<DocumentFieldsResponse> => {
      const res = await api.get<DocumentFieldsResponse>(`/documents/${documentId}/fields`);
      return res.data;
    },
    enabled: !!documentId,
    staleTime: 60 * 1000,
  });
}
