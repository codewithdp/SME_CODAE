"""
List all days found in Section 3 PDF table
"""
import sys
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

from app.pdf_processor import PDFProcessor

async def main():
    pdf_path = "/Users/writetodennis/dev/SME/EMEI_test1.pdf"
    azure_endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    azure_key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

    print("=" * 100)
    print("ALL DAYS FOUND IN SECTION 3 PDF TABLE")
    print("=" * 100)

    pdf_processor = PDFProcessor(azure_endpoint, azure_key)
    pdf_data = await pdf_processor.process_pdf(pdf_path)

    if pdf_data.section3_table:
        print(f"\nSection 3 table: {pdf_data.section3_table.row_count} rows × {pdf_data.section3_table.column_count} cols")
        print("\nDays extracted from PDF:")
        print("-" * 100)

        days_found = []
        for row_idx, row in enumerate(pdf_data.section3_table.cells):
            if row_idx < 2:  # Skip headers
                continue

            day_col = str(row[0] if len(row) > 0 else "").strip()

            if day_col and day_col.isdigit():
                day_num = int(day_col)
                if 1 <= day_num <= 31:
                    days_found.append(day_num)
                    grupo_b_freq = row[5] if len(row) > 5 else ''
                    grupo_b_lanche_6h = row[7] if len(row) > 7 else ''
                    print(f"Day {day_num:2d}: Grupo B Freq = {str(grupo_b_freq):>4}, Lanche 6h = {str(grupo_b_lanche_6h):>4}")

        print("\n" + "-" * 100)
        print(f"Total days found: {len(days_found)} / 31")
        print(f"Days found: {sorted(days_found)}")

        # Check which days are missing
        all_days = set(range(1, 32))
        found_days = set(days_found)
        missing_days = sorted(all_days - found_days)

        if missing_days:
            print(f"\n⚠️  MISSING DAYS: {missing_days}")
            print("\nThis explains the mismatches - Azure DI OCR failed to extract these rows!")
        else:
            print("\n✅ All 31 days found!")
    else:
        print("❌ Section 3 table not found!")

    print("=" * 100)

if __name__ == "__main__":
    asyncio.run(main())
