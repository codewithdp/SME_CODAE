"""
Excel Parser Module for Reconciliation System
Extracts structured data from EMEI Excel sheets
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
import openpyxl
from openpyxl.worksheet.worksheet import Worksheet
from pydantic import BaseModel, Field


# ============================================================================
# DATA MODELS
# ============================================================================

class HeaderData(BaseModel):
    """Header section data from Excel"""
    emei_code: str
    emei_name: str
    ceu_emei: str
    alto_alegre: str
    email: str
    cep: str
    address: str
    empresa: str
    mes: str
    ano: str


class EnrollmentPeriod(BaseModel):
    """Student enrollment for a specific period"""
    periodo: str
    num_students_enrolled: int
    num_students_special_diet_a: int  # COM DIETA ESPECIAL - A
    num_students_special_diet_b: int  # COM DIETA ESPECIAL - B


class Section1Data(BaseModel):
    """Section 1: Student enrollment numbers"""
    periods: List[EnrollmentPeriod]
    total_students: int
    total_special_diet_a: int
    total_special_diet_b: int


class FrequencyRecord(BaseModel):
    """Daily frequency record for Section 2"""
    dia: int
    frequency_a: Optional[int] = None
    lunch_a: Optional[int] = None
    frequency_b: Optional[int] = None
    lunch_b: Optional[int] = None
    lunch_emergency: Optional[int] = None


class Section2Data(BaseModel):
    """Section 2: Frequency data (from page 2 of PDF)"""
    records: List[FrequencyRecord]


class DailyAttendanceRow(BaseModel):
    """Single day's attendance across all meal types"""
    dia: int
    
    # 1º PERÍODO
    breakfast_p1: Optional[int] = None
    lunch_p1: Optional[int] = None
    
    # 2º PERÍODO  
    breakfast_p2: Optional[int] = None
    lunch_p2: Optional[int] = None
    
    # INTERMEDIÁRIO
    breakfast_int: Optional[int] = None
    lunch_int: Optional[int] = None
    
    # INTEGRAL
    breakfast_integral: Optional[int] = None
    lunch_integral: Optional[int] = None
    dinner_integral: Optional[int] = None
    
    # 3º PERÍODO (NOTURNO)
    breakfast_p3: Optional[int] = None
    lunch_p3: Optional[int] = None
    dinner_p3: Optional[int] = None
    
    # Flags for special situations
    has_observation: bool = False
    observation_text: Optional[str] = None


class Section3Data(BaseModel):
    """Section 3: Daily attendance grid"""
    daily_records: List[DailyAttendanceRow]
    total_row: Optional[DailyAttendanceRow] = None


class ExcelReconciliationData(BaseModel):
    """Complete structured data from Excel file"""
    filename: str
    parsed_at: datetime = Field(default_factory=datetime.now)
    
    header: HeaderData
    section1_enrollment: Section1Data
    section2_frequency: Section2Data
    section3_daily_attendance: Section3Data
    
    # Metadata
    total_rows: int
    sheet_name: str
    
    # Cell coordinate mapping for reconciliation
    cell_coordinates: Dict[str, str] = Field(default_factory=dict)


# ============================================================================
# EXCEL PARSER CLASS
# ============================================================================

