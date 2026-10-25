import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import { queryKeys } from './queryKeys';
import { components } from '../types/api';

export type DocumentOcrResponse = components['schemas']['DocumentOcrResponse'];

export function useDocumentOcr(documentId: string) {
  return useQuery({
    queryKey: queryKeys.documents.ocr(documentId),
    queryFn: async (): Promise<DocumentOcrResponse> => {
      const res = await api.get<DocumentOcrResponse>(`/documents/${documentId}/ocr`);
      return res.data;
    },
    enabled: !!documentId,
    staleTime: 60 * 1000,
  });
}
