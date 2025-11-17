"""
Comprehensive Reconciliation Engine
Cell-by-cell comparison across all sections
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import logging
import base64
import io
import fitz  # PyMuPDF
from PIL import Image
import os
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

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
    excel_cell_ref: Optional[str] = None  # e.g., "B5", "D12"
    pdf_image_base64: Optional[str] = None  # Base64 encoded image of the PDF cell
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
        self._azure_di_cache = {}  # Cache for Azure DI table analysis results

        # Excel cell mappings for Section 1 (Enrollment)
        self.section1_rows = {
            "INTEGRAL": 15,
            "1º PERÍODO MATUTINO": 16,
            "2º PERÍODO INTERMEDIÁRIO": 17,
            "3º PERÍODO VESPERTINO": 18,
            "TOTAL": 20
        }
        self.section1_cols = {
            "Number of Students": 12,  # Column L
            "Special Diet A": 18,       # Column R
            "Special Diet B": 22        # Column V
        }

        # Excel cell mappings for Section 2 (Daily Frequency)
        self.section2_start_row = 28
        self.section2_total_row = 59
        self.section2_field_cols = {
            # INTEGRAL (11 fields) - cols E,G,H,J-Q (5,7,8,10-17)
            "INTEGRAL - Frequência": 5,
            "INTEGRAL - Lanche 4h": 7,
            "INTEGRAL - Lanche 6h": 8,
            "INTEGRAL - Refeição": 10,
            "INTEGRAL - Repetição Refeição": 11,
            "INTEGRAL - Sobremesa": 12,
            "INTEGRAL - Repetição Sobremesa": 13,
            "INTEGRAL - 2ª Refeição": 14,
            "INTEGRAL - Repetição 2ª Refeição": 15,
            "INTEGRAL - 2ª Sobremesa": 16,
            "INTEGRAL - Repetição 2ª Sobremesa": 17,
            # P1 (7 fields) - cols R,T,U,X,AB,AE,AI (18,20,21,24,28,31,35)
            "P1 - Frequência": 18,
            "P1 - Lanche 4h": 20,
            "P1 - Lanche 6h": 21,
            "P1 - Refeição": 24,
            "P1 - Repetição Refeição": 28,
            "P1 - Sobremesa": 31,
            "P1 - Repetição Sobremesa": 35,
            # INTERMEDIÁRIO (6 fields) - cols AK,AL,AM,AO,AQ,AS (37,38,39,41,43,45)
            "INTERMEDIÁRIO - Frequência": 37,
            "INTERMEDIÁRIO - Lanche 4h": 38,
            "INTERMEDIÁRIO - Refeição": 39,
            "INTERMEDIÁRIO - Repetição Refeição": 41,
            "INTERMEDIÁRIO - Sobremesa": 43,
            "INTERMEDIÁRIO - Repetição Sobremesa": 45,
            # P3 (7 fields) - cols AU,AW,AY,BE,BI,BJ,BQ (47,49,51,57,61,62,69)
            "P3 - Frequência": 47,
            "P3 - Lanche 4h": 49,
            "P3 - Lanche 6h": 51,
            "P3 - Refeição": 57,
            "P3 - Repetição Refeição": 61,
            "P3 - Sobremesa": 62,
            "P3 - Repetição Sobremesa": 69,
            # DOCE checkboxes - cols (need to verify exact columns)
            "DOCE - INTEGRAL": 72,
            "DOCE - P1": 73,
            "DOCE - INTERMEDIÁRIO": 74,
            "DOCE - P3": 75,
        }

        # Excel cell mappings for Section 3 (Special Diet Data)
        self.section3_start_row = 77
        self.section3_total_row = 108
        self.section3_field_cols = {
            "Group A - Frequência": 3,
            "Group A - Lanche 4h": 4,
            "Group A - Lanche 6h": 6,
            "Group A - Refeição Enteral": 8,
            "Group B - Frequência": 11,
            "Group B - Lanche 4h": 13,
            "Group B - Lanche 6h": 15,
            "Lanche Emergencial": 17,
            "Kit Lanche": 19,
            "Observações": 21,
        }

    def _col_num_to_letter(self, col_num: int) -> str:
        """Convert column number (1-indexed) to Excel column letter (A, B, ... Z, AA, AB, ...)"""
        result = ""
        while col_num > 0:
            col_num -= 1
            result = chr(65 + (col_num % 26)) + result
            col_num //= 26
        return result

    def _get_excel_cell_ref(self, section: str, field: str, row_identifier: str) -> Optional[str]:
        """
        Generate Excel cell reference (e.g., "L15", "E28", "AB32")

        Args:
            section: "Section1", "Section2", "Section3", "Header"
            field: Field name (e.g., "Number of Students", "INTEGRAL - Frequência")
            row_identifier: Row identifier (e.g., "INTEGRAL", "Day 1", "TOTAL")

        Returns:
            Excel cell reference string (e.g., "L15") or None if mapping not found
        """
        try:
            if section == "Header":
                # Header EMEI code is typically in a specific cell, but we don't have exact mapping
                return None

            elif section == "Section1":
                # Get row number from period name
                row = self.section1_rows.get(row_identifier)
                if not row:
                    return None

                # Get column number from field name
                col = self.section1_cols.get(field)
                if not col:
                    return None

                return f"{self._col_num_to_letter(col)}{row}"

            elif section == "Section2":
                # Parse day number from row_identifier (e.g., "Day 1" -> 1)
                if row_identifier == "TOTAL":
                    row = self.section2_total_row
                elif row_identifier.startswith("Day "):
                    day = int(row_identifier.split()[1])
                    row = self.section2_start_row + (day - 1)
                else:
                    return None

                # Get column number from field name
                col = self.section2_field_cols.get(field)
                if not col:
                    return None

                return f"{self._col_num_to_letter(col)}{row}"

            elif section == "Section3":
                # Parse day number from row_identifier
                if row_identifier == "TOTAL":
                    row = self.section3_total_row
                elif row_identifier.startswith("Day "):
                    day = int(row_identifier.split()[1])
                    row = self.section3_start_row + (day - 1)
                else:
                    return None

                # Get column number from field name
                col = self.section3_field_cols.get(field)
                if not col:
                    return None

                return f"{self._col_num_to_letter(col)}{row}"

            return None

        except Exception as e:
            logger.warning(f"Error generating Excel cell reference: {e}")
            return None

    def _find_table_by_section(self, tables, section: str):
        """
        Find the correct table for a section by examining header content
        instead of relying on fixed table indices.

        Section1: Has headers like "ALUNOS MATRICULADOS"
        Section2: Has headers like "Frequência", "Lanche", "Refeição"
        Section3: Has headers like "DIETA A", "DIETA B"
        """
        for table in tables:
            # Get all cell contents from first few rows (headers)
            header_content = []
            for cell in table.cells:
                if cell.row_index <= 2:  # Check first 3 rows
                    header_content.append(str(cell.content).upper())

            header_text = " ".join(header_content)

            if section == "Section1":
                # Section1 has period names: INTEGRAL, 1º PERÍODO, etc.
                if "INTEGRAL" in header_text and ("PERÍODO" in header_text or "PERIODO" in header_text):
                    logger.info(f"Found Section1 table (table index {tables.index(table)})")
                    return table

            elif section == "Section2":
                # Section2 has "Dias" in first cell AND meal columns: Frequência, Lanche, Refeição
                has_dias = False
                for cell in table.cells:
                    if cell.row_index == 0 and cell.column_index == 0:
                        if "DIAS" in str(cell.content).upper():
                            has_dias = True
                            break

                if has_dias and \
                   ("FREQUÊNCIA" in header_text or "FREQUENCIA" in header_text) and \
                   "LANCHE" in header_text and \
                   ("REFEIÇÃO" in header_text or "REFEICAO" in header_text):
                    logger.info(f"Found Section2 table (table index {tables.index(table)})")
                    return table

            elif section == "Section3":
                # Section3 has "Dias" in first cell AND diet columns with "DIETA A", "DIETA B"
                has_dias = False
                for cell in table.cells:
                    if cell.row_index == 0 and cell.column_index == 0:
                        if "DIAS" in str(cell.content).upper():
                            has_dias = True
                            break

                if has_dias and "DIETA" in header_text and \
                   ("DIETA A" in header_text or "DIET A" in header_text):
                    logger.info(f"Found Section3 table (table index {tables.index(table)})")
                    return table

        return None

    def _find_cell_coordinates_from_azure(self, pdf_path: str, section: str, row_identifier: str, field: str) -> Optional[tuple]:
        """
        Use Azure Document Intelligence to find exact cell coordinates
        Uses caching to avoid re-analyzing the same PDF multiple times.

        Returns:
            Tuple of (x0, y0, x1, y1) in page coordinates, or None if not found
        """
        try:
            # Check cache first
            if pdf_path not in self._azure_di_cache:
                # Initialize Azure DI client
                endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
                key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

                if not endpoint or not key:
                    logger.warning("Azure DI credentials not found")
                    return None

                logger.info(f"Analyzing PDF with Azure DI (not in cache): {pdf_path}")
                client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))

                # Analyze document with prebuilt-layout model
                with open(pdf_path, "rb") as f:
                    poller = client.begin_analyze_document("prebuilt-layout", analyze_request=f, content_type="application/pdf")
                    result = poller.result()

                if not result.tables:
                    logger.warning("No tables found in PDF")
                    return None

                # Cache the result
                self._azure_di_cache[pdf_path] = result
                logger.info(f"Cached Azure DI result for {pdf_path}")
            else:
                logger.info(f"Using cached Azure DI result for {pdf_path}")
                result = self._azure_di_cache[pdf_path]

            if not result.tables:
                logger.warning("No tables found in PDF")
                return None

            # Find the correct table by examining content instead of using fixed indices
            table = self._find_table_by_section(result.tables, section)

            if table is None:
                logger.warning(f"Table not found for {section}")
                return None

            # Log table info for debugging
            logger.info(f"Table for {section} has {len([c for c in table.cells if c.row_index == 0])} cells in row 0, {len([c for c in table.cells if c.column_index == 0])} cells in col 0")

            # Find the cell that matches our row and field
            target_cell = self._find_matching_cell(table, section, row_identifier, field)

            if not target_cell:
                logger.warning(f"Cell not found for {section}, {row_identifier}, {field}")
                return None

            # Get bounding polygon (normalized coordinates)
            if not target_cell.bounding_regions or not target_cell.bounding_regions[0].polygon:
                logger.warning("Cell has no bounding region")
                return None

            polygon = target_cell.bounding_regions[0].polygon

            # Polygon is a list of points: [x1, y1, x2, y2, x3, y3, x4, y4]
            # Extract min/max to get bounding box
            x_coords = [polygon[i] for i in range(0, len(polygon), 2)]
            y_coords = [polygon[i] for i in range(1, len(polygon), 2)]

            return (min(x_coords), min(y_coords), max(x_coords), max(y_coords))

        except Exception as e:
            logger.warning(f"Error finding cell coordinates from Azure: {e}")
            return None

    def _find_matching_cell(self, table, section: str, row_identifier: str, field: str) -> Optional[Any]:
        """
        Find the cell in the Azure DI table that matches our field and row

        Strategy:
        1. Parse the row identifier to find the row index
        2. Map the field name to find the column index
        3. Return the cell at that position
        """
        try:
            # Find row index based on row_identifier
            target_row = None

            if section == "Section1":
                # Section 1: Match by period name
                for cell in table.cells:
                    if cell.column_index == 0:  # First column has period names
                        cell_content = str(cell.content).strip().upper()
                        if row_identifier.upper() in cell_content or cell_content in row_identifier.upper():
                            target_row = cell.row_index
                            break

            elif section in ["Section2", "Section3"]:
                # Section 2 & 3: Match by day number
                if "Day " in row_identifier:
                    day_num = int(row_identifier.split()[1])
                    # Find the row where first column contains this day number
                    logger.info(f"Looking for day {day_num} in {section}")
                    day_cells_found = []
                    all_col0_cells = []  # Track ALL column 0 cells for debugging

                    # DEBUG: Log first 20 cells with their positions
                    first_cells = []
                    for idx, cell in enumerate(list(table.cells)[:20]):
                        first_cells.append(f"Cell[{cell.row_index},{cell.column_index}]='{cell.content}'")
                    logger.info(f"First 20 cells: {first_cells}")

                    for cell in table.cells:
                        if cell.column_index == 0:  # Day column
                            all_col0_cells.append(f"Row {cell.row_index}: '{cell.content}'")
                            try:
                                cell_day = int(str(cell.content).strip())
                                day_cells_found.append(f"Row {cell.row_index}: {cell_day}")
                                if cell_day == day_num:
                                    target_row = cell.row_index
                                    logger.info(f"Found day {day_num} at row {cell.row_index}")
                                    break
                            except (ValueError, AttributeError):
                                continue
                    if target_row is None:
                        logger.warning(f"Day {day_num} not found. All column 0 cells: {all_col0_cells[:15]}")
                        logger.warning(f"Parseable day cells: {day_cells_found[:10]}")
                elif "TOTAL" in row_identifier:
                    # Find TOTAL row
                    for cell in table.cells:
                        if cell.column_index == 0:
                            if "TOTAL" in str(cell.content).upper():
                                target_row = cell.row_index
                                break

            if target_row is None:
                logger.warning(f"Could not find row for {row_identifier}")
                return None

            # Find column index based on field name
            target_col = self._find_column_for_field(table, section, field)

            if target_col is None:
                logger.warning(f"Could not find column for {field}")
                return None

            # Find the cell at (target_row, target_col)
            for cell in table.cells:
                if cell.row_index == target_row and cell.column_index == target_col:
                    return cell

            return None

        except Exception as e:
            logger.warning(f"Error finding matching cell: {e}")
            return None

    def _find_column_for_field(self, table, section: str, field: str) -> Optional[int]:
        """
        Find the column index for a given field name by matching header content
        """
        try:
            field_upper = field.upper()

            # Search through header rows (usually rows 0-2) to find column with matching content
            for cell in table.cells:
                if cell.row_index <= 2:  # Check header rows
                    cell_content = str(cell.content).strip().upper()

                    # Match based on key terms in the field name
                    if "FREQUÊNCIA" in field_upper or "FREQUENCIA" in field_upper:
                        if "FREQUÊNCIA" in cell_content or "FREQUENCIA" in cell_content:
                            return cell.column_index
                    elif "LANCHE 4H" in field_upper or "LANCHE (4H)" in field_upper:
                        if "4H" in cell_content and "LANCHE" in cell_content:
                            return cell.column_index
                    elif "LANCHE 6H" in field_upper or "LANCHE (6H)" in field_upper:
                        if "6H" in cell_content and "LANCHE" in cell_content:
                            return cell.column_index
                    elif "REFEIÇÃO" in field_upper and "REPETIÇÃO" not in field_upper and "2ª" not in field_upper:
                        if "REFEIÇÃO" in cell_content and "REPETIÇÃO" not in cell_content and "2A" not in cell_content:
                            return cell.column_index
                    elif "REPETIÇÃO REFEIÇÃO" in field_upper and "2ª" not in field_upper:
                        if "REPETIÇÃO" in cell_content and "REFEIÇÃO" in cell_content and "2A" not in cell_content:
                            return cell.column_index
                    elif "SOBREMESA" in field_upper and "REPETIÇÃO" not in field_upper and "2ª" not in field_upper:
                        if "SOBREMESA" in cell_content and "REPETIÇÃO" not in cell_content and "2A" not in cell_content:
                            return cell.column_index
                    elif "REPETIÇÃO SOBREMESA" in field_upper and "2ª" not in field_upper:
                        if "REPETIÇÃO" in cell_content and "SOBREMESA" in cell_content and "2A" not in cell_content:
                            return cell.column_index
                    elif "2ª REFEIÇÃO" in field_upper and "REPETIÇÃO" not in field_upper:
                        if "2A" in cell_content and "REFEIÇÃO" in cell_content and "REPETIÇÃO" not in cell_content:
                            return cell.column_index
                    elif "REPETIÇÃO 2ª REFEIÇÃO" in field_upper or "2ª REFEIÇÃO" in field_upper and "REPETIÇÃO" in field_upper:
                        if "2A" in cell_content and "REFEIÇÃO" in cell_content and "REPETIÇÃO" in cell_content:
                            return cell.column_index
                    elif "2ª SOBREMESA" in field_upper and "REPETIÇÃO" not in field_upper:
                        if "2A" in cell_content and "SOBREMESA" in cell_content and "REPETIÇÃO" not in cell_content:
                            return cell.column_index
                    elif "REPETIÇÃO 2ª SOBREMESA" in field_upper or "2ª SOBREMESA" in field_upper and "REPETIÇÃO" in field_upper:
                        if "2A" in cell_content and "SOBREMESA" in cell_content and "REPETIÇÃO" in cell_content:
                            return cell.column_index
                    elif "STUDENTS" in field_upper or "ALUNOS" in field_upper:
                        if "ALUNOS" in cell_content or "MATRÍCULA" in cell_content:
                            return cell.column_index
                    elif "DIET A" in field_upper or "DIETA A" in field_upper:
                        if "DIETA" in cell_content and "A" in cell_content:
                            return cell.column_index
                    elif "DIET B" in field_upper or "DIETA B" in field_upper:
                        if "DIETA" in cell_content and "B" in cell_content:
                            return cell.column_index
                    elif "DOCE" in field_upper:
                        if "DOCE" in cell_content:
                            return cell.column_index

            return None

        except Exception as e:
            logger.warning(f"Error finding column for field: {e}")
            return None

    def _extract_cell_image(self, pdf_path: str, section: str, row_identifier: str, field: str) -> Optional[str]:
        """
        Extract PDF section table image with highlighted cell (yellow box around specific cell)
        Uses Azure Document Intelligence to find exact cell coordinates.

        Args:
            pdf_path: Path to the PDF file
            section: Section name (Section1, Section2, Section3)
            row_identifier: Row identifier (e.g., "Day 1", "INTEGRAL")
            field: Field name

        Returns:
            Base64 encoded PNG image of section table with highlighted cell or None if extraction fails
        """
        try:
            # Get exact cell coordinates from Azure DI
            cell_coords = self._find_cell_coordinates_from_azure(pdf_path, section, row_identifier, field)

            if not cell_coords:
                logger.warning(f"Could not find cell coordinates for {section}, {row_identifier}, {field}")
                return None

            # Open PDF
            doc = fitz.open(pdf_path)
            page_num = 0
            page = doc[page_num]

            # Get page dimensions
            page_rect = page.rect
            page_width = page_rect.width
            page_height = page_rect.height

            # Use Azure coordinates
            cell_x0, cell_y0, cell_x1, cell_y1 = cell_coords

            # Expand section_rect to show context around the cell
            padding = min(page_width, page_height) * 0.15  # 15% padding
            section_rect = fitz.Rect(
                max(0, cell_x0 - padding),
                max(0, cell_y0 - padding),
                min(page_width, cell_x1 + padding),
                min(page_height, cell_y1 + padding)
            )

            # Render the section with high resolution
            mat = fitz.Matrix(3.0, 3.0)  # 3x zoom for clear view
            pix = page.get_pixmap(matrix=mat, clip=section_rect)

            # Convert pixmap to PIL Image so we can draw on it
            img = Image.open(io.BytesIO(pix.tobytes("png")))

            # Create a drawing context
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img, 'RGBA')

            # Calculate cell position in the rendered image coordinates
            # (need to adjust for section_rect offset and zoom)
            highlight_x0 = (cell_x0 - section_rect.x0) * mat.a
            highlight_y0 = (cell_y0 - section_rect.y0) * mat.d
            highlight_x1 = (cell_x1 - section_rect.x0) * mat.a
            highlight_y1 = (cell_y1 - section_rect.y0) * mat.d

            # Draw yellow highlight box around the cell (semi-transparent fill + bright border)
            draw.rectangle(
                [highlight_x0, highlight_y0, highlight_x1, highlight_y1],
                outline=(255, 215, 0, 255),  # Gold/yellow border - fully opaque
                fill=(255, 255, 0, 80),      # Yellow fill - semi-transparent
                width=4
            )

            # Convert back to PNG bytes
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_bytes = img_buffer.getvalue()

            # Encode as base64
            img_base64 = base64.b64encode(img_bytes).decode('utf-8')

            doc.close()

            return f"data:image/png;base64,{img_base64}"

        except Exception as e:
            logger.warning(f"Error extracting PDF cell image with highlight: {e}")
            return None

    def reconcile(
        self,
        excel_data: ExcelReconciliationData,
        pdf_data: PDFReconciliationData,
        reconciliation_id: str,
        pdf_path: Optional[str] = None
    ) -> ReconciliationResult:
        """
        Main reconciliation method with comprehensive comparison
        """
        logger.info(f"Starting comprehensive reconciliation for {reconciliation_id}")

        # Store pdf_path for helper methods to access
        self.pdf_path = pdf_path

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
                excel_cell_ref=self._get_excel_cell_ref("Header", "EMEI Code", "Header"),
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
                    excel_cell_ref=self._get_excel_cell_ref("Section1", "Number of Students", excel_period.period_name),
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
                    excel_cell_ref=self._get_excel_cell_ref("Section1", "Number of Students", excel_period.period_name),
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
                    excel_cell_ref=self._get_excel_cell_ref("Section1", "Special Diet A", excel_period.period_name),
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
                    excel_cell_ref=self._get_excel_cell_ref("Section1", "Special Diet B", excel_period.period_name),
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
                    excel_cell_ref=self._get_excel_cell_ref("Section1", "Number of Students", "TOTAL"),
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
                    excel_cell_ref=self._get_excel_cell_ref("Section1", "Special Diet A", "TOTAL"),
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
                    excel_cell_ref=self._get_excel_cell_ref("Section1", "Special Diet B", "TOTAL"),
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
            row_id = f"Day {day}"

            # Extract PDF cell image if pdf_path is available
            pdf_image = None
            if self.pdf_path:
                pdf_image = self._extract_cell_image(self.pdf_path, section, row_id, field)

            mismatches.append(CellMismatch(
                section=section,
                field=field,
                row_identifier=row_id,
                excel_value=excel_val,
                pdf_value=pdf_val,
                excel_cell_ref=self._get_excel_cell_ref(section, field, row_id),
                pdf_image_base64=pdf_image,
                description=f"{field} mismatch for day {day}"
            ))

    def _compare_checkbox(self, excel_val, pdf_val, section, field, day, mismatches, cells_compared):
        """Helper to compare checkbox fields (True/False/None)"""
        cells_compared[0] += 1

        # Normalize: None and False are equivalent for checkboxes
        excel_norm = excel_val if excel_val else False
        pdf_norm = pdf_val if pdf_val else False

        if excel_norm != pdf_norm:
            row_id = f"Day {day}"

            # Extract PDF cell image if pdf_path is available
            pdf_image = None
            if self.pdf_path:
                pdf_image = self._extract_cell_image(self.pdf_path, section, row_id, field)

            mismatches.append(CellMismatch(
                section=section,
                field=field,
                row_identifier=row_id,
                excel_value=excel_val,
                pdf_value=pdf_val,
                excel_cell_ref=self._get_excel_cell_ref(section, field, row_id),
                pdf_image_base64=pdf_image,
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
                row_id = f"Day {day}"
                mismatches.append(CellMismatch(
                    section="Section3",
                    field="Observações",
                    row_identifier=row_id,
                    excel_value=excel_obs,
                    pdf_value=pdf_obs,
                    excel_cell_ref=self._get_excel_cell_ref("Section3", "Observações", row_id),
                    description=f"Observações mismatch for day {day}"
                ))

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