class ExcelParser:
    """
    Parses EMEI Excel files and extracts structured data
    """
    
    def __init__(self):
        self.workbook = None
        self.worksheet = None
        self.cell_map = {}
        
    def parse_file(self, file_path: str, sheet_name: str = "EMEI") -> ExcelReconciliationData:
        """
        Main parsing method
        
        Args:
            file_path: Path to Excel file
            sheet_name: Name of worksheet to parse
            
        Returns:
            ExcelReconciliationData object with all extracted data
        """
        self.workbook = openpyxl.load_workbook(file_path)
        self.worksheet = self.workbook[sheet_name]
        
        # Extract all sections
        header = self._extract_header()
        section1 = self._extract_section1_enrollment()
        section2 = self._extract_section2_frequency()
        section3 = self._extract_section3_daily_attendance()
        
        return ExcelReconciliationData(
            filename=file_path.split('/')[-1],
            header=header,
            section1_enrollment=section1,
            section2_frequency=section2,
            section3_daily_attendance=section3,
            total_rows=self.worksheet.max_row,
            sheet_name=sheet_name,
            cell_coordinates=self.cell_map
        )
    
    def _get_cell_value(self, cell_ref: str, label: str = None) -> Any:
        """
        Get cell value and track coordinate for reconciliation
        
        Args:
            cell_ref: Excel cell reference (e.g., "A1")
            label: Optional label for tracking (e.g., "emei_code")
        """
        value = self.worksheet[cell_ref].value
        if label:
            self.cell_map[label] = cell_ref
        return value
    
    def _extract_header(self) -> HeaderData:
        """
        Extract header information from top rows
        Based on the PDF structure showing:
        - Row 1-2: City/Department info
        - Row 3: CEU EMEI / ALTO ALEGRE
        - Row 4: Email
        - Row 5: CEP and Address
        - Row 6: Company name
        """
        # This is a template - adjust row/column positions based on actual Excel
        # You'll need to examine the actual Excel structure to set correct cells
        
        return HeaderData(
            emei_code=str(self._get_cell_value("B3", "header.emei_code") or ""),
            emei_name=str(self._get_cell_value("C3", "header.emei_name") or ""),
            ceu_emei=str(self._get_cell_value("D3", "header.ceu_emei") or ""),
            alto_alegre=str(self._get_cell_value("E3", "header.alto_alegre") or ""),
            email=str(self._get_cell_value("B4", "header.email") or ""),
            cep=str(self._get_cell_value("B5", "header.cep") or ""),
            address=str(self._get_cell_value("C5", "header.address") or ""),
            empresa=str(self._get_cell_value("B6", "header.empresa") or ""),
            mes=str(self._get_cell_value("F1", "header.mes") or "agosto"),
            ano=str(self._get_cell_value("F2", "header.ano") or "2025")
        )
    
    def _extract_section1_enrollment(self) -> Section1Data:
        """
        Extract Section 1: Student enrollment numbers
        
        From the PDF, this section shows:
        - INTEGRAL (4 a 6 horas): 225 students, 12 special diet A
        - PERÍODO MATUTINO (4 a 6 horas): XXX students
        - etc.
        - TOTAL row at bottom
        """
        periods = []
        
        # Define the rows where enrollment data is located
        # This is based on typical structure - adjust based on actual Excel
        enrollment_rows = [
            ("INTEGRAL (4 a 6 horas)", 10),
            ("PERÍODO MATUTINO", 11),
            ("PERÍODO INTERMEDIÁRIO", 12),
            ("PERÍODO VESPERTINO", 13),
        ]
        
        for period_name, row_num in enrollment_rows:
            num_enrolled = self._get_cell_value(
                f"C{row_num}", 
                f"section1.{period_name}.enrolled"
            )
            special_a = self._get_cell_value(
                f"D{row_num}", 
                f"section1.{period_name}.special_a"
            )
            special_b = self._get_cell_value(
                f"E{row_num}", 
                f"section1.{period_name}.special_b"
            )
            
            if num_enrolled is not None:
                periods.append(EnrollmentPeriod(
                    periodo=period_name,
                    num_students_enrolled=int(num_enrolled or 0),
                    num_students_special_diet_a=int(special_a or 0),
                    num_students_special_diet_b=int(special_b or 0)
                ))
        
        # Extract totals
        total_row = 14  # Adjust based on actual Excel
        total_students = int(self._get_cell_value(f"C{total_row}", "section1.total") or 0)
        total_special_a = int(self._get_cell_value(f"D{total_row}", "section1.total_special_a") or 0)
        total_special_b = int(self._get_cell_value(f"E{total_row}", "section1.total_special_b") or 0)
        
        return Section1Data(
            periods=periods,
            total_students=total_students,
            total_special_diet_a=total_special_a,
            total_special_diet_b=total_special_b
        )
    
    def _extract_section2_frequency(self) -> Section2Data:
        """
        Extract Section 2: Frequency data
        This corresponds to page 2 of the PDF
        Shows frequency by day with special diet groups A and B
        """
        records = []
        
        # Section 2 typically starts after Section 1
        # Adjust row numbers based on actual Excel layout
        start_row = 20
        end_row = 50  # Will be determined by finding empty rows
        
        for row_num in range(start_row, end_row):
            dia = self._get_cell_value(f"A{row_num}", f"section2.day_{row_num}")
            
            if dia is None or dia == "":
                break
                
            freq_a = self._get_cell_value(f"B{row_num}", f"section2.freq_a_{row_num}")
            lunch_a = self._get_cell_value(f"C{row_num}", f"section2.lunch_a_{row_num}")
            freq_b = self._get_cell_value(f"D{row_num}", f"section2.freq_b_{row_num}")
            lunch_b = self._get_cell_value(f"E{row_num}", f"section2.lunch_b_{row_num}")
            emergency = self._get_cell_value(f"F{row_num}", f"section2.emergency_{row_num}")
            
            records.append(FrequencyRecord(
                dia=int(dia),
                frequency_a=int(freq_a) if freq_a else None,
                lunch_a=int(lunch_a) if lunch_a else None,
                frequency_b=int(freq_b) if freq_b else None,
                lunch_b=int(lunch_b) if lunch_b else None,
                lunch_emergency=int(emergency) if emergency else None
            ))
        
        return Section2Data(records=records)
    
    def _extract_section3_daily_attendance(self) -> Section3Data:
        """
        Extract Section 3: Large daily attendance grid
        This is the main reconciliation table with days x meal types
        
        From PDF, columns include:
        - Day number
        - 1º PERÍODO: Breakfast, Lunch
        - 2º PERÍODO: Breakfast, Lunch  
        - INTERMEDIÁRIO: Breakfast, Lunch
        - INTEGRAL: Breakfast, Lunch, Dinner
        - 3º PERÍODO: Breakfast, Lunch, Dinner
        """
        daily_records = []
        
        # Section 3 typically starts after Section 2
        # Based on PDF, this appears to start around row 1 of the main grid
        # Adjust based on actual Excel structure
        start_row = 60
        max_days = 31  # Maximum days in a month
        
        for day_num in range(1, max_days + 1):
            row = start_row + day_num - 1
            
            # Check if day exists
            day_cell = self._get_cell_value(f"A{row}", f"section3.day_{day_num}")
            if day_cell is None or day_cell == "":
                break
            
            # Extract all meal columns
            # Column positions would need to be mapped from actual Excel
            record = DailyAttendanceRow(
                dia=int(day_cell),
                
                # 1º PERÍODO
                breakfast_p1=self._safe_int(self._get_cell_value(f"B{row}", f"s3.d{day_num}.bf_p1")),
                lunch_p1=self._safe_int(self._get_cell_value(f"C{row}", f"s3.d{day_num}.l_p1")),
                
                # 2º PERÍODO
                breakfast_p2=self._safe_int(self._get_cell_value(f"D{row}", f"s3.d{day_num}.bf_p2")),
                lunch_p2=self._safe_int(self._get_cell_value(f"E{row}", f"s3.d{day_num}.l_p2")),
                
                # INTERMEDIÁRIO
                breakfast_int=self._safe_int(self._get_cell_value(f"F{row}", f"s3.d{day_num}.bf_int")),
                lunch_int=self._safe_int(self._get_cell_value(f"G{row}", f"s3.d{day_num}.l_int")),
                
                # INTEGRAL
                breakfast_integral=self._safe_int(self._get_cell_value(f"H{row}", f"s3.d{day_num}.bf_integ")),
                lunch_integral=self._safe_int(self._get_cell_value(f"I{row}", f"s3.d{day_num}.l_integ")),
                dinner_integral=self._safe_int(self._get_cell_value(f"J{row}", f"s3.d{day_num}.d_integ")),
                
                # 3º PERÍODO
                breakfast_p3=self._safe_int(self._get_cell_value(f"K{row}", f"s3.d{day_num}.bf_p3")),
                lunch_p3=self._safe_int(self._get_cell_value(f"L{row}", f"s3.d{day_num}.l_p3")),
                dinner_p3=self._safe_int(self._get_cell_value(f"M{row}", f"s3.d{day_num}.d_p3")),
            )
            
            daily_records.append(record)
        
        # Extract total row if exists
        total_row_num = start_row + len(daily_records)
        total_row = None
        
        if self._get_cell_value(f"A{total_row_num}") == "Total":
            total_row = DailyAttendanceRow(
                dia=0,  # 0 indicates total row
                breakfast_p1=self._safe_int(self._get_cell_value(f"B{total_row_num}")),
                lunch_p1=self._safe_int(self._get_cell_value(f"C{total_row_num}")),
                # ... all other columns
            )
        
        return Section3Data(
            daily_records=daily_records,
            total_row=total_row
        )
    
    def _safe_int(self, value: Any) -> Optional[int]:
        """Safely convert value to int, return None if not possible"""
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    
    def get_cell_coordinate(self, label: str) -> Optional[str]:
        """Get Excel cell coordinate for a given data label"""
        return self.cell_map.get(label)


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    parser = ExcelParser()
    
    try:
        # Parse the Excel file
        data = parser.parse_file("/path/to/019382.xlsm", "EMEI")
        
        print(f"Parsed: {data.filename}")
        print(f"EMEI Code: {data.header.emei_code}")
        print(f"Total Students: {data.section1_enrollment.total_students}")
        print(f"Days with attendance: {len(data.section3_daily_attendance.daily_records)}")
        
        # Example: Get cell coordinate for a specific value
        total_cell = parser.get_cell_coordinate("section1.total")
        print(f"Total students found in cell: {total_cell}")
        
    except Exception as e:
        print(f"Error parsing Excel: {e}")
        import traceback
        traceback.print_exc()
