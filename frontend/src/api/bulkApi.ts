import axios from 'axios';
import {
  BulkUploadResponse,
  BulkUploadStatus,
  BulkDocument,
  ExcelMatchingResponse,
} from '../types';

const API_BASE_URL = '/api/v1/bulk';

export const bulkApi = {
  /**
   * Upload combined PDF for bulk processing
   */
  uploadPdf: async (pdfFile: File): Promise<BulkUploadResponse> => {
    const formData = new FormData();
    formData.append('file', pdfFile);

    const response = await axios.post<BulkUploadResponse>(
      `${API_BASE_URL}/upload-pdf`,
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
   * Get bulk upload status by ID
   */
  getStatus: async (uploadId: string): Promise<BulkUploadStatus> => {
    const response = await axios.get<BulkUploadStatus>(
      `${API_BASE_URL}/${uploadId}/status`
    );

    return response.data;
  },

  /**
   * Get all documents for a bulk upload
   */
  getDocuments: async (uploadId: string): Promise<BulkDocument[]> => {
    const response = await axios.get<BulkDocument[]>(
      `${API_BASE_URL}/${uploadId}/documents`
    );

    return response.data;
  },

  /**
   * Upload Excel files for matching
   */
  uploadExcelFiles: async (
    uploadId: string,
    excelFiles: File[]
  ): Promise<ExcelMatchingResponse> => {
    const formData = new FormData();
    excelFiles.forEach((file) => {
      formData.append('files', file);
    });

    const response = await axios.post<ExcelMatchingResponse>(
      `${API_BASE_URL}/${uploadId}/upload-excel`,
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
   * Poll status until completion or failure
   */
  pollStatus: async (
    uploadId: string,
    onProgress: (status: BulkUploadStatus) => void,
    intervalMs: number = 3000
  ): Promise<BulkUploadStatus> => {
    return new Promise((resolve, reject) => {
      const checkStatus = async () => {
        try {
          const status = await bulkApi.getStatus(uploadId);
          onProgress(status);

          if (status.status === 'completed' || status.status === 'failed') {
            if (status.status === 'completed') {
              resolve(status);
            } else {
              reject(new Error(status.error_message || 'Processamento falhou'));
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

  /**
   * Start batch reconciliation for documents
   */
  startReconciliation: async (
    uploadId: string,
    documentIds?: string[]
  ): Promise<{ message: string; upload_id: string; document_count: number; document_ids: string[] }> => {
    const response = await axios.post(
      `${API_BASE_URL}/${uploadId}/reconcile`,
      {
        bulk_upload_id: uploadId,
        document_ids: documentIds || []
      }
    );

    return response.data;
  },

  /**
   * Get detailed reconciliation results for a document
   */
  getReconciliationDetails: async (
    uploadId: string,
    reconciliationId: string
  ): Promise<any> => {
    const response = await axios.get(
      `${API_BASE_URL}/${uploadId}/reconciliation/${reconciliationId}`
    );

    return response.data;
  },
};
