"""
Data models for bulk upload feature
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID


# ============================================================================
# REQUEST MODELS
# ============================================================================

class BulkUploadRequest(BaseModel):
    """Request for initiating bulk PDF upload"""
    # File will be sent as multipart/form-data
    pass


class ExcelUploadRequest(BaseModel):
    """Request for uploading Excel files"""
    bulk_upload_id: UUID


class ReconcileRequest(BaseModel):
    """Request to reconcile selected documents"""
    bulk_upload_id: UUID
    document_ids: List[str]  # List of EMEI IDs to reconcile


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class BulkDocumentResponse(BaseModel):
    """Individual document in the bulk upload"""
    id: UUID
    bulk_upload_id: UUID
    document_id: str  # EMEI ID

    # Extracted metadata
    tipo: Optional[str] = None
    lugar: Optional[str] = None
    codigo_codae: Optional[str] = None
    mes: Optional[str] = None
    ano: Optional[str] = None
    cep: Optional[str] = None
    diretoria: Optional[str] = None
    prestador: Optional[str] = None

    # PDF info
    page_count: int
    page_numbers: Optional[List[int]] = None

    # Excel matching
    excel_filename: Optional[str] = None
    excel_matched: bool = False

    # Reconciliation
    reconciliation_id: Optional[UUID] = None
    reconciliation_status: Optional[str] = None
    reconciliation_match_percentage: Optional[float] = None
    reconciliation_total_mismatches: Optional[int] = None

    # Status
    status: str
    error_message: Optional[str] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # For SQLAlchemy ORM compatibility


class BulkUploadResponse(BaseModel):
    """Response for bulk upload operation"""
    id: UUID
    original_filename: str
    upload_timestamp: datetime
    status: str

    # Statistics
    total_pages: Optional[int] = None
    total_documents: Optional[int] = None
    documents_with_2_pages: Optional[int] = None
    documents_with_excel: Optional[int] = None
    documents_reconciled: Optional[int] = None

    # Processing info
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    # Documents
    documents: List[BulkDocumentResponse] = []

    class Config:
        from_attributes = True


class BulkUploadStatusResponse(BaseModel):
    """Status response for checking upload progress"""
    id: UUID
    status: str
    total_pages: Optional[int] = None
    total_documents: Optional[int] = None
    progress_percentage: int = 0
    current_step: Optional[str] = None
    error_message: Optional[str] = None


class ExcelMatchingResponse(BaseModel):
    """Response after uploading Excel files"""
    bulk_upload_id: UUID
    total_excel_files: int
    matched_count: int
    missing_count: int
    matched_documents: List[str]  # List of document IDs
    missing_documents: List[str]  # List of document IDs without Excel


class ReconciliationProgressResponse(BaseModel):
    """Response for reconciliation progress"""
    bulk_upload_id: UUID
    total_selected: int
    completed: int
    failed: int
    in_progress: int
    progress_percentage: int


class DocumentReconciliationResult(BaseModel):
    """Detailed reconciliation result for a single document"""
    document_id: str
    reconciliation_id: UUID
    status: str
    match_percentage: float
    total_mismatches: int
    total_cells_compared: int

    # Mismatches summary
    mismatches: List[dict] = []

    # Links
    report_url: Optional[str] = None


# ============================================================================
# DATABASE MODELS (for SQLAlchemy)
# ============================================================================

class BulkUploadDB(BaseModel):
    """Database model for bulk_uploads table"""
    id: UUID
    original_filename: str
    upload_timestamp: datetime
    status: str

    total_pages: Optional[int] = None
    total_documents: Optional[int] = None
    documents_with_2_pages: Optional[int] = None
    documents_with_excel: Optional[int] = None
    documents_reconciled: Optional[int] = None

    blob_container: str = "bulk-uploads"
    blob_path: Optional[str] = None

    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    retention_until: Optional[datetime] = None
    user_id: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BulkDocumentDB(BaseModel):
    """Database model for bulk_documents table"""
    id: UUID
    bulk_upload_id: UUID
    document_id: str

    tipo: Optional[str] = None
    lugar: Optional[str] = None
    codigo_codae: Optional[str] = None
    mes: Optional[str] = None
    ano: Optional[str] = None
    cep: Optional[str] = None
    diretoria: Optional[str] = None
    prestador: Optional[str] = None

    page_count: int
    page_numbers: Optional[str] = None  # JSON array as string
    pdf_blob_path: Optional[str] = None

    excel_filename: Optional[str] = None
    excel_blob_path: Optional[str] = None
    excel_matched: bool = False
    excel_uploaded_at: Optional[datetime] = None

    reconciliation_id: Optional[UUID] = None
    reconciliation_status: Optional[str] = None
    reconciliation_match_percentage: Optional[float] = None
    reconciliation_total_mismatches: Optional[int] = None

    status: str = "extracted"
    error_message: Optional[str] = None
    extraction_confidence: Optional[float] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
