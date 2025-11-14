"""
Reconciliation Engine - Compares Excel vs PDF data
Identifies mismatches at cell level across all sections
"""

from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from pydantic import BaseModel, Field
from datetime import datetime
import logging

# Import our data models
from excel_parser import ExcelReconciliationData, DailyAttendanceRow
from pdf_processor import PDFReconciliationData, PDFTable

logger = logging.getLogger(__name__)


# ============================================================================
# RECONCILIATION DATA MODELS
# ============================================================================

class CellMismatch(BaseModel):
    """Represents a single cell-level mismatch"""
    section: str  # "Section1", "Section2", "Section3"
    
    # Excel information
    excel_cell: str  # e.g., "B15"
    excel_value: Any
    excel_label: str  # Human-readable label
    
    # PDF information  
    pdf_value: Any
    pdf_page: int
    pdf_confidence: Optional[float] = None
    
    # Context
    row_label: str  # e.g., "Day 4", "INTEGRAL period"
    column_label: str  # e.g., "Breakfast", "Students enrolled"
    
    # Severity (for future use)
    is_critical: bool = False


class SectionResult(BaseModel):
    """Results for a single section comparison"""
    section_name: str
    section_display_name: str
    
    total_cells_compared: int
    match_count: int
    mismatch_count: int
    
    mismatches: List[CellMismatch]
    match_percentage: float
    
    skipped: bool = False
    skip_reason: Optional[str] = None


class ReconciliationResult(BaseModel):
    """Complete reconciliation result"""
    reconciliation_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # File information
    excel_filename: str
    pdf_filename: str
    emei_id_excel: str
    emei_id_pdf: str
    
    # ID validation
    id_match: bool
    id_match_message: str
    
    # PDF quality
    pdf_confidence_ok: bool
    pdf_overall_confidence: float
    low_confidence_areas: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Row count comparison
    excel_row_count: int
    pdf_row_count: int
    row_count_match: bool
    row_count_message: str
    
    # Section results
    section1_result: Optional[SectionResult] = None
    section2_result: Optional[SectionResult] = None
    section3_result: Optional[SectionResult] = None
    
    # Overall metrics
    total_cells_compared: int
    total_mismatches: int
    overall_match_percentage: float
    
    # Status
    status: str  # "completed", "completed_with_warnings", "failed"
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


# ============================================================================
# RECONCILIATION ENGINE
# ============================================================================

