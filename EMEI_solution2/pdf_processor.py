"""
PDF Processor Module using Azure Document Intelligence
Extracts structured data from 2-page PDF documents
"""

from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import asyncio
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# DATA MODELS
# ============================================================================

class ConfidenceScore(BaseModel):
    """Confidence score for a specific field or area"""
    field_name: str
    confidence: float
    page_number: int
    location: Optional[str] = None


class LowConfidenceArea(BaseModel):
    """Areas with confidence below threshold"""
    description: str
    confidence: float
    page: int
    section: str  # "header", "section1", "section2", "section3"


class PDFHeaderData(BaseModel):
    """Header extracted from PDF"""
    emei_code: str
    emei_name: Optional[str] = None
    address: Optional[str] = None
    company_name: Optional[str] = None
    month: Optional[str] = None
    year: Optional[str] = None
    confidence_scores: List[ConfidenceScore] = Field(default_factory=list)


class PDFTable(BaseModel):
    """Represents a table extracted from PDF"""
    page_number: int
    row_count: int
    column_count: int
    cells: List[List[Any]]
    confidence: float
    section: str  # "section1", "section2", "section3"


class PDFReconciliationData(BaseModel):
    """Complete structured data extracted from PDF"""
    filename: str
    extracted_at: datetime = Field(default_factory=datetime.now)
    
    # Header information
    header: PDFHeaderData
    
    # Tables by section
    section1_table: Optional[PDFTable] = None
    section2_table: Optional[PDFTable] = None
    section3_table: Optional[PDFTable] = None
    
    # Quality metrics
    overall_confidence: float
    meets_confidence_threshold: bool
    low_confidence_areas: List[LowConfidenceArea] = Field(default_factory=list)
    
    # Page information
    total_pages: int
    pages_processed: List[int]


# ============================================================================
# PDF PROCESSOR CLASS
# ============================================================================

