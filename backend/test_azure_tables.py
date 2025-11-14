"""
Test Azure DI table structure
"""

import os
from dotenv import load_dotenv
load_dotenv()

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

client = DocumentIntelligenceClient(endpoint, AzureKeyCredential(key))

pdf_path = "/Users/writetodennis/dev/SME/EMEI_test1.pdf"

with open(pdf_path, "rb") as f:
    poller = client.begin_analyze_document(
        model_id="prebuilt-layout",
        analyze_request=f.read(),
        content_type="application/octet-stream"
    )
    result = poller.result()

print(f"Total tables: {len(result.tables)}\n")

for i, table in enumerate(result.tables):
    print(f"Table {i+1}:")
    print(f"  Rows: {table.row_count}, Cols: {table.column_count}")
    print(f"  Bounding regions: {table.bounding_regions}")

    # Check cells
    if hasattr(table, 'cells'):
        print(f"  Cells: {len(table.cells) if table.cells else 0}")
        if table.cells and len(table.cells) > 0:
            first_cell = table.cells[0]
            print(f"  First cell type: {type(first_cell)}")
            print(f"  First cell attributes: {[attr for attr in dir(first_cell) if not attr.startswith('_')][:15]}")
            print(f"  First cell content: {first_cell.content if hasattr(first_cell, 'content') else 'N/A'}")
            print(f"  First cell row_index: {first_cell.row_index if hasattr(first_cell, 'row_index') else 'N/A'}")
            print(f"  First cell column_index: {first_cell.column_index if hasattr(first_cell, 'column_index') else 'N/A'}")
    print()

print("\nExtracting EMEI code from content:")
import re
pattern = r'\b\d{6}\b'
matches = re.findall(pattern, result.content)
print(f"6-digit numbers found: {matches[:5]}")
