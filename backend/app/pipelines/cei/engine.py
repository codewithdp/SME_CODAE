"""
CEI Pipeline - Reconciliation Engine
Handles CEI-specific reconciliation logic
"""
import os
import logging
from typing import Dict, List, Optional, Tuple, Any
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient

from ..shared.positional_engine import PositionalReconciliationEngine
from .mappings import (
    TABLE2_PAGE1_EXCEL_TO_PDF_MAPPING,
    TABLE3_PAGE1_EXCEL_TO_PDF_MAPPING,
    TABLE1_PAGE2_EXCEL_TO_PDF_MAPPING,
    TABLE2_PAGE2_CELLS,
    TABLE2_PAGE1_COLUMN_NAMES,
    TABLE3_PAGE1_COLUMN_NAMES,
    TABLE1_PAGE2_COLUMN_NAMES,
    EXCEL_RANGES,
)

load_dotenv()

logger = logging.getLogger(__name__)


def col_letter_to_idx(col: str) -> int:
    """Convert Excel column letter to 0-indexed column number"""
    result = 0
    for c in col.upper():
        result = result * 26 + (ord(c) - ord('A') + 1)
    return result - 1


class CEIReconciliationEngine:
    """CEI reconciliation engine using prebuilt-layout model"""

    def __init__(self):
        self.positional_engine = PositionalReconciliationEngine()
        self.azure_di_endpoint = os.getenv('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT')
        self.azure_di_key = os.getenv('AZURE_DOCUMENT_INTELLIGENCE_KEY')
        self.model_id = "prebuilt-layout"  # CEI uses prebuilt-layout

        logger.info(f"CEIReconciliationEngine initialized with model: {self.model_id}")

    def _detect_cei_tables(self, result) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        """
        Detect CEI tables by their dimensions

        Table dimensions (rows x columns):
        - Page 1, Table 2: 11 x 7
        - Page 1, Table 3: 35 x 18
        - Page 2, Table 1: 37 x 32

        Returns:
            Tuple of (table2_page1_idx, table3_page1_idx, table1_page2_idx)
        """
        logger.info("Detecting CEI tables by dimensions...")

        table2_page1_idx = None
        table3_page1_idx = None
        table1_page2_idx = None

        for idx, table in enumerate(result.tables):
            page_num = table.bounding_regions[0].page_number if table.bounding_regions else 0
            rows = table.row_count
            cols = table.column_count

            logger.debug(f"Table {idx}: Page {page_num}, {rows}x{cols}")

            # Page 1, Table 2: 11 rows x 7 columns
            if page_num == 1 and rows == 11 and cols == 7:
                table2_page1_idx = idx
                logger.info(f"Found Table 2 (Page 1) at index {idx}: {rows}x{cols}")

            # Page 1, Table 3: 35 rows x 18 columns
            elif page_num == 1 and rows == 35 and cols == 18:
                table3_page1_idx = idx
                logger.info(f"Found Table 3 (Page 1) at index {idx}: {rows}x{cols}")

            # Page 2, Table 1: ~37 rows x 32 columns (allow 35-39 rows for flexibility)
            elif page_num == 2 and 35 <= rows <= 39 and cols == 32:
                table1_page2_idx = idx
                logger.info(f"Found Table 1 (Page 2) at index {idx}: {rows}x{cols}")

        logger.info(
            f"Detection complete: Table2_P1={table2_page1_idx}, "
            f"Table3_P1={table3_page1_idx}, Table1_P2={table1_page2_idx}"
        )

        return table2_page1_idx, table3_page1_idx, table1_page2_idx

    def _convert_relative_to_absolute_mapping(
        self,
        relative_mapping: Dict[int, int],
        start_col_letter: str
    ) -> Dict[int, int]:
        """
        Convert relative column mapping to absolute Excel column indices

        Args:
            relative_mapping: Dict of {relative_col: pdf_col}
            start_col_letter: Starting column letter (e.g., 'M', 'Y')

        Returns:
            Dict of {absolute_excel_col: pdf_col}
        """
        start_col_idx = col_letter_to_idx(start_col_letter)
        return {
            start_col_idx + rel_col: pdf_col
            for rel_col, pdf_col in relative_mapping.items()
        }

    def _convert_relative_to_absolute_names(
        self,
        relative_names: Dict[int, str],
        start_col_letter: str
    ) -> Dict[int, str]:
        """Convert relative column names to absolute Excel column indices"""
        start_col_idx = col_letter_to_idx(start_col_letter)
        return {
            start_col_idx + rel_col: name
            for rel_col, name in relative_names.items()
        }

    def reconcile_all_sections(
        self,
        pdf_path: str,
        excel_path: str,
        section_configs: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Reconcile all CEI sections between PDF and Excel

        Args:
            pdf_path: Path to PDF file
            excel_path: Path to Excel file
            section_configs: Optional config (ignored, using fixed configs)

        Returns:
            Dictionary with overall reconciliation results
        """
        logger.info(f"Starting CEI reconciliation for {pdf_path} and {excel_path}")

        overall_results = {
            "pdf_file": pdf_path,
            "excel_file": excel_path,
            "sections": {},
            "overall_cells_compared": 0,
            "overall_matches": 0,
            "overall_mismatches": 0,
            "overall_match_percentage": 0.0
        }

        # Analyze PDF with prebuilt-layout model
        logger.info("Analyzing PDF with Azure Document Intelligence (prebuilt-layout)...")
        client = DocumentIntelligenceClient(
            self.azure_di_endpoint,
            credential=AzureKeyCredential(self.azure_di_key)
        )

        with open(pdf_path, "rb") as f:
            poller = client.begin_analyze_document(
                self.model_id,
                analyze_request=f,
                content_type="application/pdf",
                features=[]
            )
            pdf_analysis_result = poller.result()

        logger.info(f"PDF analysis complete, found {len(pdf_analysis_result.tables)} tables")

        # Detect tables by dimensions
        table2_p1_idx, table3_p1_idx, table1_p2_idx = self._detect_cei_tables(pdf_analysis_result)

        # =================================================================
        # Reconcile Table 2 (Page 1) - Section 1A: Enrolled students
        # Excel range: Y16:DG24
        # =================================================================
        if table2_p1_idx is not None:
            logger.info("Reconciling Table 2 (Page 1) - Section 1A...")

            # Convert relative mappings to absolute
            abs_mapping = self._convert_relative_to_absolute_mapping(
                TABLE2_PAGE1_EXCEL_TO_PDF_MAPPING, "Y"
            )
            abs_names = self._convert_relative_to_absolute_names(
                TABLE2_PAGE1_COLUMN_NAMES, "Y"
            )

            section1_result = self.positional_engine.reconcile_section(
                pdf_path=pdf_path,
                excel_path=excel_path,
                table_index=table2_p1_idx,
                excel_start_row=16,  # Row 16 = "0 a 1 mês" (empty)
                column_mapping=abs_mapping,
                column_names=abs_names,
                pdf_data_start_row=2,  # Skip header rows (0, 1)
                excel_row_skip=0,  # No skip needed - Total at row 24
                pdf_table=pdf_analysis_result.tables[table2_p1_idx],
                sheet_name="CEI"
            )

            overall_results["sections"]["section1_table2_p1"] = section1_result
            overall_results["overall_cells_compared"] += section1_result.get("cells_compared", 0)
            overall_results["overall_matches"] += section1_result.get("matches", 0)
            overall_results["overall_mismatches"] += section1_result.get("mismatches", 0)
        else:
            logger.warning("Table 2 (Page 1) not found - Section 1A skipped")

        # =================================================================
        # Reconcile Table 3 (Page 1) - Section 2: Daily attendance
        # Excel range: M31:CN62
        # =================================================================
        if table3_p1_idx is not None:
            logger.info("Reconciling Table 3 (Page 1) - Section 2...")

            # Convert relative mappings to absolute
            abs_mapping = self._convert_relative_to_absolute_mapping(
                TABLE3_PAGE1_EXCEL_TO_PDF_MAPPING, "M"
            )
            abs_names = self._convert_relative_to_absolute_names(
                TABLE3_PAGE1_COLUMN_NAMES, "M"
            )

            section2_result = self.positional_engine.reconcile_section(
                pdf_path=pdf_path,
                excel_path=excel_path,
                table_index=table3_p1_idx,
                excel_start_row=31,  # M31 starts at row 31
                column_mapping=abs_mapping,
                column_names=abs_names,
                pdf_data_start_row=2,  # Day-based table, auto-detect day 1
                excel_row_skip=0,
                pdf_table=pdf_analysis_result.tables[table3_p1_idx],
                sheet_name="CEI"
            )

            overall_results["sections"]["section2_table3_p1"] = section2_result
            overall_results["overall_cells_compared"] += section2_result.get("cells_compared", 0)
            overall_results["overall_matches"] += section2_result.get("matches", 0)
            overall_results["overall_mismatches"] += section2_result.get("mismatches", 0)
        else:
            logger.warning("Table 3 (Page 1) not found - Section 2 skipped")

        # =================================================================
        # Reconcile Table 1 (Page 2) - Section 3: Special diet attendance
        # Excel range: M71:DB102
        # =================================================================
        if table1_p2_idx is not None:
            logger.info("Reconciling Table 1 (Page 2) - Section 3...")

            # Convert relative mappings to absolute
            abs_mapping = self._convert_relative_to_absolute_mapping(
                TABLE1_PAGE2_EXCEL_TO_PDF_MAPPING, "M"
            )
            abs_names = self._convert_relative_to_absolute_names(
                TABLE1_PAGE2_COLUMN_NAMES, "M"
            )

            section3_result = self.positional_engine.reconcile_section(
                pdf_path=pdf_path,
                excel_path=excel_path,
                table_index=table1_p2_idx,
                excel_start_row=71,  # M71 starts at row 71
                column_mapping=abs_mapping,
                column_names=abs_names,
                pdf_data_start_row=2,  # Day-based table
                excel_row_skip=0,
                pdf_table=pdf_analysis_result.tables[table1_p2_idx],
                sheet_name="CEI"
            )

            overall_results["sections"]["section3_table1_p2"] = section3_result
            overall_results["overall_cells_compared"] += section3_result.get("cells_compared", 0)
            overall_results["overall_matches"] += section3_result.get("matches", 0)
            overall_results["overall_mismatches"] += section3_result.get("mismatches", 0)
        else:
            logger.warning("Table 1 (Page 2) not found - Section 3 skipped")

        # =================================================================
        # Reconcile Table 2 (Page 2) - Summary cells
        # Excel cells: CD110, CD111, CD113
        # =================================================================
        # TODO: Implement special cell reconciliation
        # This requires different logic than table-based reconciliation
        logger.info("Table 2 (Page 2) - Summary cells: Not yet implemented")

        # Calculate overall match percentage
        if overall_results["overall_cells_compared"] > 0:
            overall_results["overall_match_percentage"] = round(
                (overall_results["overall_matches"] / overall_results["overall_cells_compared"]) * 100, 2
            )

        logger.info(
            f"CEI reconciliation finished: {overall_results['overall_match_percentage']}% overall match rate "
            f"({overall_results['overall_matches']}/{overall_results['overall_cells_compared']} cells)"
        )
        return overall_results