class PDFProcessor:
    """
    Processes PDF files using Azure Document Intelligence
    Handles multi-page structure and extracts tables
    """
    
    def __init__(
        self, 
        endpoint: str, 
        key: str,
        min_confidence: float = 0.75
    ):
        """
        Initialize PDF processor
        
        Args:
            endpoint: Azure Document Intelligence endpoint
            key: Azure Document Intelligence key
            min_confidence: Minimum confidence threshold (0-1)
        """
        self.endpoint = endpoint
        self.credential = AzureKeyCredential(key)
        self.client = DocumentAnalysisClient(endpoint, self.credential)
        self.min_confidence = min_confidence
        
        logger.info(f"PDFProcessor initialized with min_confidence={min_confidence}")
    
    async def process_pdf(self, pdf_path: str) -> PDFReconciliationData:
        """
        Main processing method
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            PDFReconciliationData with all extracted information
        """
        logger.info(f"Starting PDF processing: {pdf_path}")
        
        # Read PDF file
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        
        # Process with Azure Document Intelligence
        poller = self.client.begin_analyze_document(
            "prebuilt-document",
            pdf_bytes
        )
        result = poller.result()
        
        logger.info(f"Azure DI analysis complete. Pages: {len(result.pages)}")
        
        # Extract data from both pages
        page1_data = self._extract_page1(result)
        page2_data = self._extract_page2(result)
        
        # Stitch together
        reconciliation_data = self._stitch_pages(page1_data, page2_data, pdf_path)
        
        # Check confidence levels
        self._check_confidence_threshold(reconciliation_data)
        
        logger.info(f"PDF processing complete. Overall confidence: {reconciliation_data.overall_confidence:.2f}")
        
        return reconciliation_data
    
    def _extract_page1(self, result) -> Dict[str, Any]:
        """
        Extract data from page 1
        Contains: Header, Section 1 (enrollment), Section 3 (partial grid)
        """
        logger.info("Extracting data from page 1")
        
        page1 = result.pages[0]
        
        # Extract header information from key-value pairs
        header = self._extract_header_from_page(result, page_number=1)
        
        # Extract tables from page 1
        page1_tables = [table for table in result.tables if table.page_range[0] == 1]
        
        # Identify Section 1 table (enrollment - usually smaller table)
        section1_table = None
        section3_page1 = None
        
        for table in page1_tables:
            if table.row_count <= 6:  # Section 1 is small (4-5 rows + header + total)
                section1_table = self._parse_table(table, page_number=1, section="section1")
            else:  # Larger table is Section 3
                section3_page1 = self._parse_table(table, page_number=1, section="section3")
        
        return {
            "header": header,
            "section1_table": section1_table,
            "section3_page1": section3_page1
        }
    
    def _extract_page2(self, result) -> Dict[str, Any]:
        """
        Extract data from page 2
        Contains: Section 2 (frequency), Section 3 (continuation of grid)
        """
        if len(result.pages) < 2:
            logger.warning("PDF has only 1 page, expected 2")
            return {
                "section2_table": None,
                "section3_page2": None
            }
        
        logger.info("Extracting data from page 2")
        
        # Extract tables from page 2
        page2_tables = [
            table for table in result.tables 
            if any(page_num == 2 for page_num in range(table.page_range[0], table.page_range[1] + 1))
        ]
        
        # Identify Section 2 and Section 3 continuation
        section2_table = None
        section3_page2 = None
        
        for table in page2_tables:
            # Section 2 has specific structure with frequency data
            # Heuristic: smaller table with ~30 rows (days of month)
            if table.row_count >= 20 and table.row_count <= 35 and table.column_count <= 7:
                section2_table = self._parse_table(table, page_number=2, section="section2")
            elif table.row_count >= 10:  # Section 3 continuation
                section3_page2 = self._parse_table(table, page_number=2, section="section3")
        
        return {
            "section2_table": section2_table,
            "section3_page2": section3_page2
        }
    
    def _extract_header_from_page(self, result, page_number: int = 1) -> PDFHeaderData:
        """
        Extract header information from PDF
        Uses key-value pairs and direct text extraction
        """
        confidence_scores = []
        
        # Try to find EMEI code from key-value pairs
        emei_code = None
        for kv in result.key_value_pairs:
            if kv.key and "emei" in kv.key.content.lower():
                emei_code = kv.value.content if kv.value else None
                if kv.confidence:
                    confidence_scores.append(ConfidenceScore(
                        field_name="emei_code",
                        confidence=kv.confidence,
                        page_number=page_number
                    ))
                break
        
        # Fallback: Extract from text using pattern matching
        if not emei_code:
            emei_code = self._extract_emei_from_text(result.content)
        
        # Extract other header fields
        company_name = None
        for kv in result.key_value_pairs:
            if kv.key and "comercial" in kv.key.content.lower():
                company_name = kv.value.content if kv.value else None
                break
        
        return PDFHeaderData(
            emei_code=emei_code or "UNKNOWN",
            company_name=company_name,
            confidence_scores=confidence_scores
        )
    
    def _extract_emei_from_text(self, text: str) -> Optional[str]:
        """
        Extract EMEI code from raw text using pattern matching
        Example: "019382" from the PDF header
        """
        import re
        
        # Look for 6-digit EMEI code pattern
        pattern = r'\b\d{6}\b'
        matches = re.findall(pattern, text)
        
        if matches:
            return matches[0]
        
        return None
    
    def _parse_table(self, table, page_number: int, section: str) -> PDFTable:
        """
        Parse Azure DI table into structured format
        
        Args:
            table: Azure DocumentTable object
            page_number: Page number where table is found
            section: Section identifier
        """
        # Build 2D array of cells
        cells = [[None for _ in range(table.column_count)] for _ in range(table.row_count)]
        
        total_confidence = 0
        cell_count = 0
        
        for cell in table.cells:
            row = cell.row_index
            col = cell.column_index
            
            # Handle merged cells
            row_span = cell.row_span or 1
            col_span = cell.column_span or 1
            
            # Fill the cell(s)
            for r in range(row, min(row + row_span, table.row_count)):
                for c in range(col, min(col + col_span, table.column_count)):
                    if r < len(cells) and c < len(cells[0]):
                        cells[r][c] = cell.content
            
            if cell.confidence:
                total_confidence += cell.confidence
                cell_count += 1
        
        avg_confidence = total_confidence / cell_count if cell_count > 0 else 0.0
        
        return PDFTable(
            page_number=page_number,
            row_count=table.row_count,
            column_count=table.column_count,
            cells=cells,
            confidence=avg_confidence,
            section=section
        )
    
    def _stitch_pages(
        self, 
        page1_data: Dict[str, Any], 
        page2_data: Dict[str, Any],
        pdf_path: str
    ) -> PDFReconciliationData:
        """
        Combine data from both pages into single reconciliation data object
        """
        # Merge Section 3 data from both pages
        section3_combined = None
        
        if page1_data.get("section3_page1") and page2_data.get("section3_page2"):
            # Combine the two parts of Section 3
            section3_combined = self._merge_section3_tables(
                page1_data["section3_page1"],
                page2_data["section3_page2"]
            )
        elif page1_data.get("section3_page1"):
            section3_combined = page1_data["section3_page1"]
        
        # Calculate overall confidence
        confidences = []
        for table_key in ["section1_table", "section3_page1"]:
            if page1_data.get(table_key):
                confidences.append(page1_data[table_key].confidence)
        for table_key in ["section2_table", "section3_page2"]:
            if page2_data.get(table_key):
                confidences.append(page2_data[table_key].confidence)
        
        overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return PDFReconciliationData(
            filename=pdf_path.split('/')[-1],
            header=page1_data["header"],
            section1_table=page1_data.get("section1_table"),
            section2_table=page2_data.get("section2_table"),
            section3_table=section3_combined,
            overall_confidence=overall_confidence,
            meets_confidence_threshold=overall_confidence >= self.min_confidence,
            total_pages=2,
            pages_processed=[1, 2]
        )
    
    def _merge_section3_tables(self, page1_table: PDFTable, page2_table: PDFTable) -> PDFTable:
        """
        Merge Section 3 tables from page 1 and page 2
        Page 2 continues where page 1 left off
        """
        # Combine rows from both tables
        merged_cells = page1_table.cells + page2_table.cells
        
        # Average confidence
        avg_confidence = (page1_table.confidence + page2_table.confidence) / 2
        
        return PDFTable(
            page_number=1,  # Spans both pages
            row_count=len(merged_cells),
            column_count=page1_table.column_count,
            cells=merged_cells,
            confidence=avg_confidence,
            section="section3"
        )
    
    def _check_confidence_threshold(self, data: PDFReconciliationData) -> None:
        """
        Check if confidence scores meet minimum threshold
        Populate low_confidence_areas if below threshold
        """
        low_conf_areas = []
        
        # Check Section 1
        if data.section1_table and data.section1_table.confidence < self.min_confidence:
            low_conf_areas.append(LowConfidenceArea(
                description="Section 1 (Student Enrollment)",
                confidence=data.section1_table.confidence,
                page=1,
                section="section1"
            ))
        
        # Check Section 2
        if data.section2_table and data.section2_table.confidence < self.min_confidence:
            low_conf_areas.append(LowConfidenceArea(
                description="Section 2 (Frequency Data)",
                confidence=data.section2_table.confidence,
                page=2,
                section="section2"
            ))
        
        # Check Section 3
        if data.section3_table and data.section3_table.confidence < self.min_confidence:
            low_conf_areas.append(LowConfidenceArea(
                description="Section 3 (Daily Attendance Grid)",
                confidence=data.section3_table.confidence,
                page=1,  # Spans both pages
                section="section3"
            ))
        
        data.low_confidence_areas = low_conf_areas
        
        if low_conf_areas:
            logger.warning(f"Found {len(low_conf_areas)} low confidence areas")
            for area in low_conf_areas:
                logger.warning(f"  - {area.description}: {area.confidence:.2f}")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def extract_cell_value(table: PDFTable, row: int, col: int) -> Optional[Any]:
    """
    Extract cell value from parsed table
    
    Args:
        table: PDFTable object
        row: Row index (0-based)
        col: Column index (0-based)
    
    Returns:
        Cell value or None if out of bounds
    """
    if 0 <= row < len(table.cells) and 0 <= col < len(table.cells[0]):
        return table.cells[row][col]
    return None


