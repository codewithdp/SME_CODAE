"""
Mock PDF Processor for Testing
Returns dummy data without calling Azure
"""

from typing import List, Optional
from datetime import datetime
import logging

from .pdf_processor import (
    PDFReconciliationData,
    PDFHeaderData,
    PDFTable,
    ConfidenceScore,
    LowConfidenceArea
)

logger = logging.getLogger(__name__)


class MockPDFProcessor:
    """
    Mock PDF processor that returns test data
    Use this for testing without Azure Document Intelligence
    """

    def __init__(self, endpoint: str, key: str, min_confidence: float = 0.75):
        self.endpoint = endpoint
        self.key = key
        self.min_confidence = min_confidence
        logger.info("MockPDFProcessor initialized (no Azure calls will be made)")

    async def process_pdf(self, pdf_path: str) -> PDFReconciliationData:
        """
        Mock PDF processing - returns dummy data
        """
        logger.info(f"Mock processing PDF: {pdf_path}")

        # Create mock header
        header = PDFHeaderData(
            emei_code="19382",
            emei_name="CEU EMEI ALTO ALEGRE",
            company_name="Comercial Milano Brasil LTDA",
            confidence_scores=[
                ConfidenceScore(
                    field_name="emei_code",
                    confidence=0.95,
                    page_number=1
                )
            ]
        )

        # Create mock Section 1 table (enrollment)
        section1_cells = [
            ["PERÍODOS", "Nº ALUNOS", "DIETA A", "DIETA B"],
            ["1º PERÍODO MATUTINO", "294", "0", "12"],
            ["3º PERÍODO VESPERTINO", "296", "0", "6"],
            ["TOTAL", "590", "0", "18"]
        ]

        section1_table = PDFTable(
            page_number=1,
            row_count=4,
            column_count=4,
            cells=section1_cells,
            confidence=0.92,
            section="section1"
        )

        # Create mock Section 2 table (daily frequency)
        section2_cells = []
        section2_cells.append(["Dia", "Freq", "Lanche", "Refeição"])

        # Add some sample days
        for day in range(1, 6):
            section2_cells.append([
                str(day),
                str(156 + day),
                str(145 + day),
                str(156 + day)
            ])

        section2_table = PDFTable(
            page_number=2,
            row_count=len(section2_cells),
            column_count=4,
            cells=section2_cells,
            confidence=0.88,
            section="section2"
        )

        # Create mock Section 3 table (would be larger grid)
        section3_table = PDFTable(
            page_number=1,
            row_count=10,
            column_count=12,
            cells=[[""] * 12 for _ in range(10)],
            confidence=0.85,
            section="section3"
        )

        # Create reconciliation data
        data = PDFReconciliationData(
            filename=pdf_path.split('/')[-1],
            header=header,
            section1_table=section1_table,
            section2_table=section2_table,
            section3_table=section3_table,
            overall_confidence=0.89,
            meets_confidence_threshold=True,
            low_confidence_areas=[],
            total_pages=2,
            pages_processed=[1, 2]
        )

        logger.info(f"Mock PDF processing complete. EMEI: {header.emei_code}, Confidence: 0.89")

        return data


# For easy switching between mock and real
PDFProcessor = MockPDFProcessor
