import { useMutation } from '@tanstack/react-query';
import api from '../lib/api';

export function useReportDownload() {
  return useMutation({
    mutationFn: async ({
      applicationId,
      filename = `Report_${applicationId}.pdf`,
    }: {
      applicationId: string;
      filename?: string;
    }): Promise<void> => {
      const res = await api.get(`/applications/${applicationId}/report.pdf`, {
        responseType: 'blob',
      });
      const blob = new Blob([res.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    },
  });
}
