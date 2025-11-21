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

            # Page 1, Table 2: ~11-12 rows x 6-7 columns
            if page_num == 1 and 10 <= rows <= 13 and 6 <= cols <= 7:
                table2_page1_idx = idx
                logger.info(f"Found Table 2 (Page 1) at index {idx}: {rows}x{cols}")

            # Page 1, Table 3: ~35 rows x 17-19 columns
            elif page_num == 1 and 33 <= rows <= 37 and 16 <= cols <= 19:
                table3_page1_idx = idx
                logger.info(f"Found Table 3 (Page 1) at index {idx}: {rows}x{cols}")

            # Page 2, Table 1: ~34-39 rows x 30-32 columns
            elif page_num == 2 and 32 <= rows <= 40 and 30 <= cols <= 32:
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
        # First data cell: Y16 (N° Matriculados Integral)
        # =================================================================
        if table2_p1_idx is not None:
            logger.info("Reconciling Table 2 (Page 1) - Section 1A...")

            table2 = pdf_analysis_result.tables[table2_p1_idx]

            # Build sequential mapping based on first data cell Y16
            # PDF structure: col 0=Faixa Etária (labels), then data columns
            # For 7-col table: cols 1-6 = Integral(N°), Parcial(N°), Integral(A), Parcial(A), Integral(B), Parcial(B)
            # For 6-col table: cols 1-5 = one column is missing

            logger.info(f"Table 2 has {table2.row_count} rows x {table2.column_count} columns")

            # Y = col 24 (absolute), so start_col_idx = 24
            # Build mapping: Excel absolute col -> PDF col
            # Sequential from first data cell (Y -> PDF col 1)
            if table2.column_count == 7:
                # Standard 7-col table
                abs_mapping = {
                    24: 1,   # Y (rel 0): N° Matriculados Integral
                    43: 2,   # AR (rel 19): N° Matriculados Parcial
                    94: 5,   # CQ (rel 70): Dieta Especial Tipo B Integral
                }
            else:
                # 6-col table - adjust mapping (assume last col is missing)
                abs_mapping = {
                    24: 1,   # Y (rel 0): N° Matriculados Integral
                    43: 2,   # AR (rel 19): N° Matriculados Parcial
                    94: table2.column_count - 2,  # CQ: second to last col
                }
                logger.info(f"Adjusted mapping for {table2.column_count}-col table: CQ -> col {table2.column_count - 2}")

            abs_names = self._convert_relative_to_absolute_names(
                TABLE2_PAGE1_COLUMN_NAMES, "Y"
            )

            # Find first data row by looking for "0 a 1" in column 0 (first age group)
            pdf_data_start = 2  # default
            for cell in table2.cells:
                if cell.column_index == 0 and cell.content:
                    content = cell.content.strip().lower()
                    if "0 a 1" in content or "0a1" in content:
                        pdf_data_start = cell.row_index
                        logger.info(f"Found first data row at {pdf_data_start}: '{cell.content.strip()}'")
                        break

            section1_result = self.positional_engine.reconcile_section(
                pdf_path=pdf_path,
                excel_path=excel_path,
                table_index=table2_p1_idx,
                excel_start_row=16,  # Row 16 = "0 a 1 mês" (empty)
                column_mapping=abs_mapping,
                column_names=abs_names,
                pdf_data_start_row=pdf_data_start,  # Skip header rows plus any extra
                excel_row_skip=0,  # No skip needed - Total at row 24
                pdf_table=table2,
                sheet_name="CEI",
                auto_detect_day1=False  # Section 1 has age ranges, not days
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

            table3 = pdf_analysis_result.tables[table3_p1_idx]

            # Build sequential mapping based on data cell positions
            # First data cell M31 -> PDF col 1 (after DIA at col 0)
            # INTEGRAL: cols 1-7 (fixed, 7 data columns)
            # OBSERVAÇÕES: col 8 (may span multiple columns)
            # PARCIAL: starts after OBSERVAÇÕES span

            logger.info(f"Table 3 has {table3.column_count} columns")

            # Find OBSERVAÇÕES span to determine where PARCIAL starts
            # Look at Day 1 data row (find row where col 0 = "1")
            obs_span = 1  # default
            for cell in table3.cells:
                if cell.column_index == 8:
                    # Check if this is a data row (not header)
                    row_cells = {c.column_index: c for c in table3.cells if c.row_index == cell.row_index}
                    if row_cells.get(0) and row_cells[0].content and row_cells[0].content.strip() == "1":
                        obs_span = cell.column_span if hasattr(cell, 'column_span') and cell.column_span else 1
                        break

            parcial_start = 8 + obs_span  # PARCIAL starts after OBSERVAÇÕES
            logger.info(f"OBSERVAÇÕES span={obs_span}, PARCIAL starts at col {parcial_start}")

            # Build mapping sequentially from first data cell
            # Excel col (abs) -> PDF col
            # M = col 12, so rel + 12 = abs
            abs_mapping = {
                # INTEGRAL (cols 1-7, sequential from col 1)
                15: 2,   # P (rel 3): 01 a 03 M
                18: 3,   # S (rel 6): 04 a 05 M
                21: 4,   # V (rel 9): 6 M
                24: 5,   # Y (rel 12): 07 a 11 M
                27: 6,   # AB (rel 15): 01 a 03 anos e 11 meses
                30: 7,   # AE (rel 18): 04 a 06 anos
                # PARCIAL (sequential from parcial_start)
                84: parcial_start + 5,  # CI (rel 72): 01 a 03 anos e 11 meses
                87: parcial_start + 6,  # CL (rel 75): 04 a 06 anos
            }

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
                pdf_table=table3,
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

            table1_p2 = pdf_analysis_result.tables[table1_p2_idx]

            # Build sequential mapping based on data cell positions
            # M71 is first data cell (Day 1, col 0 a 1 M)
            # Structure: col 0=DIA, then 4 sections of 7 cols each
            # Section 1: cols 1-7, Section 2: cols 8-14, Section 3: cols 15-21, Section 4: cols 22-28

            logger.info(f"Table 1 (Page 2) has {table1_p2.row_count} rows x {table1_p2.column_count} columns")

            # Build mapping sequentially (M = col 12, so rel + 12 = abs)
            abs_mapping = {
                # Section 1 (cols 1-7) - no 0a1M in Excel
                15: 2,   # rel 3: 01 a 03 M
                18: 3,   # rel 6: 04 a 05 M
                21: 4,   # rel 9: 6 M
                24: 5,   # rel 12: 07 a 11 M
                27: 6,   # rel 15: 01 a 03 anos e 11 meses
                30: 7,   # rel 18: 04 a 06 anos

                # Section 2 (cols 8-14) - has 0a1M at col 8
                34: 8,   # rel 22: 0 a 1 M
                37: 9,   # rel 25: 01 a 03 M
                40: 10,  # rel 28: 04 a 05 M
                43: 11,  # rel 31: 6 M
                46: 12,  # rel 34: 07 a 11 M
                49: 13,  # rel 37: 01 a 03 anos e 11 meses
                53: 14,  # rel 41: 04 a 06 anos

                # Section 3 (cols 15-21) - partial section in Excel
                69: 19,  # rel 57: 07 a 11 M
                72: 20,  # rel 60: 01 a 03 anos e 11 meses
                75: 21,  # rel 63: 04 a 06 anos

                # Section 4 (cols 22-28) - has 0a1M at col 22
                78: 22,  # rel 66: 0 a 1 M
                81: 23,  # rel 69: 01 a 03 M
                84: 24,  # rel 72: 04 A 05 M
                87: 25,  # rel 75: 6 M
                91: 26,  # rel 79: 07 a 11 M
                94: 27,  # rel 82: 01 a 03 anos e 11 meses
            }

            abs_names = self._convert_relative_to_absolute_names(
                TABLE1_PAGE2_COLUMN_NAMES, "M"
            )

            # Adjust for varying header rows based on table size
            row_count = table1_p2.row_count
            if row_count == 34:
                pdf_data_start = 2  # 2 header rows, Day 1 at row 2
            elif row_count >= 36:
                pdf_data_start = 4  # 4 header rows, Day 1 at row 4
            else:
                pdf_data_start = max(2, row_count - 32)

            logger.info(f"Data starts at row {pdf_data_start}")

            section3_result = self.positional_engine.reconcile_section(
                pdf_path=pdf_path,
                excel_path=excel_path,
                table_index=table1_p2_idx,
                excel_start_row=71,  # M71 starts at row 71
                column_mapping=abs_mapping,
                column_names=abs_names,
                pdf_data_start_row=pdf_data_start,
                excel_row_skip=0,
                pdf_table=table1_p2,
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
