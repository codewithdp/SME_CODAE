import axios from 'axios';
import { ReconciliationStatus, UploadResponse } from '../types';

const API_BASE_URL = '/api/v1';

export const reconciliationApi = {
  /**
   * Upload Excel and PDF files for reconciliation
   */
  uploadFiles: async (excelFile: File, pdfFile: File): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('excel_file', excelFile);
    formData.append('pdf_file', pdfFile);

    const response = await axios.post<UploadResponse>(
      `${API_BASE_URL}/reconciliation/upload`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    return response.data;
  },

  /**
   * Get reconciliation status by ID
   */
  getStatus: async (reconciliationId: string): Promise<ReconciliationStatus> => {
    const response = await axios.get<ReconciliationStatus>(
      `${API_BASE_URL}/reconciliation/${reconciliationId}/status`
    );

    return response.data;
  },

  /**
   * Download reconciliation report
   */
  downloadReport: async (reconciliationId: string): Promise<Blob> => {
    const response = await axios.get(
      `${API_BASE_URL}/reconciliation/${reconciliationId}/report`,
      {
        responseType: 'blob',
      }
    );

    return response.data;
  },

  /**
   * Poll status until completion or failure
   */
  pollStatus: async (
    reconciliationId: string,
    onProgress: (status: ReconciliationStatus) => void,
    intervalMs: number = 2000
  ): Promise<ReconciliationStatus> => {
    return new Promise((resolve, reject) => {
      const checkStatus = async () => {
        try {
          const status = await reconciliationApi.getStatus(reconciliationId);
          onProgress(status);

          if (status.status === 'completed' || status.status === 'failed') {
            if (status.status === 'completed') {
              resolve(status);
            } else {
              reject(new Error(status.error_message || 'Reconciliação falhou'));
            }
            return true; // Stop polling
          }
          return false; // Continue polling
        } catch (error) {
          reject(error);
          return true; // Stop polling on error
        }
      };

      // Check immediately first
      checkStatus().then((shouldStop) => {
        if (shouldStop) return;

        // Then poll every intervalMs
        const interval = setInterval(async () => {
          const shouldStop = await checkStatus();
          if (shouldStop) {
            clearInterval(interval);
          }
        }, intervalMs);
      });
    });
  },
};
