"""
Complete Positional Reconciliation Engine
Combines Section 1, 2, and 3 table-based reconciliation
"""
import os
import logging
from typing import Dict, List, Optional
from dotenv import load_dotenv

from .reconciliation_engine_positional import (
    PositionalReconciliationEngine,
    SECTION1_EXCEL_TO_PDF_MAPPING,
    SECTION2_EXCEL_TO_PDF_MAPPING,
    SECTION3_EXCEL_TO_PDF_MAPPING
)

load_dotenv()

logger = logging.getLogger(__name__)


class CompletePositionalReconciliationEngine:
    """Complete reconciliation engine using positional table-based approach for all sections"""

    def __init__(self):
        self.positional_engine = PositionalReconciliationEngine()
        logger.info("CompletePositionalReconciliationEngine initialized")

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

        # Section 1 configuration
        try:
            logger.info("Reconciling Section 1 (Table 0)...")
            section1_results = self.positional_engine.reconcile_section(
                pdf_path=pdf_path,
                excel_path=excel_path,
                table_index=0,  # Table 0
                excel_start_row=15,  # INTEGRAL row
                column_mapping=SECTION1_EXCEL_TO_PDF_MAPPING,
                pdf_data_start_row=1,  # Data starts at row 1
                excel_row_skip=1  # Skip empty row 19 before Total
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

        # Section 2 configuration
        try:
            logger.info("Reconciling Section 2 (Table 2)...")
            section2_results = self.positional_engine.reconcile_section(
                pdf_path=pdf_path,
                excel_path=excel_path,
                table_index=2,  # Table 2
                excel_start_row=28,  # Day 1 row
                column_mapping=SECTION2_EXCEL_TO_PDF_MAPPING,
                pdf_data_start_row=2  # Data starts at row 2
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

        # Section 3 configuration
        try:
            logger.info("Reconciling Section 3 (Table 4)...")
            section3_results = self.positional_engine.reconcile_section(
                pdf_path=pdf_path,
                excel_path=excel_path,
                table_index=4,  # Table 4
                excel_start_row=77,  # Day 1 row
                column_mapping=SECTION3_EXCEL_TO_PDF_MAPPING,
                pdf_data_start_row=3  # Data starts at row 3
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

        # Calculate overall match percentage
        if overall_results["overall_cells_compared"] > 0:
            overall_results["overall_match_percentage"] = round(
                (overall_results["overall_matches"] / overall_results["overall_cells_compared"]) * 100, 2
            )

        logger.info(f"Complete reconciliation finished: {overall_results['overall_match_percentage']}% overall match rate")
        return overall_results
