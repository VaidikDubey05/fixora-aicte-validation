import { useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';
import { queryKeys } from './queryKeys';
import { components } from '../types/api';

export type DocumentItem = components['schemas']['DocumentItem'];

export interface UploadDocumentParams {
  applicationId: string;
  file: File;
  category: string;
  documentType?: string;
  onProgress?: (percent: number) => void;
}

export function useUploadDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      applicationId,
      file,
      category,
      documentType,
      onProgress,
    }: UploadDocumentParams): Promise<DocumentItem> => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('category', category);
      if (documentType) {
        formData.append('document_type', documentType);
      }

      const res = await api.post<DocumentItem>(
        `/applications/${applicationId}/documents`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          onUploadProgress: (progressEvent) => {
            if (progressEvent.total) {
              const percent = Math.round(
                (progressEvent.loaded * 100) / progressEvent.total
              );
              onProgress?.(percent);
            }
          },
        }
      );
      return res.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.applications.detail(variables.applicationId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.applications.checklist(variables.applicationId),
      });
    },
  });
}
