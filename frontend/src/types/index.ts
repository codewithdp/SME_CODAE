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
  excel_value: string | number | null;
  pdf_value: string | number | null;
}

export interface UploadResponse {
  reconciliation_id: string;
  status: string;
  message: string;
}
