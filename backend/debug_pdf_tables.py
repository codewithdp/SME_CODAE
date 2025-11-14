"""
Debug script to see what tables Azure DI extracts from the PDF
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

    print("Analyzing PDF tables...")

    client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))

    with open(pdf_path, "rb") as f:
        poller = await client.begin_analyze_document(
            "prebuilt-layout",
            analyze_request=f,
            content_type="application/pdf"
        )
        result = await poller.result()

    print(f"\nTotal tables found: {len(result.tables)}")
    print("=" * 100)

    for i, table in enumerate(result.tables):
        print(f"\nTable {i + 1}:")
        print(f"  Rows: {table.row_count}")
        print(f"  Columns: {table.column_count}")

        # Check page number
        if table.bounding_regions:
            pages = [region.page_number for region in table.bounding_regions]
            print(f"  Pages: {pages}")

        # Show first few cells to identify the table
        print(f"  First 5 cells:")
        for j, cell in enumerate(table.cells[:5]):
            print(f"    Cell [{cell.row_index}, {cell.column_index}]: {cell.content[:50] if cell.content else 'empty'}")

    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
