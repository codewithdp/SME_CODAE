"""
Debug script to check what tables exist on page 2
"""

import sys
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential

async def main():
    pdf_path = "/Users/writetodennis/dev/SME/EMEI_test1.pdf"
    azure_endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    azure_key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

    print("=" * 100)
    print("DEBUGGING PAGE 2 TABLES")
    print("=" * 100)

    # Create client
    client = DocumentIntelligenceClient(endpoint=azure_endpoint, credential=AzureKeyCredential(azure_key))

    # Read PDF
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    # Analyze
    print("\nAnalyzing PDF...")
    poller = client.begin_analyze_document(
        model_id="prebuilt-layout",
        analyze_request=pdf_bytes,
        content_type="application/octet-stream"
    )
    result = poller.result()

    print(f"Total pages: {len(result.pages)}")
    print(f"Total tables: {len(result.tables)}")

    # Check all tables
    print("\n" + "=" * 100)
    print("ALL TABLES")
    print("=" * 100)
    for i, table in enumerate(result.tables):
        page_num = table.bounding_regions[0].page_number if table.bounding_regions else "Unknown"
        print(f"\nTable {i+1}:")
        print(f"  Page: {page_num}")
        print(f"  Rows: {table.row_count}")
        print(f"  Columns: {table.column_count}")

    # Filter page 2 tables
    page2_tables = [
        table for table in result.tables
        if table.bounding_regions and any(region.page_number == 2 for region in table.bounding_regions)
    ]

    print("\n" + "=" * 100)
    print(f"PAGE 2 TABLES ({len(page2_tables)} found)")
    print("=" * 100)

    for i, table in enumerate(page2_tables):
        print(f"\nPage 2 Table {i+1}:")
        print(f"  Rows: {table.row_count}")
        print(f"  Columns: {table.column_count}")

        # Check against Section 3 criteria
        if table.row_count >= 30 and table.row_count <= 35 and table.column_count >= 10:
            print(f"  ✅ MATCHES Section 3 criteria (rows 30-35, cols >= 10)")
        else:
            print(f"  ❌ Does NOT match Section 3 criteria")
            print(f"     - Rows check: {table.row_count} >= 30 and <= 35? {table.row_count >= 30 and table.row_count <= 35}")
            print(f"     - Cols check: {table.column_count} >= 10? {table.column_count >= 10}")

        # Show first few cells
        print(f"  First 3 cells:")
        for j, cell in enumerate(table.cells[:3]):
            print(f"    [{cell.row_index},{cell.column_index}]: '{cell.content}'")

    client.close()

if __name__ == "__main__":
    asyncio.run(main())
