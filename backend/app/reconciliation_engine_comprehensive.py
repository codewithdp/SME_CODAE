"""
Comprehensive Reconciliation Engine
Cell-by-cell comparison across all sections
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from .excel_parser_custom import ExcelReconciliationData
from .pdf_processor import PDFReconciliationData

logger = logging.getLogger(__name__)


# ============================================================================
# RECONCILIATION RESULT MODELS
# ============================================================================

class CellMismatch(BaseModel):
    """Represents a single mismatch"""
    section: str
    field: str
    row_identifier: str  # e.g., "Day 1", "1º PERÍODO MATUTINO"
    excel_value: Any
    pdf_value: Any
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


# ============================================================================
# COMPREHENSIVE RECONCILIATION ENGINE
# ============================================================================

class ComprehensiveReconciliationEngine:
    """
    Comprehensive reconciliation engine
    Performs cell-by-cell comparison across all sections
    """

    def __init__(self, min_pdf_confidence: float = 0.75):
        self.min_pdf_confidence = min_pdf_confidence

    def reconcile(
        self,
        excel_data: ExcelReconciliationData,
        pdf_data: PDFReconciliationData,
        reconciliation_id: str
    ) -> ReconciliationResult:
        """
        Main reconciliation method with comprehensive comparison
        """
        logger.info(f"Starting comprehensive reconciliation for {reconciliation_id}")

        mismatches = []
        total_cells_compared = 0

        # 1. Compare EMEI codes (normalize by stripping leading zeros)
        excel_emei = excel_data.header.emei_code.strip()
        pdf_emei = pdf_data.header.emei_code.strip()

        # Normalize EMEI codes for comparison (strip leading zeros)
        excel_emei_normalized = excel_emei.lstrip('0')
        pdf_emei_normalized = pdf_emei.lstrip('0')
        emei_match = excel_emei_normalized == pdf_emei_normalized
        total_cells_compared += 1

        if not emei_match:
            mismatches.append(CellMismatch(
                section="Header",
                field="EMEI Code",
                row_identifier="Header",
                excel_value=excel_emei,
                pdf_value=pdf_emei,
                description=f"EMEI codes do not match: Excel={excel_emei}, PDF={pdf_emei}"
            ))

        # 2. Check PDF confidence
        pdf_confidence_ok = pdf_data.overall_confidence >= self.min_pdf_confidence
        if not pdf_confidence_ok:
            logger.warning(
                f"PDF confidence ({pdf_data.overall_confidence:.2f}) below "
                f"threshold ({self.min_pdf_confidence})"
            )

        # 3. Compare Section 1 - Enrollment (comprehensive)
        section1_compared, section1_mismatches = self._compare_section1_comprehensive(
            excel_data, pdf_data
        )
        total_cells_compared += section1_compared
        mismatches.extend(section1_mismatches)

        # 4. Compare Section 2 - Daily Frequency (comprehensive)
        section2_compared, section2_mismatches = self._compare_section2_comprehensive(
            excel_data, pdf_data
        )
        total_cells_compared += section2_compared
        mismatches.extend(section2_mismatches)

        # 5. Compare Section 3 - Special Diet Data (comprehensive)
        section3_compared, section3_mismatches = self._compare_section3_comprehensive(
            excel_data, pdf_data
        )
        total_cells_compared += section3_compared
        mismatches.extend(section3_mismatches)

        # Calculate statistics
        total_mismatches = len(mismatches)
        match_percentage = ((total_cells_compared - total_mismatches) / max(1, total_cells_compared)) * 100

        # Row counts
        excel_row_count = len(excel_data.section2.primeiro_periodo)
        pdf_row_count = pdf_data.section2_table.row_count if pdf_data.section2_table else None
        row_count_match = excel_row_count == pdf_row_count if pdf_row_count else False

        # Determine status
        if total_mismatches == 0 and pdf_confidence_ok:
            status = "match"
        elif match_percentage >= 90:
            status = "warning"
        else:
            status = "mismatch"

        # Get totals
        excel_total = excel_data.section1.total_students
        pdf_total = self._extract_pdf_total_students(pdf_data)

        result = ReconciliationResult(
            reconciliation_id=reconciliation_id,
            emei_code_match=emei_match,
            excel_emei=excel_emei,
            pdf_emei=pdf_emei,
            emei_id_excel=excel_emei,
            id_match=emei_match,
            pdf_confidence_ok=pdf_confidence_ok,
            pdf_overall_confidence=pdf_data.overall_confidence,
            total_mismatches=total_mismatches,
            total_cells_compared=total_cells_compared,
            mismatches=mismatches,
            excel_total_students=excel_total,
            pdf_total_students=pdf_total,
            excel_row_count=excel_row_count,
            pdf_row_count=pdf_row_count,
            row_count_match=row_count_match,
            excel_filename=excel_data.filename,
            pdf_filename=pdf_data.filename,
            overall_match_percentage=match_percentage,
            status=status
        )

        logger.info(
            f"Comprehensive reconciliation complete: {total_cells_compared} cells compared, "
            f"{total_mismatches} mismatches ({match_percentage:.1f}% match)"
        )

        return result

    def _compare_section1_comprehensive(
        self,
        excel_data: ExcelReconciliationData,
        pdf_data: PDFReconciliationData
    ) -> tuple[int, List[CellMismatch]]:
        """
        Comprehensive Section 1 comparison: enrollment data by period

        Compares ALL periods (including empty rows) for complete reconciliation
        """
        logger.info("Comparing Section 1 (Enrollment) comprehensively...")

        cells_compared = 0
        mismatches = []

        if not pdf_data.section1_table:
            logger.warning("No PDF Section 1 table found")
            return cells_compared, mismatches

        # Build PDF data map by period name - include ALL periods except header
        pdf_periods = {}
        pdf_total_row = None

        for row_idx, row in enumerate(pdf_data.section1_table.cells):
            if row_idx == 0:  # Skip header
                continue

            period_name = str(row[0] if len(row) > 0 else "").strip()
            if not period_name:
                continue

            # PDF structure: Col 0=Period, Col 1=Hours, Col 2=Students, Col 3=Diet A, Col 4=Diet B
            students = self._safe_int(row[2] if len(row) > 2 else None)
            diet_a = self._safe_int(row[3] if len(row) > 3 else None)
            diet_b = self._safe_int(row[4] if len(row) > 4 else None)

            # Check if this is the TOTAL row
            if "TOTAL" in period_name.upper():
                pdf_total_row = {
                    "students": students,
                    "diet_a": diet_a,
                    "diet_b": diet_b
                }
            else:
                # Add all other periods (including INTEGRAL, INTERMEDIÁRIO)
                pdf_periods[self._normalize_period_name(period_name)] = {
                    "students": students,
                    "diet_a": diet_a,
                    "diet_b": diet_b
                }

        # Compare each Excel period with PDF (ALL periods)
        for excel_period in excel_data.section1.periods:
            # Find matching PDF period using fuzzy matching
            pdf_period = None
            for pdf_period_name, pdf_data in pdf_periods.items():
                if self._periods_match(excel_period.period_name, pdf_period_name):
                    pdf_period = pdf_data
                    break

            if pdf_period is None:
                logger.warning(f"Period not found in PDF: {excel_period.period_name}")
                # Still count as compared but mark as mismatch
                cells_compared += 3
                mismatches.append(CellMismatch(
                    section="Section1",
                    field="Period Missing",
                    row_identifier=excel_period.period_name,
                    excel_value=f"{excel_period.num_students}, {excel_period.special_diet_a}, {excel_period.special_diet_b}",
                    pdf_value="Period not found in PDF",
                    description=f"Period {excel_period.period_name} exists in Excel but not in PDF"
                ))
                continue

            # Compare student count (treat None and 0 as equivalent)
            cells_compared += 1
            excel_students = excel_period.num_students if excel_period.num_students is not None else 0
            pdf_students = pdf_period["students"] if pdf_period["students"] is not None else 0
            if excel_students != pdf_students:
                mismatches.append(CellMismatch(
                    section="Section1",
                    field="Number of Students",
                    row_identifier=excel_period.period_name,
                    excel_value=excel_period.num_students,
                    pdf_value=pdf_period["students"],
                    description=f"Student count mismatch for {excel_period.period_name}"
                ))

            # Compare diet A (treat None and 0 as equivalent)
            cells_compared += 1
            excel_diet_a = excel_period.special_diet_a if excel_period.special_diet_a is not None else 0
            pdf_diet_a = pdf_period["diet_a"] if pdf_period["diet_a"] is not None else 0
            if excel_diet_a != pdf_diet_a:
                mismatches.append(CellMismatch(
                    section="Section1",
                    field="Special Diet A",
                    row_identifier=excel_period.period_name,
                    excel_value=excel_period.special_diet_a,
                    pdf_value=pdf_period["diet_a"],
                    description=f"Diet A mismatch for {excel_period.period_name}"
                ))

            # Compare diet B (treat None and 0 as equivalent)
            cells_compared += 1
            excel_diet_b = excel_period.special_diet_b if excel_period.special_diet_b is not None else 0
            pdf_diet_b = pdf_period["diet_b"] if pdf_period["diet_b"] is not None else 0
            if excel_diet_b != pdf_diet_b:
                mismatches.append(CellMismatch(
                    section="Section1",
                    field="Special Diet B",
                    row_identifier=excel_period.period_name,
                    excel_value=excel_period.special_diet_b,
                    pdf_value=pdf_period["diet_b"],
                    description=f"Diet B mismatch for {excel_period.period_name}"
                ))

        # Compare totals (all 3 fields)
        if pdf_total_row:
            # Total students
            cells_compared += 1
            excel_total = excel_data.section1.total_students
            pdf_total = pdf_total_row["students"] if pdf_total_row["students"] is not None else 0
            if excel_total != pdf_total:
                mismatches.append(CellMismatch(
                    section="Section1",
                    field="Total Students",
                    row_identifier="TOTAL",
                    excel_value=excel_total,
                    pdf_value=pdf_total_row["students"],
                    description="Total student count mismatch"
                ))

            # Total diet A
            cells_compared += 1
            excel_total_a = excel_data.section1.total_special_diet_a
            pdf_total_a = pdf_total_row["diet_a"] if pdf_total_row["diet_a"] is not None else 0
            if excel_total_a != pdf_total_a:
                mismatches.append(CellMismatch(
                    section="Section1",
                    field="Total Special Diet A",
                    row_identifier="TOTAL",
                    excel_value=excel_total_a,
                    pdf_value=pdf_total_row["diet_a"],
                    description="Total Diet A mismatch"
                ))

            # Total diet B
            cells_compared += 1
            excel_total_b = excel_data.section1.total_special_diet_b
            pdf_total_b = pdf_total_row["diet_b"] if pdf_total_row["diet_b"] is not None else 0
            if excel_total_b != pdf_total_b:
                mismatches.append(CellMismatch(
                    section="Section1",
                    field="Total Special Diet B",
                    row_identifier="TOTAL",
                    excel_value=excel_total_b,
                    pdf_value=pdf_total_row["diet_b"],
                    description="Total Diet B mismatch"
                ))

        logger.info(f"Section 1: {cells_compared} cells compared, {len(mismatches)} mismatches")
        return cells_compared, mismatches

    def _compare_section2_comprehensive(
        self,
        excel_data: ExcelReconciliationData,
        pdf_data: PDFReconciliationData
    ) -> tuple[int, List[CellMismatch]]:
        """
        Compare ALL Section 2 cells: 1,116 total
        - INTEGRAL: 11 fields × 31 days = 341 cells
        - P1: 7 fields × 31 days = 217 cells
        - INTERMEDIÁRIO: 6 fields × 31 days = 186 cells
        - P3: 7 fields × 31 days = 217 cells
        - DOCE: 4 fields × 31 days = 124 cells
        - TOTAL row: 31 fields
        """
        logger.info("Comparing Section 2 (Daily Frequency) comprehensively - ALL 1,116 cells...")

        cells_compared = [0]  # Use list to allow modification in helper
        mismatches = []

        if not pdf_data.section2_table:
            logger.warning("No PDF Section 2 table found")
            return 0, []

        # Build PDF data map by day (rows 3+ = days 1-31)
        pdf_days = {}
        pdf_total_row = None

        # Debug: Show PDF table structure
        if pdf_data.section2_table.cells:
            print(f"\nDEBUG: PDF Section 2 table structure:")
            print(f"  Total rows: {len(pdf_data.section2_table.cells)}")
            print(f"  Total columns: {len(pdf_data.section2_table.cells[0]) if pdf_data.section2_table.cells else 0}")
            print(f"\n  First data row (row 3, day 1):")
            if len(pdf_data.section2_table.cells) > 3:
                row3 = pdf_data.section2_table.cells[3]
                for col_idx, cell_val in enumerate(row3[:15]):  # Show first 15 columns
                    print(f"    Col {col_idx}: {cell_val}")

        for row_idx, row in enumerate(pdf_data.section2_table.cells):
            if row_idx < 3:  # Skip headers
                continue

            day_str = str(row[0] if len(row) > 0 else "").strip()

            # Check if this is TOTAL row
            if "TOTAL" in day_str.upper():
                pdf_total_row = row
                continue

            day = self._safe_int(day_str)
            if not day or day < 1 or day > 31:
                continue

            # Extract ALL 35 fields
            pdf_days[day] = {
                # INTEGRAL (11 fields, PDF cols 1-11)
                "integral": {
                    "frequencia": self._safe_int(row[1] if len(row) > 1 else None),
                    "lanche_4h": self._safe_int(row[2] if len(row) > 2 else None),
                    "lanche_6h": self._safe_int(row[3] if len(row) > 3 else None),
                    "refeicao": self._safe_int(row[4] if len(row) > 4 else None),
                    "repeticao_refeicao": self._safe_int(row[5] if len(row) > 5 else None),
                    "sobremesa": self._safe_int(row[6] if len(row) > 6 else None),
                    "repeticao_sobremesa": self._safe_int(row[7] if len(row) > 7 else None),
                    "refeicao_2a": self._safe_int(row[8] if len(row) > 8 else None),
                    "repeticao_refeicao_2a": self._safe_int(row[9] if len(row) > 9 else None),
                    "sobremesa_2a": self._safe_int(row[10] if len(row) > 10 else None),
                    "repeticao_sobremesa_2a": self._safe_int(row[11] if len(row) > 11 else None),
                },
                # P1 (7 fields, PDF cols 12-18)
                "p1": {
                    "frequencia": self._safe_int(row[12] if len(row) > 12 else None),
                    "lanche_4h": self._safe_int(row[13] if len(row) > 13 else None),
                    "lanche_6h": self._safe_int(row[14] if len(row) > 14 else None),
                    "refeicao": self._safe_int(row[15] if len(row) > 15 else None),
                    "repeticao_refeicao": self._safe_int(row[16] if len(row) > 16 else None),
                    "sobremesa": self._safe_int(row[17] if len(row) > 17 else None),
                    "repeticao_sobremesa": self._safe_int(row[18] if len(row) > 18 else None),
                },
                # INTERMEDIÁRIO (6 fields, PDF cols 19-24)
                "intermediario": {
                    "frequencia": self._safe_int(row[19] if len(row) > 19 else None),
                    "lanche_4h": self._safe_int(row[20] if len(row) > 20 else None),
                    "refeicao": self._safe_int(row[21] if len(row) > 21 else None),
                    "repeticao_refeicao": self._safe_int(row[22] if len(row) > 22 else None),
                    "sobremesa": self._safe_int(row[23] if len(row) > 23 else None),
                    "repeticao_sobremesa": self._safe_int(row[24] if len(row) > 24 else None),
                },
                # P3 (7 fields, PDF cols 25-31)
                "p3": {
                    "frequencia": self._safe_int(row[25] if len(row) > 25 else None),
                    "lanche_4h": self._safe_int(row[26] if len(row) > 26 else None),
                    "lanche_6h": self._safe_int(row[27] if len(row) > 27 else None),
                    "refeicao": self._safe_int(row[28] if len(row) > 28 else None),
                    "repeticao_refeicao": self._safe_int(row[29] if len(row) > 29 else None),
                    "sobremesa": self._safe_int(row[30] if len(row) > 30 else None),
                    "repeticao_sobremesa": self._safe_int(row[31] if len(row) > 31 else None),
                },
                # DOCE checkboxes (4 fields, PDF cols 32-35)
                "doce": {
                    "integral": self._is_checkbox_selected(row[32] if len(row) > 32 else None),
                    "p1": self._is_checkbox_selected(row[33] if len(row) > 33 else None),
                    "intermediario": self._is_checkbox_selected(row[34] if len(row) > 34 else None),
                    "p3": self._is_checkbox_selected(row[35] if len(row) > 35 else None),
                }
            }

        # Compare ALL days (31 days)
        for day in range(1, 32):
            pdf_day = pdf_days.get(day, {})

            # Compare INTEGRAL (11 fields)
            excel_int = excel_data.section2.integral[day - 1]  # 0-indexed
            pdf_int = pdf_day.get("integral", {})

            self._compare_field(excel_int.frequencia, pdf_int.get("frequencia"),
                               "Section2", "INTEGRAL - Frequência", day, mismatches, cells_compared)
            self._compare_field(excel_int.lanche_4h, pdf_int.get("lanche_4h"),
                               "Section2", "INTEGRAL - Lanche 4h", day, mismatches, cells_compared)
            self._compare_field(excel_int.lanche_6h, pdf_int.get("lanche_6h"),
                               "Section2", "INTEGRAL - Lanche 6h", day, mismatches, cells_compared)
            self._compare_field(excel_int.refeicao, pdf_int.get("refeicao"),
                               "Section2", "INTEGRAL - Refeição", day, mismatches, cells_compared)
            self._compare_field(excel_int.repeticao_refeicao, pdf_int.get("repeticao_refeicao"),
                               "Section2", "INTEGRAL - Repetição Refeição", day, mismatches, cells_compared)
            self._compare_field(excel_int.sobremesa, pdf_int.get("sobremesa"),
                               "Section2", "INTEGRAL - Sobremesa", day, mismatches, cells_compared)
            self._compare_field(excel_int.repeticao_sobremesa, pdf_int.get("repeticao_sobremesa"),
                               "Section2", "INTEGRAL - Repetição Sobremesa", day, mismatches, cells_compared)
            self._compare_field(excel_int.refeicao_2a, pdf_int.get("refeicao_2a"),
                               "Section2", "INTEGRAL - 2ª Refeição", day, mismatches, cells_compared)
            self._compare_field(excel_int.repeticao_refeicao_2a, pdf_int.get("repeticao_refeicao_2a"),
                               "Section2", "INTEGRAL - Repetição 2ª Refeição", day, mismatches, cells_compared)
            self._compare_field(excel_int.sobremesa_2a, pdf_int.get("sobremesa_2a"),
                               "Section2", "INTEGRAL - 2ª Sobremesa", day, mismatches, cells_compared)
            self._compare_field(excel_int.repeticao_sobremesa_2a, pdf_int.get("repeticao_sobremesa_2a"),
                               "Section2", "INTEGRAL - Repetição 2ª Sobremesa", day, mismatches, cells_compared)

            # Compare P1 (7 fields)
            excel_p1 = excel_data.section2.primeiro_periodo[day - 1]
            pdf_p1 = pdf_day.get("p1", {})

            self._compare_field(excel_p1.frequencia, pdf_p1.get("frequencia"),
                               "Section2", "P1 - Frequência", day, mismatches, cells_compared)
            self._compare_field(excel_p1.lanche_4h, pdf_p1.get("lanche_4h"),
                               "Section2", "P1 - Lanche 4h", day, mismatches, cells_compared)
            self._compare_field(excel_p1.lanche_6h, pdf_p1.get("lanche_6h"),
                               "Section2", "P1 - Lanche 6h", day, mismatches, cells_compared)
            self._compare_field(excel_p1.refeicao, pdf_p1.get("refeicao"),
                               "Section2", "P1 - Refeição", day, mismatches, cells_compared)
            self._compare_field(excel_p1.repeticao_refeicao, pdf_p1.get("repeticao_refeicao"),
                               "Section2", "P1 - Repetição Refeição", day, mismatches, cells_compared)
            self._compare_field(excel_p1.sobremesa, pdf_p1.get("sobremesa"),
                               "Section2", "P1 - Sobremesa", day, mismatches, cells_compared)
            self._compare_field(excel_p1.repeticao_sobremesa, pdf_p1.get("repeticao_sobremesa"),
                               "Section2", "P1 - Repetição Sobremesa", day, mismatches, cells_compared)

            # Compare INTERMEDIÁRIO (6 fields)
            excel_inter = excel_data.section2.intermediario[day - 1]
            pdf_inter = pdf_day.get("intermediario", {})

            self._compare_field(excel_inter.frequencia, pdf_inter.get("frequencia"),
                               "Section2", "INTERMEDIÁRIO - Frequência", day, mismatches, cells_compared)
            self._compare_field(excel_inter.lanche_4h, pdf_inter.get("lanche_4h"),
                               "Section2", "INTERMEDIÁRIO - Lanche 4h", day, mismatches, cells_compared)
            self._compare_field(excel_inter.refeicao, pdf_inter.get("refeicao"),
                               "Section2", "INTERMEDIÁRIO - Refeição", day, mismatches, cells_compared)
            self._compare_field(excel_inter.repeticao_refeicao, pdf_inter.get("repeticao_refeicao"),
                               "Section2", "INTERMEDIÁRIO - Repetição Refeição", day, mismatches, cells_compared)
            self._compare_field(excel_inter.sobremesa, pdf_inter.get("sobremesa"),
                               "Section2", "INTERMEDIÁRIO - Sobremesa", day, mismatches, cells_compared)
            self._compare_field(excel_inter.repeticao_sobremesa, pdf_inter.get("repeticao_sobremesa"),
                               "Section2", "INTERMEDIÁRIO - Repetição Sobremesa", day, mismatches, cells_compared)

            # Compare P3 (7 fields)
            excel_p3 = excel_data.section2.terceiro_periodo[day - 1]
            pdf_p3 = pdf_day.get("p3", {})

            self._compare_field(excel_p3.frequencia, pdf_p3.get("frequencia"),
                               "Section2", "P3 - Frequência", day, mismatches, cells_compared)
            self._compare_field(excel_p3.lanche_4h, pdf_p3.get("lanche_4h"),
                               "Section2", "P3 - Lanche 4h", day, mismatches, cells_compared)
            self._compare_field(excel_p3.lanche_6h, pdf_p3.get("lanche_6h"),
                               "Section2", "P3 - Lanche 6h", day, mismatches, cells_compared)
            self._compare_field(excel_p3.refeicao, pdf_p3.get("refeicao"),
                               "Section2", "P3 - Refeição", day, mismatches, cells_compared)
            self._compare_field(excel_p3.repeticao_refeicao, pdf_p3.get("repeticao_refeicao"),
                               "Section2", "P3 - Repetição Refeição", day, mismatches, cells_compared)
            self._compare_field(excel_p3.sobremesa, pdf_p3.get("sobremesa"),
                               "Section2", "P3 - Sobremesa", day, mismatches, cells_compared)
            self._compare_field(excel_p3.repeticao_sobremesa, pdf_p3.get("repeticao_sobremesa"),
                               "Section2", "P3 - Repetição Sobremesa", day, mismatches, cells_compared)

            # Compare DOCE checkboxes (4 fields)
            excel_doce = excel_data.section2.doce_checkboxes[day - 1]
            pdf_doce = pdf_day.get("doce", {})

            self._compare_checkbox(excel_doce.integral, pdf_doce.get("integral"),
                                  "Section2", "DOCE - INTEGRAL", day, mismatches, cells_compared)
            self._compare_checkbox(excel_doce.primeiro_periodo, pdf_doce.get("p1"),
                                  "Section2", "DOCE - P1", day, mismatches, cells_compared)
            self._compare_checkbox(excel_doce.intermediario, pdf_doce.get("intermediario"),
                                  "Section2", "DOCE - INTERMEDIÁRIO", day, mismatches, cells_compared)
            self._compare_checkbox(excel_doce.terceiro_periodo, pdf_doce.get("p3"),
                                  "Section2", "DOCE - P3", day, mismatches, cells_compared)

        # TODO: Compare TOTAL row (31 fields)

        logger.info(f"Section 2: {cells_compared[0]} cells compared, {len(mismatches)} mismatches")
        return cells_compared[0], mismatches

    def _compare_field(self, excel_val, pdf_val, section, field, day, mismatches, cells_compared):
        """
        Helper to compare a single field and track mismatches
        Treats None and 0 as equivalent for numeric fields
        """
        # Always count the cell
        cells_compared[0] += 1

        # Normalize None and 0
        excel_norm = excel_val if excel_val is not None else 0
        pdf_norm = pdf_val if pdf_val is not None else 0

        if excel_norm != pdf_norm:
            mismatches.append(CellMismatch(
                section=section,
                field=field,
                row_identifier=f"Day {day}",
                excel_value=excel_val,
                pdf_value=pdf_val,
                description=f"{field} mismatch for day {day}"
            ))

    def _compare_checkbox(self, excel_val, pdf_val, section, field, day, mismatches, cells_compared):
        """Helper to compare checkbox fields (True/False/None)"""
        cells_compared[0] += 1

        # Normalize: None and False are equivalent for checkboxes
        excel_norm = excel_val if excel_val else False
        pdf_norm = pdf_val if pdf_val else False

        if excel_norm != pdf_norm:
            mismatches.append(CellMismatch(
                section=section,
                field=field,
                row_identifier=f"Day {day}",
                excel_value=excel_val,
                pdf_value=pdf_val,
                description=f"{field} checkbox mismatch for day {day}"
            ))

    def _is_checkbox_selected(self, val) -> Optional[bool]:
        """Check if PDF checkbox is selected (:selected: vs :unselected:)"""
        if val is None or val == "":
            return None
        val_str = str(val).strip().lower()
        if "selected" in val_str and "unselected" not in val_str:
            return True
        if "unselected" in val_str:
            return False
        return None

    def _extract_pdf_total_students(self, pdf_data: PDFReconciliationData) -> Optional[int]:
        """Extract total students from PDF Section 1 table"""
        if not pdf_data.section1_table:
            return None

        # Look for TOTAL row
        for row in pdf_data.section1_table.cells:
            if len(row) > 0 and "TOTAL" in str(row[0]).upper():
                # PDF structure: Col 0=Period, Col 1=Hours, Col 2=Students
                return self._safe_int(row[2] if len(row) > 2 else None)

        return None

    def _normalize_period_name(self, name: str) -> str:
        """
        Normalize period name for comparison
        Handles OCR errors and variations
        """
        import unicodedata

        name = name.strip().upper()

        # Remove accents (INTERMEDIÁRIO → INTERMEDIARIO)
        name = ''.join(
            c for c in unicodedata.normalize('NFD', name)
            if unicodedata.category(c) != 'Mn'
        )

        # Remove common variations
        name = name.replace("º", "").replace("°", "")
        name = name.replace("PERÍODO", "").replace("PERIODO", "")

        # Handle common OCR errors
        name = name.replace(".O", "O")  # "INTERMEDIAR.O" → "INTERMEDIARO"
        name = name.replace(".", "")    # Remove other dots
        name = name.replace(" ", "")    # Remove spaces for comparison

        return name.strip()

    def _periods_match(self, name1: str, name2: str) -> bool:
        """
        Check if two period names match, allowing for minor OCR errors
        Uses fuzzy matching with 85% similarity threshold
        """
        norm1 = self._normalize_period_name(name1)
        norm2 = self._normalize_period_name(name2)

        # Exact match
        if norm1 == norm2:
            return True

        # Fuzzy match for OCR errors
        # Calculate similarity: longer common prefix / shorter length
        min_len = min(len(norm1), len(norm2))
        if min_len == 0:
            return False

        # Count matching characters at the start
        matching = 0
        for c1, c2 in zip(norm1, norm2):
            if c1 == c2:
                matching += 1
            else:
                break

        # If 85% or more characters match, consider it a match
        similarity = matching / min_len
        return similarity >= 0.85

    def _compare_section3_comprehensive(self, excel_data, pdf_data):
        """
        Compare Section 3: Special Diet Data (comprehensive)
        Compares all 11 fields × 31 days = 341 cells + Total row
        """
        cells_compared = [0]  # Use list for pass-by-reference
        mismatches = []

        # Check if Section 3 exists in both Excel and PDF
        if not excel_data.section3:
            logger.warning("Section 3 not found in Excel data")
            return 0, []

        if not pdf_data.section3_table:
            logger.warning("Section 3 table not found in PDF")
            return 0, []

        # Build PDF data map by day (rows 3+ = days 1-31, rows 0-1 = headers, row 2 can be day 1 or another header)
        # Based on earlier analysis: Row 2 = Day 1, Row 3 = Day 2, etc.
        pdf_days = {}

        for row_idx, row in enumerate(pdf_data.section3_table.cells):
            if row_idx < 2:  # Skip first 2 header rows
                continue

            # Get day number from column 0
            day_str = str(row[0] if len(row) > 0 else "").strip()

            # Check if this is TOTAL row
            if "TOTAL" in day_str.upper():
                # Handle total row separately
                continue

            day = self._safe_int(day_str)
            if not day or day < 1 or day > 31:
                continue

            # Extract all 11 fields from PDF (columns 0-11)
            # Based on PDF structure: 12 columns total
            # Col 0: Day
            # Col 1-4: Group A fields
            # Col 5-7: Group B fields
            # Col 8-9: Emergency snacks
            # Col 10: (might be empty)
            # Col 11: Observations
            pdf_days[day] = {
                "grupo_a_frequencia": self._safe_int(row[1] if len(row) > 1 else None),
                "grupo_a_lanche_4h": self._safe_int(row[2] if len(row) > 2 else None),
                "grupo_a_lanche_6h": self._safe_int(row[3] if len(row) > 3 else None),
                "grupo_a_refeicao_enteral": self._safe_int(row[4] if len(row) > 4 else None),
                "grupo_b_frequencia": self._safe_int(row[5] if len(row) > 5 else None),
                "grupo_b_lanche_4h": self._safe_int(row[6] if len(row) > 6 else None),
                "grupo_b_lanche_6h": self._safe_int(row[7] if len(row) > 7 else None),
                "lanche_emergencial": self._safe_int(row[8] if len(row) > 8 else None),
                "kit_lanche": self._safe_int(row[9] if len(row) > 9 else None),
                "observacoes": str(row[11] if len(row) > 11 and row[11] else "").strip() or None
            }

        # Compare all 31 days
        for excel_day in excel_data.section3.days:
            day = excel_day.day
            pdf_day = pdf_days.get(day, {})

            # Compare all 11 fields
            self._compare_field(excel_day.grupo_a_frequencia, pdf_day.get("grupo_a_frequencia"),
                               "Section3", "Group A - Frequência", day, mismatches, cells_compared)
            self._compare_field(excel_day.grupo_a_lanche_4h, pdf_day.get("grupo_a_lanche_4h"),
                               "Section3", "Group A - Lanche 4h", day, mismatches, cells_compared)
            self._compare_field(excel_day.grupo_a_lanche_6h, pdf_day.get("grupo_a_lanche_6h"),
                               "Section3", "Group A - Lanche 6h", day, mismatches, cells_compared)
            self._compare_field(excel_day.grupo_a_refeicao_enteral, pdf_day.get("grupo_a_refeicao_enteral"),
                               "Section3", "Group A - Refeição Enteral", day, mismatches, cells_compared)
            self._compare_field(excel_day.grupo_b_frequencia, pdf_day.get("grupo_b_frequencia"),
                               "Section3", "Group B - Frequência", day, mismatches, cells_compared)
            self._compare_field(excel_day.grupo_b_lanche_4h, pdf_day.get("grupo_b_lanche_4h"),
                               "Section3", "Group B - Lanche 4h", day, mismatches, cells_compared)
            self._compare_field(excel_day.grupo_b_lanche_6h, pdf_day.get("grupo_b_lanche_6h"),
                               "Section3", "Group B - Lanche 6h", day, mismatches, cells_compared)
            self._compare_field(excel_day.lanche_emergencial, pdf_day.get("lanche_emergencial"),
                               "Section3", "Lanche Emergencial", day, mismatches, cells_compared)
            self._compare_field(excel_day.kit_lanche, pdf_day.get("kit_lanche"),
                               "Section3", "Kit Lanche", day, mismatches, cells_compared)

            # Compare observations (text field, can be None)
            excel_obs = excel_day.observacoes
            pdf_obs = pdf_day.get("observacoes")
            cells_compared[0] += 1
            # Only flag mismatch if both have values and they differ
            if excel_obs and pdf_obs and excel_obs != pdf_obs:
                mismatches.append({
                    "section": "Section3",
                    "field": "Observações",
                    "row_identifier": f"Day {day}",
                    "excel_value": excel_obs,
                    "pdf_value": pdf_obs,
                    "description": f"Observações mismatch for day {day}"
                })

        logger.info(f"Section 3 comparison: {cells_compared[0]} cells compared, {len(mismatches)} mismatches")
        return cells_compared[0], mismatches

    def _safe_int(self, value) -> Optional[int]:
        """Safely convert value to int"""
        if value is None or value == "":
            return None
        try:
            # Handle string numbers
            if isinstance(value, str):
                value = value.strip()
                if not value:
                    return None
            return int(float(value))
        except (ValueError, TypeError):
            return None


# Export as ReconciliationEngine
ReconciliationEngine = ComprehensiveReconciliationEngine
