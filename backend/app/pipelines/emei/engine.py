"""
Complete Positional Reconciliation Engine
Combines Section 1, 2, and 3 table-based reconciliation
"""
import os
import logging
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient

from ..shared.positional_engine import PositionalReconciliationEngine
from .mappings import (
    SECTION1_EXCEL_TO_PDF_MAPPING,
    SECTION2_EXCEL_TO_PDF_MAPPING,
    SECTION3_EXCEL_TO_PDF_MAPPING,
    SECTION1_COLUMN_NAMES,
    SECTION2_COLUMN_NAMES,
    SECTION3_COLUMN_NAMES
)

load_dotenv()

logger = logging.getLogger(__name__)


class CompletePositionalReconciliationEngine:
    """Complete reconciliation engine using positional table-based approach for all sections"""

    def __init__(self):
        self.positional_engine = PositionalReconciliationEngine()
        self.azure_di_endpoint = os.getenv('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT')
        self.azure_di_key = os.getenv('AZURE_DOCUMENT_INTELLIGENCE_KEY')

        # Use same model configuration as positional engine
        self.model_id = self.positional_engine.model_id
        logger.info(f"CompletePositionalReconciliationEngine initialized with model: {self.model_id}")

    def _detect_section_tables_from_result(self, result) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        """
        Detect which table index corresponds to Section 1, 2, and 3 from an existing Azure DI result

        Args:
            result: Azure Document Intelligence analysis result

        Returns:
            Tuple of (section1_index, section2_index, section3_index)
        """
        logger.info(f"Detecting section tables from cached PDF analysis result")

        section1_idx = None
        section2_idx = None
        section3_idx = None

        for idx, table in enumerate(result.tables):
            # Get first few rows to check content
            first_row_content = ""
            all_content = ""

            for cell in table.cells:
                if cell.row_index == 0:
                    first_row_content += (cell.content or "").upper() + " "
                all_content += (cell.content or "").upper() + " "

            # Section 1: Has "PERÍODOS" or "PERIODO" in first row, 5-6 columns
            if ("PERÍODO" in first_row_content or "PERIODO" in first_row_content) and \
               table.column_count >= 4 and table.column_count <= 6 and \
               table.row_count >= 5 and table.row_count <= 10:
                section1_idx = idx
                logger.info(f"Section 1 detected at table index {idx} ({table.row_count}×{table.column_count})")

            # Section 2: Very wide table (30+ columns), has "FREQUENCIA" or "Dias"
            elif table.column_count >= 30 and \
                 ("FREQUENCIA" in all_content or "FREQUÊNCIA" in all_content or "DIAS" in first_row_content):
                section2_idx = idx
                logger.info(f"Section 2 detected at table index {idx} ({table.row_count}×{table.column_count})")

            # Section 3: Has "DIETA ESPECIAL", 7-15 columns, 30-40 rows
            elif ("DIETA ESPECIAL" in all_content or "DIETA\nESPECIAL" in all_content) and \
                 table.column_count >= 7 and table.column_count <= 15 and \
                 table.row_count >= 25:
                section3_idx = idx
                logger.info(f"Section 3 detected at table index {idx} ({table.row_count}×{table.column_count})")

        logger.info(f"Detection complete: Section1={section1_idx}, Section2={section2_idx}, Section3={section3_idx}")
        return section1_idx, section2_idx, section3_idx

    def reconcile_all_sections(
        self,
        pdf_path: str,
        excel_path: str,
        section_configs: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Reconcile all sections (1, 2, 3) between PDF and Excel using positional mapping

        Args:
            pdf_path: Path to PDF file
            excel_path: Path to Excel file
            section_configs: Optional config (ignored, using fixed configs)

        Returns:
            Dictionary with overall reconciliation results matching CustomModelReconciliationEngine format
        """
        logger.info(f"Starting complete positional reconciliation for {pdf_path} and {excel_path}")

        overall_results = {
            "pdf_file": pdf_path,
            "excel_file": excel_path,
            "sections": {},
            "overall_cells_compared": 0,
            "overall_matches": 0,
            "overall_mismatches": 0,
            "overall_match_percentage": 0.0
        }

        # OPTIMIZATION: Analyze PDF once and cache the result to avoid 4 separate API calls
        logger.info(f"Analyzing PDF with Azure Document Intelligence (this may take 30-90 seconds)...")
        client = DocumentIntelligenceClient(
            self.azure_di_endpoint,
            credential=AzureKeyCredential(self.azure_di_key)
        )

        with open(pdf_path, "rb") as f:
            poller = client.begin_analyze_document(
                self.model_id,
                analyze_request=f,
                content_type="application/pdf",
                features=[]  # Disable image extraction for faster processing
            )
            pdf_analysis_result = poller.result()

        logger.info(f"PDF analysis complete, found {len(pdf_analysis_result.tables)} tables")

        # Detect which table index corresponds to which section using the cached result
        section1_idx, section2_idx, section3_idx = self._detect_section_tables_from_result(pdf_analysis_result)

        # Section 1 configuration
        if section1_idx is not None:
            try:
                logger.info(f"Reconciling Section 1 (Table {section1_idx})...")
                section1_results = self.positional_engine.reconcile_section(
                    pdf_path=pdf_path,
                    excel_path=excel_path,
                    table_index=section1_idx,
                    excel_start_row=15,  # INTEGRAL row
                    column_mapping=SECTION1_EXCEL_TO_PDF_MAPPING,
                    column_names=SECTION1_COLUMN_NAMES,
                    pdf_data_start_row=1,  # Data starts at row 1
                    excel_row_skip=1,  # Skip empty row 19 before Total
                    pdf_table=pdf_analysis_result.tables[section1_idx]  # Use cached table
                )
                overall_results["sections"]["Section1"] = section1_results
                overall_results["overall_cells_compared"] += section1_results["cells_compared"]
                overall_results["overall_matches"] += section1_results["matches"]
                overall_results["overall_mismatches"] += section1_results["mismatches"]
                logger.info(f"Section 1: {section1_results['match_percentage']}% match rate")
            except Exception as e:
                logger.error(f"Error reconciling Section 1: {e}", exc_info=True)
                overall_results["sections"]["Section1"] = {
                    "error": str(e),
                    "cells_compared": 0,
                    "matches": 0,
                    "mismatches": 0,
                    "match_percentage": 0.0
                }
        else:
            logger.warning("Section 1 table not detected, skipping")
            overall_results["sections"]["Section1"] = {
                "error": "Section 1 table not detected",
                "cells_compared": 0,
                "matches": 0,
                "mismatches": 0,
                "match_percentage": 0.0
            }

        # Section 2 configuration
        if section2_idx is not None:
            try:
                logger.info(f"Reconciling Section 2 (Table {section2_idx})...")
                section2_results = self.positional_engine.reconcile_section(
                    pdf_path=pdf_path,
                    excel_path=excel_path,
                    table_index=section2_idx,
                    excel_start_row=28,  # Day 1 row
                    column_mapping=SECTION2_EXCEL_TO_PDF_MAPPING,
                    column_names=SECTION2_COLUMN_NAMES,
                    pdf_data_start_row=2,  # Data starts at row 2
                    pdf_table=pdf_analysis_result.tables[section2_idx]  # Use cached table
                )
                overall_results["sections"]["Section2"] = section2_results
                overall_results["overall_cells_compared"] += section2_results["cells_compared"]
                overall_results["overall_matches"] += section2_results["matches"]
                overall_results["overall_mismatches"] += section2_results["mismatches"]
                logger.info(f"Section 2: {section2_results['match_percentage']}% match rate")
            except Exception as e:
                logger.error(f"Error reconciling Section 2: {e}", exc_info=True)
                overall_results["sections"]["Section2"] = {
                    "error": str(e),
                    "cells_compared": 0,
                    "matches": 0,
                    "mismatches": 0,
                    "match_percentage": 0.0
                }
        else:
            logger.warning("Section 2 table not detected, skipping")
            overall_results["sections"]["Section2"] = {
                "error": "Section 2 table not detected",
                "cells_compared": 0,
                "matches": 0,
                "mismatches": 0,
                "match_percentage": 0.0
            }

        # Section 3 configuration
        if section3_idx is not None:
            try:
                logger.info(f"Reconciling Section 3 (Table {section3_idx})...")
                section3_results = self.positional_engine.reconcile_section(
                    pdf_path=pdf_path,
                    excel_path=excel_path,
                    table_index=section3_idx,
                    excel_start_row=77,  # Day 1 row
                    column_mapping=SECTION3_EXCEL_TO_PDF_MAPPING,
                    column_names=SECTION3_COLUMN_NAMES,
                    pdf_data_start_row=3,  # Data starts at row 3
                    pdf_table=pdf_analysis_result.tables[section3_idx]  # Use cached table
                )
                overall_results["sections"]["Section3"] = section3_results
                overall_results["overall_cells_compared"] += section3_results["cells_compared"]
                overall_results["overall_matches"] += section3_results["matches"]
                overall_results["overall_mismatches"] += section3_results["mismatches"]
                logger.info(f"Section 3: {section3_results['match_percentage']}% match rate")
            except Exception as e:
                logger.error(f"Error reconciling Section 3: {e}", exc_info=True)
                overall_results["sections"]["Section3"] = {
                    "error": str(e),
                    "cells_compared": 0,
                    "matches": 0,
                    "mismatches": 0,
                    "match_percentage": 0.0
                }
        else:
            logger.warning("Section 3 table not detected, skipping")
            overall_results["sections"]["Section3"] = {
                "error": "Section 3 table not detected",
                "cells_compared": 0,
                "matches": 0,
                "mismatches": 0,
                "match_percentage": 0.0
            }

        # Calculate overall match percentage
        if overall_results["overall_cells_compared"] > 0:
            overall_results["overall_match_percentage"] = round(
                (overall_results["overall_matches"] / overall_results["overall_cells_compared"]) * 100, 2
            )

        logger.info(f"Complete reconciliation finished: {overall_results['overall_match_percentage']}% overall match rate")
        return overall_results
