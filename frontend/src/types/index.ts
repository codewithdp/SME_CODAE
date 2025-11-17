export interface ReconciliationStatus {
  reconciliation_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress_percentage: number;
  current_step: string;
  result?: ReconciliationResult;
  error_message?: string;
  created_at: string;
  completed_at?: string;
}

export interface ReconciliationResult {
  total_cells_compared: number;
  matching_cells: number;
  mismatching_cells: number;
  match_percentage: number;
  mismatches: Mismatch[];
  excel_file: string;
  pdf_file: string;
  timestamp: string;
}

export interface Mismatch {
  section: string;
  field: string;
  day_or_period?: string;
  row_identifier?: string;
  excel_value: string | number | null;
  pdf_value: string | number | null;
  excel_cell_ref?: string | null;  // e.g., "L15", "E28", "AB32"
  pdf_image_base64?: string | null;  // Base64 encoded PDF cell image
  description?: string;
}

export interface UploadResponse {
  reconciliation_id: string;
  status: string;
  message: string;
}

// Bulk Upload Types
export interface BulkUploadResponse {
  id: string;
  original_filename: string;
  status: 'processing' | 'completed' | 'failed';
  upload_timestamp: string;
  total_pages?: number;
  total_documents?: number;
}

export interface BulkUploadStatus {
  id: string;
  status: 'processing' | 'completed' | 'failed';
  progress_percentage: number;
  current_step?: string;
  total_pages?: number;
  total_documents?: number;
  documents_with_2_pages?: number;
  error_message?: string;
}

export interface BulkDocument {
  id: string;
  document_id: string;
  tipo: string | null;
  lugar: string | null;
  codigo_codae: string | null;
  mes: string | null;
  ano: string | null;
  cep: string | null;
  diretoria: string | null;
  prestador: string | null;
  page_count: number;
  page_numbers: number[];
  excel_filename: string | null;
  excel_matched: boolean;
  reconciliation_id: string | null;
  reconciliation_status: string | null;
  reconciliation_match_percentage: number | null;
  reconciliation_total_mismatches: number | null;
  status: 'extracted' | 'ready' | 'reconciling' | 'completed' | 'failed';
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExcelMatchingResponse {
  upload_id: string;
  total_excel_files: number;
  matched_count: number;
  missing_count: number;
  matched_documents: string[];
  missing_documents: string[];
}