def table_to_dict(table: PDFTable, has_header: bool = True) -> List[Dict[str, Any]]:
    """
    Convert table to list of dictionaries
    
    Args:
        table: PDFTable object
        has_header: Whether first row is header
    
    Returns:
        List of row dictionaries
    """
    if not table or not table.cells:
        return []
    
    if has_header and len(table.cells) > 1:
        headers = table.cells[0]
        data_rows = table.cells[1:]
        
        result = []
        for row in data_rows:
            row_dict = {}
            for i, header in enumerate(headers):
                if i < len(row):
                    row_dict[header or f"col_{i}"] = row[i]
            result.append(row_dict)
        return result
    else:
        # No header, use column indices
        return [
            {f"col_{i}": cell for i, cell in enumerate(row)}
            for row in table.cells
        ]


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

async def main():
    """Example usage"""
    import os
    
    # Get credentials from environment
    endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
    
    if not endpoint or not key:
        print("Please set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and KEY")
        return
    
    processor = PDFProcessor(endpoint, key, min_confidence=0.75)
    
    try:
        # Process PDF
        data = await processor.process_pdf("/path/to/EMEI_test1.pdf")
        
        print(f"Processed: {data.filename}")
        print(f"EMEI Code: {data.header.emei_code}")
        print(f"Overall Confidence: {data.overall_confidence:.2f}")
        print(f"Meets Threshold: {data.meets_confidence_threshold}")
        
        if data.low_confidence_areas:
            print("\nLow confidence areas:")
            for area in data.low_confidence_areas:
                print(f"  - {area.description}: {area.confidence:.2f}")
        
        if data.section1_table:
            print(f"\nSection 1: {data.section1_table.row_count} rows, {data.section1_table.column_count} cols")
        
        if data.section3_table:
            print(f"Section 3: {data.section3_table.row_count} rows (combined from both pages)")
            
    except Exception as e:
        print(f"Error processing PDF: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
