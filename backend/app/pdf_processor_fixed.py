"""
Fixed PDF Processor using Azure Document Intelligence
Works with azure-ai-documentintelligence package
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
import logging
import re

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

from .pdf_processor import (
    PDFReconciliationData,
    PDFHeaderData,
    PDFTable,
    ConfidenceScore,
    LowConfidenceArea
)

logger = logging.getLogger(__name__)


class FixedPDFProcessor:
    """
    PDF processor using Azure Document Intelligence
    Fixed for azure-ai-documentintelligence package
    """

    def __init__(self, endpoint: str, key: str, min_confidence: float = 0.75):
        self.endpoint = endpoint
        self.credential = AzureKeyCredential(key)
        self.client = DocumentIntelligenceClient(endpoint, self.credential)
        self.min_confidence = min_confidence
        logger.info(f"FixedPDFProcessor initialized with min_confidence={min_confidence}")

    async def process_pdf(self, pdf_path: str) -> PDFReconciliationData:
        """
        Process PDF with Azure Document Intelligence
        """
        logger.info(f"Processing PDF: {pdf_path}")

        # Read PDF
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        # Call Azure DI
        poller = self.client.begin_analyze_document(
            model_id="prebuilt-layout",
            analyze_request=pdf_bytes,
            content_type="application/octet-stream"
        )
        result = poller.result()

        logger.info(f"Azure DI complete. Pages: {len(result.pages)}, Tables: {len(result.tables) if result.tables else 0}")

        # Extract data
        header = self._extract_header(result)
        section1_table = self._extract_section1(result)
        section2_table = self._extract_section2(result)
        section3_table = None  # Optional for now

        # Calculate confidence
        confidences = []
        if section1_table:
            confidences.append(section1_table.confidence)
        if section2_table:
            confidences.append(section2_table.confidence)

        overall_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        meets_threshold = overall_confidence >= self.min_confidence

        data = PDFReconciliationData(
            filename=pdf_path.split('/')[-1],
            header=header,
            section1_table=section1_table,
            section2_table=section2_table,
            section3_table=section3_table,
            overall_confidence=overall_confidence,
            meets_confidence_threshold=meets_threshold,
            low_confidence_areas=[],
            total_pages=len(result.pages),
            pages_processed=[1, 2] if len(result.pages) >= 2 else [1]
        )

        logger.info(f"PDF processing complete. EMEI: {header.emei_code}, Confidence: {overall_confidence:.2f}")
        return data

    def _extract_header(self, result) -> PDFHeaderData:
        """Extract header from PDF content"""
        # Extract EMEI code using regex
        emei_code = None
        pattern = r'\b\d{6}\b'
        matches = re.findall(pattern, result.content)
        if matches:
            emei_code = matches[0]  # First 6-digit number is usually EMEI

        # Try to extract name (look for CEU EMEI or similar)
        emei_name = None
        name_pattern = r'CEU EMEI[^\n]*'
        name_match = re.search(name_pattern, result.content)
        if name_match:
            emei_name = name_match.group(0).strip()

        # Company name
        company_pattern = r'Comercial[^\n]+'
        company_match = re.search(company_pattern, result.content)
        company_name = company_match.group(0).strip() if company_match else None

        return PDFHeaderData(
            emei_code=emei_code or "UNKNOWN",
            emei_name=emei_name,
            company_name=company_name,
            confidence_scores=[
                ConfidenceScore(
                    field_name="emei_code",
                    confidence=0.95,  # Regex extraction is reliable
                    page_number=1
                )
            ]
        )

    def _extract_section1(self, result) -> Optional[PDFTable]:
        """
        Extract Section 1 (enrollment table)
        This is typically Table 2: 6 rows x 5 cols
        """
        if not result.tables:
            return None

        # Find enrollment table (around 6 rows, 5 cols, on page 1)
        for table in result.tables:
            page_num = table.bounding_regions[0]['pageNumber'] if table.bounding_regions else 1
            if page_num == 1 and table.row_count >= 4 and table.row_count <= 8 and table.column_count >= 4:
                return self._parse_table(table, page_num, "section1")

        return None

    def _extract_section2(self, result) -> Optional[PDFTable]:
        """
        Extract Section 2 (daily frequency table)
        This is typically Table 3 on page 1 OR Table 6 on page 2
        Large table with 30+ rows
        """
        if not result.tables:
            return None

        # Find large frequency table
        for table in result.tables:
            page_num = table.bounding_regions[0]['pageNumber'] if table.bounding_regions else 1
            if table.row_count >= 30:
                return self._parse_table(table, page_num, "section2")

        return None

    def _parse_table(self, table, page_number: int, section: str) -> PDFTable:
        """Parse Azure DI table into our format"""
        # Build 2D array
        cells = [[None for _ in range(table.column_count)] for _ in range(table.row_count)]

        total_confidence = 0
        cell_count = 0

        for cell in table.cells:
            row = cell.row_index
            col = cell.column_index
            row_span = getattr(cell, 'row_span', 1) or 1
            col_span = getattr(cell, 'column_span', 1) or 1

            # Fill cells (handle spans)
            for r in range(row, min(row + row_span, table.row_count)):
                for c in range(col, min(col + col_span, table.column_count)):
                    if r < len(cells) and c < len(cells[0]):
                        cells[r][c] = cell.content

            # Confidence (if available)
            if hasattr(cell, 'confidence') and cell.confidence:
                total_confidence += cell.confidence
                cell_count += 1

        avg_confidence = total_confidence / cell_count if cell_count > 0 else 0.85

        return PDFTable(
            page_number=page_number,
            row_count=table.row_count,
            column_count=table.column_count,
            cells=cells,
            confidence=avg_confidence,
            section=section
        )


# Export as PDFProcessor
PDFProcessor = FixedPDFProcessor
