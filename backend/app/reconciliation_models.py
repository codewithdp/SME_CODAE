"""
Shared Reconciliation Data Models
Used across all reconciliation engines
"""

from typing import List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class CellMismatch(BaseModel):
    """Represents a single cell mismatch between Excel and PDF"""
    section: str
    field: str
    row_identifier: str  # e.g., "Day 1", "1º PERÍODO MATUTINO"
    excel_value: Any
    pdf_value: Any
    excel_cell_ref: Optional[str] = None  # e.g., "B5", "D12"
    column_name: Optional[str] = None  # e.g., "Frequência (INTEGRAL)", "Lanche 4h"
    pdf_image_base64: Optional[str] = None  # Base64 encoded image of the PDF cell
    description: str


class ReconciliationResult(BaseModel):
    """Final reconciliation result"""
    reconciliation_id: str
    timestamp: datetime = Field(default_factory=datetime.now)

    # ID matching
    emei_code_match: bool
    excel_emei: str
    pdf_emei: str
    emei_id_excel: str  # Alias
    id_match: bool  # Alias

    # PDF quality
    pdf_confidence_ok: bool
    pdf_overall_confidence: float

    # Comparison results
    total_mismatches: int
    total_cells_compared: int
    mismatches: List[CellMismatch]

    # Summary metrics
    excel_total_students: int
    pdf_total_students: Optional[int] = None
    excel_row_count: int
    pdf_row_count: Optional[int] = None
    row_count_match: bool

    # File names
    excel_filename: str
    pdf_filename: str

    overall_match_percentage: float
    status: str  # "match", "mismatch", "warning"
