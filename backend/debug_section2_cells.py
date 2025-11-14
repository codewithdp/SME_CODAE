"""
Debug script to see ALL cells Azure DI extracts from Section 2 table
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

    print("Analyzing PDF Section 2 table...")

    client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))

    with open(pdf_path, "rb") as f:
        poller = await client.begin_analyze_document(
            "prebuilt-layout",
            analyze_request=f,
            content_type="application/pdf"
        )
        result = await poller.result()

    print(f"\nTotal tables found: {len(result.tables)}")

    # Find Section 2 table (page 2, rows >= 30)
    section2_table = None
    for i, table in enumerate(result.tables):
        if table.bounding_regions and table.bounding_regions[0].page_number == 2:
            if table.row_count >= 30:
                section2_table = table
                print(f"\n✅ Found Section 2 table (Table {i}): rows={table.row_count}, cols={table.column_count}")
                break

    if not section2_table:
        print("❌ Section 2 table not found!")
        return

    print(f"\n" + "="*100)
    print(f"ALL CELLS IN SECTION 2 TABLE ({len(section2_table.cells)} cells)")
    print("="*100)

    for cell in section2_table.cells:
        content = cell.content[:50] if cell.content else "(empty)"
        print(f"[{cell.row_index:2d},{cell.column_index:2d}] span=({cell.row_span}x{cell.column_span}) | {content}")

    print(f"\n" + "="*100)
    print(f"CELLS BY ROW")
    print("="*100)

    # Group cells by row
    rows = {}
    for cell in section2_table.cells:
        if cell.row_index not in rows:
            rows[cell.row_index] = []
        rows[cell.row_index].append(cell)

    # Show first 5 rows
    for row_idx in range(min(5, len(rows))):
        print(f"\nRow {row_idx}:")
        for cell in sorted(rows.get(row_idx, []), key=lambda c: c.column_index):
            content = cell.content[:30] if cell.content else "(empty)"
            print(f"  Col {cell.column_index}: '{content}' (span={cell.row_span}x{cell.column_span})")

    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