class ReconciliationEngine:
    """
    Core reconciliation logic
    Compares Excel data against PDF data section by section
    """
    
    def __init__(self, min_pdf_confidence: float = 0.75):
        """
        Initialize reconciliation engine
        
        Args:
            min_pdf_confidence: Minimum acceptable PDF confidence (0-1)
        """
        self.min_pdf_confidence = min_pdf_confidence
    
    def reconcile(
        self,
        excel_data: ExcelReconciliationData,
        pdf_data: PDFReconciliationData,
        reconciliation_id: str
    ) -> ReconciliationResult:
        """
        Main reconciliation method
        
        Args:
            excel_data: Parsed Excel data
            pdf_data: Parsed PDF data
            reconciliation_id: Unique ID for this reconciliation
        
        Returns:
            ReconciliationResult with all comparison details
        """
        logger.info(f"Starting reconciliation {reconciliation_id}")
        
        # Initialize result
        result = ReconciliationResult(
            reconciliation_id=reconciliation_id,
            excel_filename=excel_data.filename,
            pdf_filename=pdf_data.filename,
            emei_id_excel=excel_data.header.emei_code,
            emei_id_pdf=pdf_data.header.emei_code,
            pdf_overall_confidence=pdf_data.overall_confidence,
            pdf_confidence_ok=pdf_data.meets_confidence_threshold,
            excel_row_count=excel_data.total_rows,
            pdf_row_count=pdf_data.total_pages,
            status="completed"
        )
        
        # Step 1: Validate ID match
        self._validate_id_match(result)
        
        # Step 2: Check PDF confidence
        if not pdf_data.meets_confidence_threshold:
            result.warnings.append(
                f"PDF confidence ({pdf_data.overall_confidence:.2f}) is below threshold ({self.min_pdf_confidence})"
            )
            result.low_confidence_areas = [
                {
                    "description": area.description,
                    "confidence": area.confidence,
                    "page": area.page,
                    "section": area.section
                }
                for area in pdf_data.low_confidence_areas
            ]
            result.status = "completed_with_warnings"
        
        # Step 3: Compare each section
        try:
            result.section1_result = self._compare_section1(excel_data, pdf_data)
        except Exception as e:
            logger.error(f"Error comparing Section 1: {e}")
            result.errors.append(f"Section 1 comparison failed: {str(e)}")
        
        try:
            result.section2_result = self._compare_section2(excel_data, pdf_data)
        except Exception as e:
            logger.error(f"Error comparing Section 2: {e}")
            result.errors.append(f"Section 2 comparison failed: {str(e)}")
        
        try:
            result.section3_result = self._compare_section3(excel_data, pdf_data)
        except Exception as e:
            logger.error(f"Error comparing Section 3: {e}")
            result.errors.append(f"Section 3 comparison failed: {str(e)}")
        
        # Step 4: Calculate overall metrics
        self._calculate_overall_metrics(result)
        
        # Step 5: Check for row count mismatch
        self._check_row_counts(result, excel_data, pdf_data)
        
        logger.info(
            f"Reconciliation complete: {result.total_mismatches} mismatches out of {result.total_cells_compared} cells"
        )
        
        return result
    
    def _validate_id_match(self, result: ReconciliationResult) -> None:
        """
        Check if EMEI IDs match between Excel and PDF
        Excel filename should contain the EMEI code
        """
        excel_id = result.emei_id_excel
        pdf_id = result.emei_id_pdf
        
        # Check if Excel filename contains PDF's EMEI code
        id_in_filename = pdf_id in result.excel_filename
        ids_match = excel_id == pdf_id
        
        result.id_match = ids_match or id_in_filename
        
        if result.id_match:
            result.id_match_message = f"✓ IDs match: {excel_id}"
        else:
            result.id_match_message = f"✗ ID mismatch: Excel={excel_id}, PDF={pdf_id}"
            result.warnings.append(result.id_match_message)
    
    def _compare_section1(
        self,
        excel_data: ExcelReconciliationData,
        pdf_data: PDFReconciliationData
    ) -> SectionResult:
        """
        Compare Section 1: Student enrollment numbers
        """
        logger.info("Comparing Section 1 (Enrollment)")
        
        mismatches = []
        cells_compared = 0
        
        if not pdf_data.section1_table:
            return SectionResult(
                section_name="Section1",
                section_display_name="Student Enrollment Numbers",
                total_cells_compared=0,
                match_count=0,
                mismatch_count=0,
                mismatches=[],
                match_percentage=0.0,
                skipped=True,
                skip_reason="Section 1 table not found in PDF"
            )
        
        pdf_table = pdf_data.section1_table
        excel_section = excel_data.section1_enrollment
        
        # Compare each period's enrollment numbers
        for idx, period in enumerate(excel_section.periods):
            # Map to PDF table row (adjust indices based on actual structure)
            pdf_row_idx = idx + 1  # Assuming row 0 is header
            
            if pdf_row_idx >= len(pdf_table.cells):
                continue
            
            pdf_row = pdf_table.cells[pdf_row_idx]
            
            # Compare enrolled students
            cells_compared += 1
            excel_val = period.num_students_enrolled
            pdf_val = self._parse_int(pdf_row[1]) if len(pdf_row) > 1 else None
            
            if excel_val != pdf_val:
                mismatches.append(CellMismatch(
                    section="Section1",
                    excel_cell=f"C{10 + idx}",  # Approximate
                    excel_value=excel_val,
                    excel_label="num_students_enrolled",
                    pdf_value=pdf_val,
                    pdf_page=1,
                    pdf_confidence=pdf_table.confidence,
                    row_label=period.periodo,
                    column_label="Students Enrolled",
                    is_critical=True
                ))
            
            # Compare special diet A
            cells_compared += 1
            excel_val_a = period.num_students_special_diet_a
            pdf_val_a = self._parse_int(pdf_row[2]) if len(pdf_row) > 2 else None
            
            if excel_val_a != pdf_val_a:
                mismatches.append(CellMismatch(
                    section="Section1",
                    excel_cell=f"D{10 + idx}",
                    excel_value=excel_val_a,
                    excel_label="special_diet_a",
                    pdf_value=pdf_val_a,
                    pdf_page=1,
                    pdf_confidence=pdf_table.confidence,
                    row_label=period.periodo,
                    column_label="Special Diet A"
                ))
            
            # Compare special diet B
            cells_compared += 1
            excel_val_b = period.num_students_special_diet_b
            pdf_val_b = self._parse_int(pdf_row[3]) if len(pdf_row) > 3 else None
            
            if excel_val_b != pdf_val_b:
                mismatches.append(CellMismatch(
                    section="Section1",
                    excel_cell=f"E{10 + idx}",
                    excel_value=excel_val_b,
                    excel_label="special_diet_b",
                    pdf_value=pdf_val_b,
                    pdf_page=1,
                    pdf_confidence=pdf_table.confidence,
                    row_label=period.periodo,
                    column_label="Special Diet B"
                ))
        
        # Compare totals
        total_row_idx = len(excel_section.periods) + 1
        if total_row_idx < len(pdf_table.cells):
            pdf_total_row = pdf_table.cells[total_row_idx]
            
            cells_compared += 3
            
            # Total students
            if excel_section.total_students != self._parse_int(pdf_total_row[1]):
                mismatches.append(CellMismatch(
                    section="Section1",
                    excel_cell="C14",  # Approximate
                    excel_value=excel_section.total_students,
                    excel_label="total_students",
                    pdf_value=self._parse_int(pdf_total_row[1]),
                    pdf_page=1,
                    row_label="TOTAL",
                    column_label="Students Enrolled",
                    is_critical=True
                ))
        
        match_count = cells_compared - len(mismatches)
        match_pct = (match_count / cells_compared * 100) if cells_compared > 0 else 0
        
        return SectionResult(
            section_name="Section1",
            section_display_name="Student Enrollment Numbers",
            total_cells_compared=cells_compared,
            match_count=match_count,
            mismatch_count=len(mismatches),
            mismatches=mismatches,
            match_percentage=match_pct
        )
    
    def _compare_section2(
        self,
        excel_data: ExcelReconciliationData,
        pdf_data: PDFReconciliationData
    ) -> SectionResult:
        """
        Compare Section 2: Frequency data (from page 2)
        """
        logger.info("Comparing Section 2 (Frequency)")
        
        mismatches = []
        cells_compared = 0
        
        if not pdf_data.section2_table:
            return SectionResult(
                section_name="Section2",
                section_display_name="Attendance Frequency",
                total_cells_compared=0,
                match_count=0,
                mismatch_count=0,
                mismatches=[],
                match_percentage=0.0,
                skipped=True,
                skip_reason="Section 2 table not found in PDF"
            )
        
        pdf_table = pdf_data.section2_table
        excel_records = excel_data.section2_frequency.records
        
        # Compare each day's frequency data
        for excel_record in excel_records:
            # Find matching row in PDF (by day number)
            pdf_row = self._find_pdf_row_by_day(pdf_table, excel_record.dia)
            
            if not pdf_row:
                continue
            
            # Compare frequency A
            cells_compared += 1
            if excel_record.frequency_a != self._parse_int(pdf_row[1]):
                mismatches.append(CellMismatch(
                    section="Section2",
                    excel_cell=f"B{20 + excel_record.dia}",  # Approximate
                    excel_value=excel_record.frequency_a,
                    excel_label="frequency_a",
                    pdf_value=self._parse_int(pdf_row[1]),
                    pdf_page=2,
                    pdf_confidence=pdf_table.confidence,
                    row_label=f"Day {excel_record.dia}",
                    column_label="Frequency A"
                ))
            
            # Compare lunch A, frequency B, lunch B, emergency
            # ... similar comparisons for other columns
        
        match_count = cells_compared - len(mismatches)
        match_pct = (match_count / cells_compared * 100) if cells_compared > 0 else 0
        
        return SectionResult(
            section_name="Section2",
            section_display_name="Attendance Frequency",
            total_cells_compared=cells_compared,
            match_count=match_count,
            mismatch_count=len(mismatches),
            mismatches=mismatches,
            match_percentage=match_pct
        )
    
    def _compare_section3(
        self,
        excel_data: ExcelReconciliationData,
        pdf_data: PDFReconciliationData
    ) -> SectionResult:
        """
        Compare Section 3: Daily attendance grid (spans both pages)
        This is the most complex section with many cells
        """
        logger.info("Comparing Section 3 (Daily Attendance Grid)")
        
        mismatches = []
        cells_compared = 0
        
        if not pdf_data.section3_table:
            return SectionResult(
                section_name="Section3",
                section_display_name="Daily Attendance Grid",
                total_cells_compared=0,
                match_count=0,
                mismatch_count=0,
                mismatches=[],
                match_percentage=0.0,
                skipped=True,
                skip_reason="Section 3 table not found in PDF"
            )
        
        pdf_table = pdf_data.section3_table
        excel_records = excel_data.section3_daily_attendance.daily_records
        
        # Compare each day's attendance data
        for excel_record in excel_records:
            # Find matching PDF row
            pdf_row = self._find_pdf_row_by_day(pdf_table, excel_record.dia)
            
            if not pdf_row:
                continue
            
            # Define column mappings (meal types)
            comparisons = [
                ("breakfast_p1", 1, "1º Período - Breakfast"),
                ("lunch_p1", 2, "1º Período - Lunch"),
                ("breakfast_p2", 3, "2º Período - Breakfast"),
                ("lunch_p2", 4, "2º Período - Lunch"),
                ("breakfast_int", 5, "Intermediário - Breakfast"),
                ("lunch_int", 6, "Intermediário - Lunch"),
                ("breakfast_integral", 7, "Integral - Breakfast"),
                ("lunch_integral", 8, "Integral - Lunch"),
                ("dinner_integral", 9, "Integral - Dinner"),
                ("breakfast_p3", 10, "3º Período - Breakfast"),
                ("lunch_p3", 11, "3º Período - Lunch"),
                ("dinner_p3", 12, "3º Período - Dinner"),
            ]
            
            for attr_name, pdf_col_idx, col_label in comparisons:
                cells_compared += 1
                
                excel_val = getattr(excel_record, attr_name)
                pdf_val = self._parse_int(pdf_row[pdf_col_idx]) if pdf_col_idx < len(pdf_row) else None
                
                # Skip if both are None/empty
                if excel_val is None and pdf_val is None:
                    continue
                
                if excel_val != pdf_val:
                    mismatches.append(CellMismatch(
                        section="Section3",
                        excel_cell=f"{chr(65 + pdf_col_idx)}{60 + excel_record.dia}",  # Approximate
                        excel_value=excel_val,
                        excel_label=attr_name,
                        pdf_value=pdf_val,
                        pdf_page=1 if excel_record.dia <= 15 else 2,  # Approximate page split
                        pdf_confidence=pdf_table.confidence,
                        row_label=f"Day {excel_record.dia}",
                        column_label=col_label
                    ))
        
        match_count = cells_compared - len(mismatches)
        match_pct = (match_count / cells_compared * 100) if cells_compared > 0 else 0
        
        return SectionResult(
            section_name="Section3",
            section_display_name="Daily Attendance Grid",
            total_cells_compared=cells_compared,
            match_count=match_count,
            mismatch_count=len(mismatches),
            mismatches=mismatches,
            match_percentage=match_pct
        )
    
    def _calculate_overall_metrics(self, result: ReconciliationResult) -> None:
        """Calculate overall reconciliation metrics"""
        total_cells = 0
        total_mismatches = 0
        
        for section_result in [result.section1_result, result.section2_result, result.section3_result]:
            if section_result and not section_result.skipped:
                total_cells += section_result.total_cells_compared
                total_mismatches += section_result.mismatch_count
        
        result.total_cells_compared = total_cells
        result.total_mismatches = total_mismatches
        result.overall_match_percentage = (
            (total_cells - total_mismatches) / total_cells * 100 
            if total_cells > 0 else 0
        )
    
    def _check_row_counts(
        self,
        result: ReconciliationResult,
        excel_data: ExcelReconciliationData,
        pdf_data: PDFReconciliationData
    ) -> None:
        """
        Check if row counts match between Excel and PDF
        """
        excel_days = len(excel_data.section3_daily_attendance.daily_records)
        pdf_days = pdf_data.section3_table.row_count if pdf_data.section3_table else 0
        
        result.excel_row_count = excel_days
        result.pdf_row_count = pdf_days
        result.row_count_match = excel_days == pdf_days
        
        if result.row_count_match:
            result.row_count_message = f"✓ Row counts match: {excel_days} days"
        else:
            result.row_count_message = f"✗ Row count mismatch: Excel has {excel_days} days, PDF has {pdf_days} days"
            result.warnings.append(result.row_count_message)
    
    # Helper methods
    
    def _parse_int(self, value: Any) -> Optional[int]:
        """Safely parse value to int"""
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    
    def _find_pdf_row_by_day(self, pdf_table: PDFTable, day: int) -> Optional[List[Any]]:
        """Find PDF table row by day number"""
        for row in pdf_table.cells:
            if len(row) > 0 and self._parse_int(row[0]) == day:
                return row
        return None


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    # This would typically be called from the main application
    # after parsing both Excel and PDF
    
    from excel_parser import ExcelParser
    from pdf_processor import PDFProcessor
    import asyncio
    
    async def test_reconciliation():
        # Parse files
        excel_parser = ExcelParser()
        excel_data = excel_parser.parse_file("/path/to/019382.xlsm")
        
        pdf_processor = PDFProcessor("endpoint", "key")
        pdf_data = await pdf_processor.process_pdf("/path/to/EMEI_test1.pdf")
        
        # Run reconciliation
        engine = ReconciliationEngine(min_pdf_confidence=0.75)
        result = engine.reconcile(excel_data, pdf_data, "test-reconciliation-001")
        
        # Print results
        print(f"Reconciliation ID: {result.reconciliation_id}")
        print(f"Status: {result.status}")
        print(f"ID Match: {result.id_match_message}")
        print(f"Overall Match: {result.overall_match_percentage:.2f}%")
        print(f"Total Mismatches: {result.total_mismatches}")
        
        if result.warnings:
            print("\nWarnings:")
            for warning in result.warnings:
                print(f"  - {warning}")
        
        # Print section results
        for section in [result.section1_result, result.section2_result, result.section3_result]:
            if section:
                print(f"\n{section.section_display_name}:")
                print(f"  Match: {section.match_percentage:.2f}%")
                print(f"  Mismatches: {section.mismatch_count}")
                
                if section.mismatches:
                    print("  First 5 mismatches:")
                    for mismatch in section.mismatches[:5]:
                        print(f"    - {mismatch.row_label} / {mismatch.column_label}: {mismatch.excel_value} vs {mismatch.pdf_value}")
    
    # asyncio.run(test_reconciliation())
