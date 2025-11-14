"""
Find where Section 2 is actually located in the PDF
"""

import asyncio
import os
from dotenv import load_dotenv
from azure.ai.documentintelligence.aio import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

load_dotenv()

async def main():
    pdf_path = "/Users/writetodennis/dev/SME/EMEI_test1.pdf"
    endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

    print("Analyzing all pages to find Section 2...")

    client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))

    with open(pdf_path, "rb") as f:
        poller = await client.begin_analyze_document(
            "prebuilt-layout",
            analyze_request=f,
            content_type="application/pdf"
        )
        result = await poller.result()

    print(f"\nTotal pages: {len(result.pages)}")
    print(f"Total tables: {len(result.tables)}")

    print("\n" + "="*100)
    print("ALL TABLES IN PDF")
    print("="*100)

    for i, table in enumerate(result.tables):
        page_num = table.bounding_regions[0].page_number if table.bounding_regions else "?"
        print(f"\nTable {i}: Page {page_num}, Rows={table.row_count}, Cols={table.column_count}")

        # Show first few cells to identify the table
        print(f"  First 5 cells:")
        for j, cell in enumerate(table.cells[:5]):
            content = cell.content[:50] if cell.content else "(empty)"
            print(f"    [{cell.row_index},{cell.column_index}]: {content}")

        # Check if this looks like Section 2 (daily attendance with many columns)
        # Section 2 should have:
        # - A "Días" or day number column
        # - Many columns for different meal types
        # - 31 rows for days of the month

        has_dias = any("día" in str(cell.content).lower() for cell in table.cells[:20] if cell.content)
        has_many_rows = table.row_count >= 20

        if has_dias and has_many_rows:
            print(f"  ✅ This MIGHT be Section 2 (has 'Días' and {table.row_count} rows)")

    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
