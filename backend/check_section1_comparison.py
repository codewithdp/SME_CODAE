"""
Check what Section 1 periods are being extracted and compared
"""

from app.excel_parser_custom import CustomExcelParser
import asyncio
from app.pdf_processor_fixed import FixedPDFProcessor
import os
from dotenv import load_dotenv
load_dotenv()

# Parse Excel
parser = CustomExcelParser()
excel_data = parser.parse_file("/Users/writetodennis/dev/SME/019382.xlsm")

print("="*80)
print("EXCEL SECTION 1 PERIODS EXTRACTED:")
print("="*80)
print(f"Total periods in list: {len(excel_data.section1.periods)}\n")

for i, period in enumerate(excel_data.section1.periods, 1):
    print(f"{i}. {period.period_name}")
    print(f"   Students: {period.num_students}")
    print(f"   Diet A: {period.special_diet_a}")
    print(f"   Diet B: {period.special_diet_b}")
    print()

print(f"Total students: {excel_data.section1.total_students}")
print(f"Total Diet A: {excel_data.section1.total_special_diet_a}")
print(f"Total Diet B: {excel_data.section1.total_special_diet_b}")

# Parse PDF
async def get_pdf_data():
    endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

    pdf_processor = FixedPDFProcessor(endpoint, key)
    pdf_data = await pdf_processor.process_pdf("/Users/writetodennis/dev/SME/EMEI_test1.pdf")
    return pdf_data

pdf_data = asyncio.run(get_pdf_data())

print("\n" + "="*80)
print("PDF SECTION 1 TABLE DATA:")
print("="*80)

if pdf_data.section1_table:
    print(f"Rows: {pdf_data.section1_table.row_count}")
    print(f"Columns: {pdf_data.section1_table.column_count}\n")

    for row_idx, row in enumerate(pdf_data.section1_table.cells):
        if row_idx == 0:
            print(f"Row {row_idx} (HEADER): {row}")
        else:
            period_name = str(row[0] if len(row) > 0 else "").strip()
            students = row[2] if len(row) > 2 else ""
            diet_a = row[3] if len(row) > 3 else ""
            diet_b = row[4] if len(row) > 4 else ""
            print(f"Row {row_idx}: {period_name}")
            print(f"   Students: '{students}'")
            print(f"   Diet A: '{diet_a}'")
            print(f"   Diet B: '{diet_b}'")

print("\n" + "="*80)
print("COMPARISON LOGIC:")
print("="*80)

# Simulate what reconciliation engine does
print("\nPeriods that would be added to pdf_periods dict:")
print("(Skips TOTAL and INTEGRAL)")

for row_idx, row in enumerate(pdf_data.section1_table.cells):
    if row_idx == 0:  # Skip header
        continue

    period_name = str(row[0] if len(row) > 0 else "").strip()
    if period_name and period_name.upper() not in ("TOTAL", "INTEGRAL"):
        print(f"  ✓ {period_name}")
    else:
        print(f"  ✗ {period_name} (SKIPPED)")

print("\nExcel periods that will be compared:")
for period in excel_data.section1.periods:
    print(f"  • {period.period_name}")

print("\n" + "="*80)
print("ISSUE ANALYSIS:")
print("="*80)

print("""
Excel Parser (lines 146-153):
  - Only adds periods if: num_students OR special_diet_a OR special_diet_b is not None
  - Converts None to 0 when creating EnrollmentPeriod
  - Result: Only 2 periods (1º MATUTINO, 3º VESPERTINO)

PDF Parser (line 211):
  - Skips TOTAL and INTEGRAL
  - Includes all other periods (including INTERMEDIÁRIO if it exists)
  - Empty values stay as empty strings → converted to None by _safe_int()
  - Result: 2 periods (1º MATUTINO, 3º VESPERTINO) + possibly INTERMEDIÁRIO

Reconciliation:
  - Loops through Excel periods
  - Tries to find matching period in PDF
  - Missing periods are warned but not counted as mismatches
""")
