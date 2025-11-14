"""
Investigate Section 3 Day 7 mismatches
"""
import sys
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

from app.excel_parser_custom import CustomExcelParser
from app.pdf_processor import PDFProcessor

async def main():
    excel_path = "/Users/writetodennis/dev/SME/019382.xlsm"
    pdf_path = "/Users/writetodennis/dev/SME/EMEI_test1.pdf"

    azure_endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    azure_key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

    print("=" * 100)
    print("INVESTIGATING SECTION 3 DAY 7 MISMATCHES")
    print("=" * 100)

    # Parse Excel
    print("\n1. Excel Data for Section 3 Day 7:")
    print("-" * 100)
    excel_parser = CustomExcelParser()
    excel_data = excel_parser.parse_file(excel_path)

    if excel_data.section3:
        day7 = excel_data.section3.days[6]  # Index 6 = Day 7
        print(f"Day: {day7.day}")
        print(f"Grupo A Frequência: {day7.grupo_a_frequencia}")
        print(f"Grupo A Lanche 4h: {day7.grupo_a_lanche_4h}")
        print(f"Grupo A Lanche 6h: {day7.grupo_a_lanche_6h}")
        print(f"Grupo A Refeição Enteral: {day7.grupo_a_refeicao_enteral}")
        print(f"Grupo B Frequência: {day7.grupo_b_frequencia} ⚠️")
        print(f"Grupo B Lanche 4h: {day7.grupo_b_lanche_4h}")
        print(f"Grupo B Lanche 6h: {day7.grupo_b_lanche_6h} ⚠️")
        print(f"Lanche Emergencial: {day7.lanche_emergencial}")
        print(f"Kit Lanche: {day7.kit_lanche}")
        print(f"Observações: {day7.observacoes}")

    # Parse PDF
    print("\n2. PDF Data for Section 3:")
    print("-" * 100)
    pdf_processor = PDFProcessor(azure_endpoint, azure_key)
    pdf_data = await pdf_processor.process_pdf(pdf_path)

    if pdf_data.section3_table:
        print(f"Section 3 table found: {pdf_data.section3_table.row_count} rows × {pdf_data.section3_table.column_count} cols")
        print(f"\nTable structure:")

        # Show header rows
        print("\nHeader rows (first 2):")
        for i in range(min(2, len(pdf_data.section3_table.cells))):
            print(f"  Row {i}: {pdf_data.section3_table.cells[i][:12]}")

        # Find Day 7 in PDF
        print(f"\nSearching for Day 7 in PDF table...")
        for row_idx, row in enumerate(pdf_data.section3_table.cells):
            if row_idx < 2:  # Skip headers
                continue

            day_col = str(row[0] if len(row) > 0 else "").strip()

            if day_col == "7":
                print(f"\n✅ Found Day 7 at row index {row_idx}:")
                print(f"   Full row data (12 columns):")
                for col_idx in range(min(12, len(row))):
                    val = row[col_idx]
                    print(f"     Col {col_idx}: '{val}' (type: {type(val).__name__})")

                print(f"\n   Mapped to Section 3 fields:")
                print(f"     Col 0: Day = {row[0]}")
                print(f"     Col 1: Grupo A Freq = {row[1] if len(row) > 1 else 'N/A'}")
                print(f"     Col 2: Grupo A Lanche 4h = {row[2] if len(row) > 2 else 'N/A'}")
                print(f"     Col 3: Grupo A Lanche 6h = {row[3] if len(row) > 3 else 'N/A'}")
                print(f"     Col 4: Grupo A Refeição Enteral = {row[4] if len(row) > 4 else 'N/A'}")
                print(f"     Col 5: Grupo B Freq = {row[5] if len(row) > 5 else 'N/A'} ⚠️")
                print(f"     Col 6: Grupo B Lanche 4h = {row[6] if len(row) > 6 else 'N/A'}")
                print(f"     Col 7: Grupo B Lanche 6h = {row[7] if len(row) > 7 else 'N/A'} ⚠️")
                print(f"     Col 8: Lanche Emergencial = {row[8] if len(row) > 8 else 'N/A'}")
                print(f"     Col 9: Kit Lanche = {row[9] if len(row) > 9 else 'N/A'}")
                print(f"     Col 10: (empty/separator) = {row[10] if len(row) > 10 else 'N/A'}")
                print(f"     Col 11: Observações = {row[11] if len(row) > 11 else 'N/A'}")
                break
        else:
            print("❌ Day 7 not found in PDF table!")
    else:
        print("❌ Section 3 table not found in PDF!")

    # Show surrounding days for context
    print("\n3. Context - Days 6, 7, 8 from PDF:")
    print("-" * 100)
    if pdf_data.section3_table:
        for row_idx, row in enumerate(pdf_data.section3_table.cells):
            if row_idx < 2:
                continue
            day_col = str(row[0] if len(row) > 0 else "").strip()
            if day_col in ["6", "7", "8"]:
                print(f"\nDay {day_col}:")
                print(f"  Grupo B Freq (col 5): {row[5] if len(row) > 5 else 'N/A'}")
                print(f"  Grupo B Lanche 6h (col 7): {row[7] if len(row) > 7 else 'N/A'}")

    print("\n" + "=" * 100)
    print("ANALYSIS")
    print("=" * 100)
    print("\nExpected:")
    print("  Excel Day 7: Grupo B Freq = 16, Lanche 6h = 16")
    print("\nActual from PDF:")
    print("  Check the Col 5 and Col 7 values above")
    print("\nPossible issues:")
    print("  1. Azure DI OCR failed to extract these specific cells")
    print("  2. Column mapping is incorrect")
    print("  3. Day 7 row is misidentified")
    print("  4. Values are in different columns than expected")
    print("=" * 100)

if __name__ == "__main__":
    asyncio.run(main())
